

import json
from pathlib import Path

file_path = Path("batch_ocr_results.json")

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

required_fields = [
    "document_type",
    "institution_name",
    "trust_society_name",
]

missing_count = {field: 0 for field in required_fields}
incomplete_documents = []

for index, doc in enumerate(data, start=1):
    fields = doc.get("fields") or {}
    missing = []

    for field in required_fields:
        value = fields.get(field)

        if not isinstance(value, str) or not value.strip():
            missing.append(field)
            missing_count[field] += 1

    if missing:
        incomplete_documents.append({
            "record": index,
            "file": doc.get("file", "Unknown"),
            "missing_fields": missing
        })

report = {
    "total_records": len(data),
    "records_with_missing_fields": len(incomplete_documents),
    "missing_field_counts": missing_count,
    "incomplete_documents": incomplete_documents,
}

with open("ocr_validation_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("\n========== OCR VALIDATION REPORT ==========")
print(f"Total records: {len(data)}")
print(f"Records with missing fields: {len(incomplete_documents)}")

print("\nMissing field counts:")
for field, count in missing_count.items():
    print(f"{field}: {count}")

print("\nFirst 20 incomplete records:")
for item in incomplete_documents[:20]:
    print(item)

print("\nFull report saved to ocr_validation_report.json")
