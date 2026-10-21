-- Additive service evidence extension; no existing records are changed.
CREATE TABLE IF NOT EXISTS service_responses (
 request_id INTEGER PRIMARY KEY REFERENCES service_requests(request_id),
 first_response_at TEXT NOT NULL CHECK(julianday(first_response_at) IS NOT NULL),
 is_synthetic INTEGER NOT NULL DEFAULT 0 CHECK(is_synthetic IN (0,1)),
 source TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS maintenance_schedule (
 maintenance_id INTEGER PRIMARY KEY,
 maintenance_key TEXT NOT NULL UNIQUE,
 customer_id INTEGER NOT NULL,
 device_id INTEGER NOT NULL,
 scheduled_at TEXT NOT NULL CHECK(julianday(scheduled_at) IS NOT NULL),
 status TEXT NOT NULL CHECK(status IN ('Scheduled','Completed','Cancelled')),
 is_synthetic INTEGER NOT NULL DEFAULT 0 CHECK(is_synthetic IN (0,1)),
 notes TEXT,
 FOREIGN KEY(customer_id,device_id) REFERENCES customer_devices(customer_id,device_id)
);
