


import json
import re
import sys
from pathlib import Path

import fitz
import pytesseract
from PIL import Image, ImageEnhance, ImageOps

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(r"C:\Users\omkar\Downloads\OCR_Module")
DATASET_DIR = (
    BASE_DIR / "datasets" / "AICTE_Synthetic_Dataset" / "documents"
)
OUTPUT_FILE = BASE_DIR / "batch_ocr_results.json"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg",
    ".tif", ".tiff", ".bmp", ".webp"
}

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# --------------------------------------------------
# FIELD LABELS
# --------------------------------------------------

INSTITUTION_LABELS = [
    r"name\s+of\s+institution",
    r"applicant\s+institution",
    r"institution\s+name",
    r"name\s+of\s+college",
    r"college\s+name",
    r"premises\s+name",
    r"institution\s+managed",
]

TRUST_LABELS = [
    r"name\s+of\s+trust\s*/\s*society",
    r"name\s+of\s+society\s*/\s*trust",
    r"name\s+of\s+trust\s+/\s+society",
    r"name\s+of\s+society\s+/\s+trust",
    r"name\s+of\s+trust",
    r"name\s+of\s+society",
    r"trust\s*/\s*society\s+name",
    r"society\s*/\s*trust\s+name",
    r"trust\s+name",
    r"society\s+name",
]

ALL_LABELS = INSTITUTION_LABELS + TRUST_LABELS

# --------------------------------------------------
# OCR
# --------------------------------------------------

def ocr_image(image):
    image = ImageOps.exif_transpose(image).convert("L")
    image = ImageEnhance.Contrast(image).enhance(1.8)

    return pytesseract.image_to_string(
        image, config="--psm 6"
    ).strip()


def extract_text(file_path):
    if file_path.suffix.lower() == ".pdf":
        page_texts = []

        with fitz.open(file_path) as pdf:
            for page in pdf:
                text = page.get_text("text").strip()

                # OCR scanned pages or pages with no embedded text
                if not text:
                    pix = page.get_pixmap(
                        matrix=fitz.Matrix(2, 2),
                        alpha=False
                    )
                    image = Image.frombytes(
                        "RGB",
                        (pix.width, pix.height),
                        pix.samples
                    )
                    text = ocr_image(image)

                if text:
                    page_texts.append(text)

        return "\n".join(page_texts).strip()

    with Image.open(file_path) as image:
        return ocr_image(image)


# --------------------------------------------------
# FIELD EXTRACTION HELPERS
# --------------------------------------------------

def normalize_text(value):
    value = re.sub(r"\s+", " ", value).strip()
    return value.strip(" \t:;,-|")


def is_label(line):
    normalized = normalize_text(line)

    return any(
        re.fullmatch(
            label, normalized, flags=re.IGNORECASE
        )
        for label in ALL_LABELS
    )


def looks_like_another_field(line):
    """Avoid treating the next field label as a field value."""
    value = normalize_text(line)

    if is_label(value):
        return True

    common_labels = [
        r"application\s+id",
        r"document\s+id",
        r"date",
        r"address",
        r"state",
        r"pin\s*code",
        r"email",
        r"phone",
        r"contact\s+(?:number|details)",
        r"registration\s+(?:no\.?|number)",
        r"pan\s+of\s+trust",
        r"type\s+of\s+institution",
        r"year\s+of\s+establishment",
        r"principal\s*/\s*director",
        r"academic\s+year",
        r"programme",
        r"total\s+faculty",
        r"total\s+land\s+area",
        r"total\s+built[\s-]*up\s+area",
    ]

    return any(
        re.match(rf"^{label}\b", value, re.IGNORECASE)
        for label in common_labels
    )


def find_label_value(text, labels):
    lines = [
        normalize_text(line)
        for line in text.splitlines()
        if normalize_text(line)
    ]

    # Match a label on its own line or a label followed by a value.
    for index, line in enumerate(lines):
        for label in labels:
            match = re.match(
                rf"^\s*(?:{label})\s*:?\s*(.*?)\s*$",
                line,
                flags=re.IGNORECASE
            )

            if not match:
                continue

            # Value may appear on the same line as the label.
            value = normalize_text(match.group(1))

            if value and not looks_like_another_field(value):
                return value

            # Or on the following line.
            if index + 1 < len(lines):
                next_line = lines[index + 1]

                if not looks_like_another_field(next_line):
                    return next_line

    return None


def find_known_name(text, candidates):
    """Find a known name only when it occurs in extracted text."""
    for candidate in candidates:
        pattern = re.escape(candidate)
        match = re.search(pattern, text, flags=re.IGNORECASE)

        if match:
            return normalize_text(match.group(0))

    return None


# --------------------------------------------------
# DOCUMENT TYPE CLASSIFICATION
# --------------------------------------------------

def classify_document(file_path, text):
    # The filename is more reliable for this synthetic dataset
    # than searching the entire document for generic words.
    name = file_path.stem.lower()
    filename_rules = [
        ("fire_safety_certificate", "fire_safety_certificate"),
        ("building_plan_approval", "building_plan_approval"),
        ("society_registration", "society_registration"),
        ("land_document", "land_document"),
        ("application_form", "application_form"),
        ("affiliation_letter", "affiliation_letter"),
        ("bank_fdr_certificate", "bank_fdr_certificate"),
        ("audited_financials", "audited_financials"),
        ("faculty_list", "faculty_list"),
        ("infrastructure_report", "infrastructure_report"),
        ("noc_state_govt", "noc_state_govt"),
        ("fee_receipt", "fee_receipt"),
    ]

    for filename_pattern, document_type in filename_rules:
        if filename_pattern in name:
            return document_type

    # Fallback when a filename does not identify the document.
    content = text.lower()

    if "fire safety" in content:
        return "fire_safety_certificate"
    if "building plan approval" in content:
        return "building_plan_approval"
    if "society registration" in content or "trust registration" in content:
        return "society_registration"
    if "application for approval of institution" in content:
        return "application_form"
    if "affiliation letter" in content:
        return "affiliation_letter"
    if "audited financial" in content:
        return "audited_financials"
    if "faculty list" in content:
        return "faculty_list"
    if "infrastructure report" in content:
        return "infrastructure_report"
    if "bank fdr" in content:
        return "bank_fdr_certificate"
    if "fee receipt" in content:
        return "fee_receipt"
    if re.search(r"\bno objection certificate\b|\bgovernment noc\b", content):
        return "noc_state_govt"
    if "land document" in content or "land ownership" in content:
        return "land_document"

    return "unknown"


# --------------------------------------------------
# EXTRACT ALL FIELDS
# --------------------------------------------------

def extract_fields(text, file_path):
    institution = find_label_value(text, INSTITUTION_LABELS)
    trust = find_label_value(text, TRUST_LABELS)

    # Dataset-specific fallbacks. These names are used only if
    # they actually occur in the extracted text.
    if not institution:
        institution = find_known_name(
            text,
            ["Sahyadri Polytechnic"]
        )

    if not trust:
        trust = find_known_name(
            text,
            ["Verma Shikshan Prasarak Mandal"]
        )

    return {
        "document_type": classify_document(file_path, text),
        "institution_name": institution,
        "trust_society_name": trust,
    }


# --------------------------------------------------
# MAIN BATCH PROCESS
# --------------------------------------------------

def main():
    print("Starting batch OCR...", flush=True)
    print(f"Dataset folder: {DATASET_DIR}", flush=True)

    if not DATASET_DIR.is_dir():
        print(f"ERROR: Dataset folder not found: {DATASET_DIR}")
        sys.exit(1)

    if not Path(TESSERACT_PATH).is_file():
        print(f"ERROR: Tesseract not found: {TESSERACT_PATH}")
        print("Update TESSERACT_PATH to your actual installation.")
        sys.exit(1)

    files = sorted(
        path for path in DATASET_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    )

    print(f"Supported documents found: {len(files)}", flush=True)

    if not files:
        print("No supported PDF or image files found.")
        sys.exit(1)

    results = []

    for number, file_path in enumerate(files, start=1):
        relative_path = str(file_path.relative_to(DATASET_DIR))
        print(
            f"[{number}/{len(files)}] {relative_path}",
            flush=True
        )

        row = {
            "file": relative_path,
            "status": "success",
            "extracted_text": "",
            "fields": {},
            "error": None,
        }

        try:
            text = extract_text(file_path)
            row["extracted_text"] = text
            row["fields"] = extract_fields(text, file_path)

        except Exception as exc:
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR: {row['error']}", flush=True)

        results.append(row)

        # Save progress after every document.
        OUTPUT_FILE.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    successful = sum(
        row["status"] == "success" for row in results
    )

    print("\nOCR processing finished.")
    print(f"Total documents: {len(files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(files) - successful}")
    print(f"Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
