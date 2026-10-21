CREATE TABLE IF NOT EXISTS customer_devices (
 customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 device_id INTEGER NOT NULL UNIQUE REFERENCES devices(device_id),
 purchase_date TEXT NOT NULL CHECK(date(purchase_date,'+0 days') IS NOT NULL AND date(purchase_date,'+0 days')=purchase_date),
 warranty_start_date TEXT NOT NULL CHECK(date(warranty_start_date,'+0 days') IS NOT NULL AND date(warranty_start_date,'+0 days')=warranty_start_date),
 warranty_end_date TEXT NOT NULL CHECK(date(warranty_end_date,'+0 days') IS NOT NULL AND date(warranty_end_date,'+0 days')=warranty_end_date),
 PRIMARY KEY(customer_id,device_id), CHECK(warranty_start_date>=purchase_date), CHECK(warranty_end_date>=warranty_start_date)
);
CREATE TABLE IF NOT EXISTS amc_renewals (
 renewal_id INTEGER PRIMARY KEY, contract_id INTEGER NOT NULL REFERENCES amc_contracts(contract_id),
 renewal_key TEXT NOT NULL UNIQUE, due_date TEXT NOT NULL, quoted_amount_cents INTEGER CHECK(quoted_amount_cents>=0),
 currency TEXT NOT NULL DEFAULT 'LKR', status TEXT NOT NULL CHECK(status IN ('Pending','Contacted','Accepted','Declined')), notes TEXT
);
CREATE TABLE IF NOT EXISTS invoices (
 invoice_id INTEGER PRIMARY KEY, invoice_number TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 issued_date TEXT NOT NULL, due_date TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>=0), currency TEXT NOT NULL DEFAULT 'LKR', description TEXT, CHECK(due_date>=issued_date)
);
CREATE TABLE IF NOT EXISTS payments (
 payment_id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL REFERENCES invoices(invoice_id), payment_reference TEXT NOT NULL UNIQUE,
 paid_date TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0), method TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS service_requests (
 request_id INTEGER PRIMARY KEY, request_number TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL, device_id INTEGER NOT NULL,
 opened_at TEXT NOT NULL, issue_description TEXT NOT NULL, priority TEXT NOT NULL CHECK(priority IN ('Low','Normal','High','Urgent')),
 status TEXT NOT NULL CHECK(status IN ('Open','Scheduled','In progress','Resolved','Cancelled')),
 FOREIGN KEY(customer_id,device_id) REFERENCES customer_devices(customer_id,device_id)
);
CREATE TABLE IF NOT EXISTS service_visits (
 visit_id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL REFERENCES service_requests(request_id), visit_key TEXT NOT NULL UNIQUE,
 scheduled_at TEXT NOT NULL, completed_at TEXT, technician_name TEXT, resolution TEXT,
 CHECK(completed_at IS NULL OR completed_at>=scheduled_at)
);
CREATE TABLE IF NOT EXISTS call_recordings (
 recording_id INTEGER PRIMARY KEY, recording_key TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL, device_id INTEGER NOT NULL,
 recorded_at TEXT NOT NULL, file_path TEXT, sha256 TEXT, duration_seconds REAL CHECK(duration_seconds>=0),
 is_synthetic INTEGER NOT NULL DEFAULT 0 CHECK(is_synthetic IN (0,1)),
 FOREIGN KEY(customer_id,device_id) REFERENCES customer_devices(customer_id,device_id)
);
CREATE TABLE IF NOT EXISTS emotion_segments (
 segment_id INTEGER PRIMARY KEY, recording_id INTEGER NOT NULL REFERENCES call_recordings(recording_id),
 start_seconds REAL NOT NULL CHECK(start_seconds>=0), end_seconds REAL NOT NULL, speaker_role TEXT NOT NULL,
 emotion TEXT NOT NULL, confidence REAL CHECK(confidence BETWEEN 0 AND 1), model_version TEXT NOT NULL,
 CHECK(end_seconds>start_seconds), UNIQUE(recording_id,start_seconds,end_seconds,speaker_role,model_version)
);
CREATE TABLE IF NOT EXISTS business_factors (
 factor_id INTEGER PRIMARY KEY, factor_key TEXT NOT NULL UNIQUE, customer_id INTEGER REFERENCES customers(customer_id),
 factor_name TEXT NOT NULL, numeric_value REAL, unit TEXT, observed_at TEXT NOT NULL, source TEXT NOT NULL, notes TEXT
);
CREATE TABLE IF NOT EXISTS policy_documents (
 document_id INTEGER PRIMARY KEY, document_key TEXT NOT NULL UNIQUE, title TEXT NOT NULL, version TEXT NOT NULL,
 source_uri TEXT, content_sha256 TEXT, effective_date TEXT, is_synthetic INTEGER NOT NULL DEFAULT 0 CHECK(is_synthetic IN (0,1))
);
CREATE TABLE IF NOT EXISTS policy_chunks (
 chunk_id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES policy_documents(document_id),
 chunk_index INTEGER NOT NULL CHECK(chunk_index>=0), content TEXT NOT NULL, page_number INTEGER CHECK(page_number>0),
 embedding_model TEXT, embedding BLOB, UNIQUE(document_id,chunk_index)
);
CREATE TABLE IF NOT EXISTS agent_runs (
 run_id INTEGER PRIMARY KEY, run_key TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL, device_id INTEGER NOT NULL,
 recording_id INTEGER REFERENCES call_recordings(recording_id), started_at TEXT NOT NULL, finished_at TEXT,
 status TEXT NOT NULL CHECK(status IN ('Queued','Running','Completed','Failed')), framework_version TEXT NOT NULL,
 FOREIGN KEY(customer_id,device_id) REFERENCES customer_devices(customer_id,device_id)
);
CREATE TABLE IF NOT EXISTS agent_findings (
 finding_id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES agent_runs(run_id), agent_name TEXT NOT NULL,
 finding_key TEXT NOT NULL, finding TEXT NOT NULL, evidence_chunk_id INTEGER REFERENCES policy_chunks(chunk_id),
 confidence REAL CHECK(confidence BETWEEN 0 AND 1), UNIQUE(run_id,agent_name,finding_key)
);
CREATE INDEX IF NOT EXISTS idx_emotion_recording ON emotion_segments(recording_id);
CREATE INDEX IF NOT EXISTS idx_requests_customer ON service_requests(customer_id,status);
CREATE INDEX IF NOT EXISTS idx_findings_run ON agent_findings(run_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE TRIGGER IF NOT EXISTS amc_v5_ownership_delete BEFORE DELETE ON customer_devices WHEN EXISTS(SELECT 1 FROM customers WHERE customer_id=OLD.customer_id AND device_id=OLD.device_id) OR EXISTS(SELECT 1 FROM amc_contracts WHERE customer_id=OLD.customer_id AND device_id=OLD.device_id) OR EXISTS(SELECT 1 FROM service_history WHERE customer_id=OLD.customer_id AND device_id=OLD.device_id) BEGIN SELECT RAISE(ABORT,'Ownership has legacy references'); END;
CREATE TRIGGER IF NOT EXISTS amc_v5_ownership_update BEFORE UPDATE OF customer_id,device_id ON customer_devices BEGIN SELECT RAISE(ABORT,'Ownership identifiers are immutable'); END;
CREATE TRIGGER IF NOT EXISTS amc_v5_customer_insert AFTER INSERT ON customers BEGIN INSERT INTO customer_devices VALUES(NEW.customer_id,NEW.device_id,NEW.purchase_date,NEW.warranty_start_date,NEW.warranty_end_date); END;
CREATE TRIGGER IF NOT EXISTS amc_v5_customer_dates AFTER UPDATE OF purchase_date,warranty_start_date,warranty_end_date ON customers BEGIN UPDATE customer_devices SET purchase_date=NEW.purchase_date,warranty_start_date=NEW.warranty_start_date,warranty_end_date=NEW.warranty_end_date WHERE customer_id=NEW.customer_id AND device_id=NEW.device_id; END;
CREATE TRIGGER IF NOT EXISTS amc_v5_primary_immutable BEFORE UPDATE OF customer_id,device_id ON customers WHEN NEW.customer_id IS NOT OLD.customer_id OR NEW.device_id IS NOT OLD.device_id BEGIN SELECT RAISE(ABORT,'Legacy primary ownership is immutable'); END;
CREATE TRIGGER IF NOT EXISTS amc_v5_run_recording_insert BEFORE INSERT ON agent_runs WHEN NEW.recording_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM call_recordings WHERE recording_id=NEW.recording_id AND customer_id=NEW.customer_id AND device_id=NEW.device_id) BEGIN SELECT RAISE(ABORT,'Recording context mismatch'); END;
CREATE TRIGGER IF NOT EXISTS amc_v5_run_recording_update BEFORE UPDATE ON agent_runs WHEN NEW.recording_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM call_recordings WHERE recording_id=NEW.recording_id AND customer_id=NEW.customer_id AND device_id=NEW.device_id) BEGIN SELECT RAISE(ABORT,'Recording context mismatch'); END;
CREATE TRIGGER IF NOT EXISTS amc_v5_recording_context BEFORE UPDATE OF customer_id,device_id ON call_recordings WHEN EXISTS(SELECT 1 FROM agent_runs WHERE recording_id=OLD.recording_id) BEGIN SELECT RAISE(ABORT,'Recording has agent runs'); END;
