
import json
from pathlib import Path

BASE_DIR = Path(r"C:\Users\omkar\Downloads\OCR_Module")
JSON_FILE = BASE_DIR / "batch_ocr_results.json"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    results = json.load(f)

# Inspect three sample documents
targets = [
    "01_application_form.pdf",
    "03_land_document.pdf",
    "05_fire_safety_certificate.pdf",
]

for target in targets:
    doc = next(
        (r for r in results if r.get("file", "").endswith(target)),
        None
    )

    print("\n" + "=" * 65)
    print("FILE:", target)

    if doc is None:
        print("Document not found.")
        continue

    print("STATUS:", doc.get("status"))
    print("EXTRACTED FIELDS:")
    print(json.dumps(doc.get("fields", {}), indent=2))

    text = doc.get("extracted_text", "")
    print("\nRELEVANT EXTRACTED TEXT:")

    lines = text.splitlines()
    matches = [
        i for i, line in enumerate(lines)
        if any(
            word in line.lower()
            for word in [
                "institution", "premises", "trust",
                "society", "sahyadri", "verma"
            ]
        )
    ]

    if not matches:
        print("No matching lines found.")
    else:
        shown = set()
        for i in matches:
            for j in range(max(0, i - 1), min(len(lines), i + 3)):
                if j not in shown:
                    print(f"{j + 1}: {lines[j]}")
                    shown.add(j)

print("\nDebug inspection complete.")
