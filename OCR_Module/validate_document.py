
import sys
import re
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


image_path = sys.argv[1] if len(sys.argv) > 1 else "sample.png"
image = Image.open(image_path)
text = pytesseract.image_to_string(image)

# Check required fields
required_fields = {
    "Student Name": r"Student Name\s*[:=]?\s*\S+",
    "Receipt Number": r"Receipt No\s*[:=]?\s*\S+",
    "Date": r"Date\s*[:=]?\s*\S+",
    "Enrollment Number": r"Enrollment No\s*[:=]?\s*\S+",
    "Total Amount": r"Total Amount Paid\s*[₹]?\s*[\d,]+"
}

print("\n--- Document Validation Report ---")

all_fields_found = True

for field, pattern in required_fields.items():
    if re.search(pattern, text, re.IGNORECASE):
        print(f"PASS: {field} found")
    else:
        print(f"CHECK: {field} missing or unreadable")
        all_fields_found = False

print("\nRequired-field check:",
      "PASSED" if all_fields_found else "NEEDS REVIEW")

print("\nNote: This checks field presence only.")
print("It does not prove document authenticity.")
