


import re
import json
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Read image and extract text
image = Image.open("sample.png")
text = pytesseract.image_to_string(image)

# Show OCR text to help debug
print("\n--- OCR TEXT ---")
print(text)

# Extract fields
patterns = {
    "student_name": r"Student Name\s*[:=]?\s*(.+)",
    "receipt_number": r"Receipt No\s*[:=]?\s*(.+)",
    "date": r"Date\s*[:=]?\s*(.+)",
    "enrollment_number": r"Enrollment No\s*[:=]?\s*(.+)",
    "total_amount": r"Total Amount Paid\s*[:=]?\s*([\d,]+)"
}

data = {}

for field, pattern in patterns.items():
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        value = match.group(1).strip().lstrip(":=").strip()

        if field == "total_amount":
            value = int(value.replace(",", ""))

        data[field] = value
    else:
        data[field] = None

data["document_type"] = (
    "Fee Receipt"
    if re.search(r"FEE\s+RECEIPT", text, re.IGNORECASE)
    else "Unknown"
)

# Save as JSON
with open("extracted_data.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=4, ensure_ascii=False)

print("\n--- EXTRACTED DATA ---")
print(json.dumps(data, indent=4, ensure_ascii=False))
print("\nSaved to extracted_data.json")
