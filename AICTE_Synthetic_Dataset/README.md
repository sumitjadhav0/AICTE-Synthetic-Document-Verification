# AICTE Synthetic Document Dataset

**All content is fictional.** Institution names, people, registration numbers, PANs, bank details and issuing
authorities are randomly generated. Every document carries a diagonal *"SYNTHETIC - NOT AN OFFICIAL DOCUMENT"*
watermark and a footer with its Doc ID. Issuing authorities are labelled "(Fictional)". No real AICTE logo, seal or
signature is used. Random names may coincide with real institutions by chance.

Built to the spec in the project README (OCR extraction, classification, missing/duplicate/inconsistent document
detection, rule validation, evidence-based reports). It was **not** derived from the contents of the GitHub repository,
which could not be accessed when this was generated.

## Contents (60 applications, 1018 files)

| Folder | What | Count |
|---|---|---|
| `documents/<APP_ID>/` | Born-digital PDFs (11 document types per application) | 658 |
| `scans/<APP_ID>/` | JPEG scans of 3 documents per application: clean / skewed / noisy_lowres / stamped | 180 |
| `images/<APP_ID>/` | Synthetic campus front, computer lab and library pictures | 180 |
| `logos/` | Generated institution logos | 60 |
| `data/` | CSV + JSON labels, extracted-field ground truth, anomaly labels | |
| `database/aicte_synthetic.db` | SQLite with the same tables as the CSVs | |
| `config/rules.json` | Rule definitions + **placeholder** thresholds | |
| `generator/` | Generator and validator (fully reproducible, seed 2026) | |

Institution mix: {'Polytechnic': 14, 'Engineering': 36, 'Management': 10}. Applications with no injected issue: 20; with 1+ injected issues: 40.

## Document types (per application)
`application_form`, `society_registration`, `land_document`, `building_plan_approval`, `fire_safety_certificate`,
`noc_state_govt`, `affiliation_letter`, `bank_fdr_certificate`, `audited_financials`, `faculty_list` (multi-page),
`infrastructure_report`. Each PDF has a QR code (Doc ID), a synthetic seal and a scribble signature.

## Injected anomalies (ground truth in `data/ground_truth_anomalies.csv`)
| Anomaly | Rule | Severity | Applications | Meaning |
|---|---|---|---|---|
| MISSING_DOCUMENT | R001 | critical | 2 | A required document is absent from the application |
| DUPLICATE_FILE | R002 | high | 2 | Same file submitted under two different document types |
| INSTITUTION_NAME_MISMATCH | R003 | medium | 2 | Institution name differs from the application form |
| TRUST_NAME_MISMATCH | R004 | high | 5 | Trust/society name differs across documents |
| SOCIETY_REG_NO_MISMATCH | R005 | high | 4 | Society registration number differs from application form |
| LAND_AREA_MISMATCH | R006 | high | 3 | Land area differs between application and supporting document |
| BUILT_UP_AREA_MISMATCH | R007 | medium | 4 | Built-up area differs between application and supporting document |
| INTAKE_MISMATCH | R008 | high | 6 | Programme intake differs from application form |
| FACULTY_COUNT_MISMATCH | R009 | medium | 3 | Declared faculty count differs from faculty list |
| FIRE_CERT_EXPIRED | R010 | high | 1 | Fire safety certificate expired before the application date |
| FUTURE_DATED_DOCUMENT | R011 | high | 5 | Document is dated after the application date |
| FDR_BELOW_THRESHOLD | R012 | high | 4 | Deposit is below the configured placeholder threshold |
| FDR_MATURED | R013 | high | 3 | Fixed deposit matured before the application date |
| FACULTY_RATIO_EXCEEDED | R014 | high | 2 | Students per faculty exceeds configured placeholder limit |
| PINCODE_MISMATCH | R015 | low | 4 | PIN code differs from application form |
| LAND_BELOW_MINIMUM | R016 | high | 2 | Land area below configured placeholder minimum (consistent across documents) |
| PAN_FORMAT_INVALID | R017 | medium | 5 | PAN does not match the AAAAA9999A format |

## Key files
* `data/documents.csv`: one row per file. `declared_doc_type` vs `actual_content_type` differ for duplicated files.
  Scans link to their source PDF via `source_doc_id`.
* `data/extracted_fields_ground_truth.csv`: the exact field values printed in each PDF (long format). Use it to score OCR.
* `data/ground_truth_anomalies.csv`: expected value vs injected value, document, field, rule.
* `data/expected_findings.json`: expected status (`CLEAN` / `NEEDS_REVIEW`) and rules violated per application.
* `data/applications.json`: everything above nested per application.

## Important limitations
* `config/rules.json` thresholds (minimum land area, FDR amount, students-per-faculty) are **placeholders for testing**.
  They are **not** taken from the AICTE Approval Process Handbook. `handbook_reference` is `null` and `verified` is
  `false` for every rule. Map each rule to a real clause and verify it before trusting any compliance result.
* Document layouts are generic and simplified, not replicas of any real certificate format.
* Results from tools tested on this data are advisory; a human must review.

## Regenerate / validate
```
pip install reportlab pillow numpy      # also needs poppler-utils (pdftoppm)
python generator/generate_dataset.py --n 60 --seed 2026 --out ./AICTE_Synthetic_Dataset --zip
python generator/validate_dataset.py ./AICTE_Synthetic_Dataset
```
`validate_dataset.py` checks file hashes and runs a reference implementation of the rules over the ground truth;
it must reproduce the injected anomalies exactly (TP=57, FP=0, FN=0 for the shipped dataset).
Same seed and same count give byte-identical output.
