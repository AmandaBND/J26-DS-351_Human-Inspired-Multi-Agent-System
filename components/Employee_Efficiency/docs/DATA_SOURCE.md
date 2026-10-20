# Company data source

The component consumes the operational company export in `data/raw/`. The current snapshot covers
January 2024 through September 2026 and includes service jobs, AMC proposals and contracts,
attendance, downtime, pricing, competitor notes, manager reviews, employee feedback, and reference
tables.

Employee identifiers are normalized during preprocessing and mapped to pseudonyms before any
employee-linked record is persisted. The mapping is stored only in `data/private/pseudonym_map.csv`,
which must not be committed, copied into reports, or shared with an LLM.

The source export is the operational record; this component derives the monthly measures documented
in [DATA_DICTIONARY.md](./DATA_DICTIONARY.md). Those measures are not substitutes for manager review.
Evaluation scores are shown only when verified, period-specific company outcome labels are available
in `data/verified_outcomes.csv`.
