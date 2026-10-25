
import json
from pathlib import Path
from collections import Counter

INPUT_FILE = Path("batch_ocr_results.json")
OUTPUT_FILE = Path("batch_ocr_results_enriched.json")
REPORT_FILE = Path("cross_document_report.json")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"{INPUT_FILE} not found. Run this script from the OCR_Module folder."
    )

with INPUT_FILE.open("r", encoding="utf-8") as f:
    records = json.load(f)


def get_app_id(file_path):
    parts = str(file_path).replace("/", "\\").split("\\")
    for part in parts:
        if part.startswith("SYN-APP-"):
            return part
    return None


# Get institution and trust names from each application form.
references = {}

for record in records:
    path = record.get("file", "")
    if path.lower().endswith("01_application_form.pdf"):
        app_id = get_app_id(path)
        fields = record.get("fields", {})

        if app_id:
            references[app_id] = {
                "institution_name": fields.get("institution_name"),
                "trust_society_name": fields.get("trust_society_name"),
            }


filled = Counter()
changes = []
unmatched = []

# Fill only fields that are missing, using the same application's form.
for record in records:
    path = record.get("file", "")
    app_id = get_app_id(path)

    if not app_id or app_id not in references:
        unmatched.append(path)
        continue

    fields = record.setdefault("fields", {})
    reference = references[app_id]

    for field in ("institution_name", "trust_society_name"):
        if not fields.get(field) and reference.get(field):
            fields[field] = reference[field]
            filled[field] += 1

            changes.append({
                "file": path,
                "application_id": app_id,
                "field": field,
                "value": reference[field],
                "source": "01_application_form.pdf",
            })


# Save new files; do not overwrite the original OCR results.
with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(records, f, indent=2, ensure_ascii=False)

report = {
    "total_documents": len(records),
    "application_forms_found": len(references),
    "institution_names_filled": filled["institution_name"],
    "trust_names_filled": filled["trust_society_name"],
    "total_fields_filled": len(changes),
    "unmatched_documents": unmatched,
    "changes": changes,
    "note": (
        "Copied names come from the application form in the same folder. "
        "They have not been independently verified against each document."
    ),
}

with REPORT_FILE.open("w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("\nCross-document check completed!")
print("Total documents:", len(records))
print("Application forms found:", len(references))
print("Institution names filled:", filled["institution_name"])
print("Trust names filled:", filled["trust_society_name"])
print("Total fields filled:", len(changes))
print("Output:", OUTPUT_FILE)
print("Report:", REPORT_FILE)
