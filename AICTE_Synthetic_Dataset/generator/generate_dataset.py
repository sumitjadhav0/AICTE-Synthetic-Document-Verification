#!/usr/bin/env python3
"""
AICTE-style SYNTHETIC document dataset generator.

Everything produced here is FICTIONAL. Institution names, people, registration
numbers, PANs, bank details and authorities are randomly generated. Issuing
authorities are labelled "(Fictional)" and every page carries a diagonal
"SYNTHETIC - NOT AN OFFICIAL DOCUMENT" watermark. No real logos or seals are used.
Random names may coincide with real institutions by chance.

Usage:  python generate_dataset.py --n 60 --seed 2026 --out ./AICTE_Synthetic_Dataset
"""
import argparse, csv, datetime as dt, hashlib, json, math, os, random, shutil
import sqlite3, subprocess, tempfile, zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
for alias, fname in [("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"),
                     ("DV-I", "DejaVuSans-Oblique.ttf"), ("DVS", "DejaVuSerif.ttf"),
                     ("DVS-B", "DejaVuSerif-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(alias, FONT_DIR + fname))


def pil_font(size, bold=False):
    return ImageFont.truetype(FONT_DIR + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)


W, H = A4
GENERATOR_VERSION = "1.0.0"
WATERMARK = "SYNTHETIC - NOT AN OFFICIAL DOCUMENT"

# --------------------------------------------------------------------------------------
# Placeholder thresholds. NOT taken from the AICTE Approval Process Handbook.
# They exist so the rule engine has something configurable to test against.
# --------------------------------------------------------------------------------------
THRESHOLDS = {
    "min_land_area_sqm": {"Engineering": 10000, "Polytechnic": 6000, "Management": 4000},
    "min_fdr_inr": {"Engineering": 5000000, "Polytechnic": 2500000, "Management": 3000000},
    "max_students_per_faculty": {"Engineering": 20, "Polytechnic": 25, "Management": 20},
}

# --------------------------------------------------------------------------------------
# Name / location pools
# --------------------------------------------------------------------------------------
PREFIXES = ["Shri Samarth", "Sant Dnyaneshwar", "Rajarshi", "Maharshi Atri", "Bhagwan Mahavir", "Vidyasagar",
            "Gyan Jyoti", "Nav Bharat", "Aryabhata", "Chanakya", "Kalpataru", "Saraswati", "Lokmanya",
            "Jai Hind", "Pragati", "Ujjwal", "Siddhivinayak", "Navjeevan", "Tapovan", "Matoshri", "Kohinoor",
            "Sahyadri", "Himalaya", "Godavari", "Narmada", "Yamuna", "Vindhya", "Sagar", "Alpha Vidya",
            "Bharat Rattan", "Sunrise", "Horizon", "Ananta", "Veer Savarkar Memorial", "Mahalaxmi",
            "Bhairavnath", "Padmashree", "Dhanvantari", "Deccan Heritage", "Orchid Valley", "Trimurti",
            "Gurukul", "Shivneri", "Jagdamba", "Lotus Crest", "Ekta", "Swami Vivek", "Kaveri", "Brahmaputra",
            "Aravali", "Konark", "Chandragupta", "Vikram Sarabhai Memorial", "Tagore Heritage"]
TYPE_SUFFIX = {
    "Engineering": ["College of Engineering", "Institute of Technology", "College of Engineering & Technology",
                    "Institute of Engineering and Research", "Engineering College"],
    "Polytechnic": ["Polytechnic", "Institute of Polytechnic Education", "Technical Campus (Polytechnic)"],
    "Management": ["Institute of Management Studies", "Business School", "Institute of Management & Research",
                   "School of Management"],
}
TRUST_SUFFIX = ["Education Society", "Shikshan Sanstha", "Charitable Trust", "Vidya Prasarak Mandal",
                "Educational Foundation", "Shikshan Prasarak Mandal"]
FIRST = ["Rajesh", "Sunita", "Amit", "Priya", "Vikram", "Anjali", "Sanjay", "Meera", "Rahul", "Kavita", "Anil",
         "Pooja", "Suresh", "Neha", "Manoj", "Deepa", "Ashok", "Swati", "Prakash", "Rekha", "Nitin", "Shweta",
         "Dinesh", "Jyoti", "Harish", "Lata", "Mahesh", "Sarika", "Ganesh", "Vandana", "Ramesh", "Archana",
         "Santosh", "Madhuri", "Kiran", "Seema", "Vivek", "Rupali", "Yogesh", "Smita"]
LAST = ["Patil", "Deshmukh", "Kulkarni", "Joshi", "Sharma", "Verma", "Gupta", "Reddy", "Naidu", "Iyer", "Menon",
        "Nair", "Singh", "Chauhan", "Thakur", "Pawar", "Jadhav", "Shinde", "More", "Gaikwad", "Mishra", "Pandey",
        "Yadav", "Bhatt", "Mehta", "Shah", "Desai", "Rao", "Das", "Banerjee", "Ghosh", "Kumar", "Agarwal",
        "Chavan", "Kale", "Bose", "Pillai", "Hegde", "Naik", "Salunkhe"]
# (state, code, pin-first-digit, [cities])
LOCATIONS = [
    ("Maharashtra", "MH", "4", ["Pune", "Nashik", "Nagpur", "Satara", "Kolhapur", "Sangli", "Latur"]),
    ("Madhya Pradesh", "MP", "4", ["Indore", "Bhopal", "Jabalpur"]),
    ("Rajasthan", "RJ", "3", ["Jaipur", "Udaipur", "Kota"]),
    ("Uttar Pradesh", "UP", "2", ["Lucknow", "Kanpur", "Varanasi"]),
    ("Tamil Nadu", "TN", "6", ["Coimbatore", "Madurai", "Salem"]),
    ("Karnataka", "KA", "5", ["Belagavi", "Mysuru", "Hubballi"]),
    ("Telangana", "TS", "5", ["Warangal", "Karimnagar"]),
    ("Gujarat", "GJ", "3", ["Surat", "Rajkot", "Vadodara"]),
    ("Kerala", "KL", "6", ["Kochi", "Thrissur"]),
    ("Odisha", "OD", "7", ["Bhubaneswar", "Cuttack"]),
    ("Punjab", "PB", "1", ["Ludhiana", "Patiala"]),
    ("West Bengal", "WB", "7", ["Durgapur", "Siliguri"]),
    ("Chhattisgarh", "CG", "4", ["Raipur", "Bilaspur"]),
    ("Bihar", "BR", "8", ["Patna", "Gaya"]),
    ("Assam", "AS", "7", ["Guwahati", "Dibrugarh"]),
]
ROADS = ["Airport Road", "NH-{n} Bypass", "Ring Road", "Industrial Area Road", "Station Road", "Lake View Road",
         "Sector {n}", "Highway Service Road"]
BANKS = ["Sample National Bank", "Bharat Demo Bank", "Unity Test Cooperative Bank", "Example Commercial Bank"]

ENG_PROGS = ["B.Tech in Computer Science & Engineering", "B.Tech in Information Technology",
             "B.Tech in Artificial Intelligence & Data Science", "B.E. in Mechanical Engineering",
             "B.E. in Civil Engineering", "B.E. in Electrical Engineering",
             "B.E. in Electronics & Telecommunication Engineering"]
POLY_PROGS = ["Diploma in Computer Engineering", "Diploma in Mechanical Engineering", "Diploma in Civil Engineering",
              "Diploma in Electrical Engineering", "Diploma in Information Technology"]
MGMT_PROGS = [("MBA", "PG", 2), ("PGDM", "PG", 2), ("MCA", "PG", 2)]
ENG_LABS = ["Computer Programming Lab", "Physics Lab", "Chemistry Lab", "Electronics Lab", "Mechanical Workshop",
            "Electrical Machines Lab", "Civil Materials Lab", "Networking Lab", "Data Science Lab", "CAD/CAM Lab"]
DESIGNATIONS = ["Professor", "Associate Professor", "Assistant Professor", "Assistant Professor", "Lecturer"]
QUALS = ["Ph.D.", "M.Tech", "M.E.", "M.Tech", "MBA", "M.Sc.", "MCA"]

DOC_TYPES = ["application_form", "society_registration", "land_document", "building_plan_approval",
             "fire_safety_certificate", "noc_state_govt", "affiliation_letter", "bank_fdr_certificate",
             "audited_financials", "faculty_list", "infrastructure_report"]
SCAN_CANDIDATES = ["society_registration", "land_document", "fire_safety_certificate", "building_plan_approval",
                   "noc_state_govt", "bank_fdr_certificate"]

DATE_KEYS = {"application_date", "registration_date", "deed_date", "approval_date", "issue_date", "valid_to",
             "fdr_date", "maturity_date", "audit_date"}
MONEY_KEYS = {"fdr_amount", "total_income", "total_expenditure", "surplus"}
AREA_KEYS = {"land_area_sqm", "built_up_area_sqm"}


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def indian(n):
    s = str(abs(int(n)))
    if len(s) <= 3:
        return s
    head, tail, parts = s[:-3], s[-3:], []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def fmt(k, v):
    if k in DATE_KEYS:
        return dt.date.fromisoformat(v).strftime("%d/%m/%Y")
    if k in MONEY_KEYS:
        return "₹ " + indian(v)
    if k in AREA_KEYS:
        return f"{int(v):,} sq. m"
    return str(v)


def iso(d):
    return d.isoformat()


def person(rng):
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def slug(s):
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------
# Institution generation
# --------------------------------------------------------------------------------------
def make_institution(i, seed, used_names):
    rng = random.Random(f"{seed}:{i}")
    itype = rng.choices(["Engineering", "Polytechnic", "Management"], [55, 25, 20])[0]
    while True:
        name = f"{rng.choice(PREFIXES)} {rng.choice(TYPE_SUFFIX[itype])}"
        if name not in used_names:
            used_names.add(name)
            break
    state, scode, pin1, cities = rng.choice(LOCATIONS)
    city = rng.choice(cities)
    pincode = pin1 + "".join(str(rng.randint(0, 9)) for _ in range(5))
    road = rng.choice(ROADS).format(n=rng.randint(2, 66))
    address = f"Plot No. {rng.randint(1, 480)}, {road}, {city}, {state}"
    trust_base = rng.choice(PREFIXES) if rng.random() < .5 else rng.choice(LAST)
    trust = f"{trust_base} {rng.choice(TRUST_SUFFIX)}"

    if itype == "Engineering":
        names = rng.sample(ENG_PROGS, rng.randint(3, 5))
        programs = [dict(name=n, level="UG", years=4, intake=rng.choice([30, 60, 90, 120, 180])) for n in names]
    elif itype == "Polytechnic":
        names = rng.sample(POLY_PROGS, rng.randint(3, 4))
        programs = [dict(name=n, level="Diploma", years=3, intake=rng.choice([30, 60, 90])) for n in names]
    else:
        ch = rng.sample(MGMT_PROGS, rng.randint(1, 2))
        programs = [dict(name=n, level=l, years=y, intake=rng.choice([60, 120, 180])) for n, l, y in ch]
    total_intake = sum(p["intake"] for p in programs)
    students = sum(p["intake"] * p["years"] for p in programs)

    ratio = THRESHOLDS["max_students_per_faculty"][itype]
    faculty_count = math.ceil(students / ratio * rng.uniform(1.05, 1.35))
    land = int(THRESHOLDS["min_land_area_sqm"][itype] * rng.uniform(1.1, 2.2))
    builtup = int(round(students * rng.uniform(4, 6) / 10.0) * 10)
    fdr = int(round(THRESHOLDS["min_fdr_inr"][itype] * rng.uniform(1.05, 2.0), -3))

    app_date = dt.date(2025, 12, 1) + dt.timedelta(days=rng.randint(0, 88))
    reg_date = app_date - dt.timedelta(days=rng.randint(4 * 365, 20 * 365))
    inst = dict(
        app_id=f"SYN-APP-2026-{i + 1:04d}", institution_name=name, institution_type=itype, trust_name=trust,
        society_reg_no=f"SYN/{scode}/SOC/{reg_date.year}/{rng.randint(1000, 99999):05d}",
        society_reg_date=iso(reg_date),
        pan="".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(5)) + f"{rng.randint(0, 9999):04d}" +
            rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ"),
        address=address, city=city, state=state, state_code=scode, pincode=pincode,
        email=f"principal@{slug(name)[:30]}.example.org", phone=f"+91-9{rng.randint(100000000, 999999999)}",
        chairman=person(rng), principal=person(rng),
        year_established=min(2025, reg_date.year + rng.randint(0, 2)),
        academic_year="2026-27", application_date=iso(app_date),
        programs=programs, total_intake=total_intake, students=students,
        land_area_sqm=land, built_up_area_sqm=builtup, ownership=rng.choice(["Owned", "Owned", "Leased"]),
        survey_no=f"{rng.randint(1, 900)}/{rng.randint(1, 20)}", floors=rng.randint(2, 5),
        classrooms=max(6, int(total_intake / 30) + rng.randint(2, 8)),
        library_volumes=rng.randint(3000, 25000), computers=rng.randint(60, 400),
        bank=rng.choice(BANKS), branch=f"{city} Main", fdr_amount=fdr, faculty_count=faculty_count,
        auditor=f"{rng.choice(LAST)} & Associates", ca_membership=f"{rng.randint(100000, 999999)}",
        university=f"{state} Technical University",
    )
    return inst, rng


def build_docs(inst, rng):
    app = dt.date.fromisoformat(inst["application_date"])
    d = lambda days: iso(app - dt.timedelta(days=days))
    iname, trust, st, city = inst["institution_name"], inst["trust_name"], inst["state"], inst["city"]
    prog_rows = [[p["name"], p["level"], p["years"], p["intake"]] for p in inst["programs"]]
    docs = {}

    docs["application_form"] = dict(
        title="APPLICATION FOR APPROVAL OF INSTITUTION (SAMPLE FORM)", issuer=iname, issuer_addr=inst["address"],
        letterhead=True, ref_label="Application ID", ref_no=inst["app_id"], date_key="application_date",
        keys=dict(institution_name=iname, institution_type=inst["institution_type"], trust_name=trust,
                  society_reg_no=inst["society_reg_no"], pan=inst["pan"], address=inst["address"],
                  pincode=inst["pincode"], state=st, year_established=inst["year_established"],
                  principal=inst["principal"], email=inst["email"], phone=inst["phone"],
                  total_intake=inst["total_intake"], faculty_count=inst["faculty_count"],
                  land_area_sqm=inst["land_area_sqm"], built_up_area_sqm=inst["built_up_area_sqm"],
                  application_date=inst["application_date"], academic_year=inst["academic_year"]),
        labels=dict(institution_name="Name of Institution", institution_type="Type of Institution",
                    trust_name="Name of Trust / Society", society_reg_no="Society Registration No.", pan="PAN of Trust",
                    address="Address", pincode="PIN Code", state="State", year_established="Year of Establishment",
                    principal="Principal / Director", email="Email", phone="Phone", total_intake="Total Annual Intake",
                    faculty_count="Total Faculty (declared)", land_area_sqm="Total Land Area",
                    built_up_area_sqm="Total Built-up Area", application_date="Date of Application",
                    academic_year="Academic Year"),
        body=["The undersigned applies for approval of the programmes listed below for the academic year "
              "{academic_year}. All particulars in this sample form are fictional."],
        table=dict(headers=["Programme", "Level", "Duration (yrs)", "Intake"], rows=prog_rows, widths=[240, 70, 90, 60]))

    docs["society_registration"] = dict(
        title="CERTIFICATE OF REGISTRATION OF SOCIETY / TRUST", issuer=f"Registrar of Societies, {st} (Fictional)",
        issuer_addr=f"Registrar Office, {city}", ref_label="Registration No.", ref_no=inst["society_reg_no"],
        date_key="registration_date",
        keys=dict(trust_name=trust, society_reg_no=inst["society_reg_no"], registration_date=inst["society_reg_date"],
                  registered_office=inst["address"], chairman=inst["chairman"], institution_name=iname),
        labels=dict(trust_name="Name of Society / Trust", society_reg_no="Registration Number",
                    registration_date="Date of Registration", registered_office="Registered Office",
                    chairman="Chairman / President", institution_name="Institution Managed"),
        body=["This is to certify that {trust_name} has been registered as an educational society/trust with "
              "Registration No. {society_reg_no} on {registration_date}. Its objects include establishing and "
              "managing {institution_name}."])

    docs["land_document"] = dict(
        title=f"LAND RECORD EXTRACT / {inst['ownership'].upper()} DEED", issuer=f"Revenue Department, {city} District, {st} (Fictional)",
        issuer_addr=f"Tehsil Office, {city}", ref_label="Survey / Record No.", ref_no=inst["survey_no"],
        date_key="deed_date",
        keys=dict(trust_name=trust, survey_no=inst["survey_no"], land_area_sqm=inst["land_area_sqm"],
                  ownership_type=inst["ownership"], location=inst["address"], pincode=inst["pincode"],
                  deed_date=d(rng.randint(400, 2500))),
        labels=dict(trust_name="Owner / Lessee", survey_no="Survey No.", land_area_sqm="Area of Land",
                    ownership_type="Nature of Holding", location="Location of Land", pincode="PIN Code",
                    deed_date="Date of Record / Deed"),
        body=["The land described above is recorded in the name of {trust_name} as {ownership_type} "
              "holding, measuring {land_area_sqm}."])

    docs["building_plan_approval"] = dict(
        title="BUILDING PLAN APPROVAL CERTIFICATE", issuer=f"Town Planning Authority, {city} (Fictional)",
        issuer_addr=f"Civic Centre, {city}", ref_label="Plan Approval No.", ref_no=f"TPA/{inst['state_code']}/{rng.randint(1000, 99999)}",
        date_key="approval_date",
        keys=dict(institution_name=iname, plan_no="", approval_date=d(rng.randint(100, 700)),
                  land_area_sqm=inst["land_area_sqm"], built_up_area_sqm=inst["built_up_area_sqm"],
                  floors=inst["floors"], pincode=inst["pincode"]),
        labels=dict(institution_name="Applicant Institution", plan_no="Plan No.", approval_date="Date of Approval",
                    land_area_sqm="Plot Area", built_up_area_sqm="Approved Built-up Area", floors="Number of Floors",
                    pincode="PIN Code"),
        body=["The building plan submitted for {institution_name} is approved for the plot area and built-up area "
              "stated above, subject to the usual conditions."])
    docs["building_plan_approval"]["keys"]["plan_no"] = docs["building_plan_approval"]["ref_no"]

    fi = dt.date.fromisoformat(d(rng.randint(30, 700)))
    docs["fire_safety_certificate"] = dict(
        title="FIRE SAFETY CERTIFICATE", issuer=f"Directorate of Fire & Emergency Services, {st} (Fictional)",
        issuer_addr=f"Fire Station Complex, {city}", ref_label="Certificate No.", ref_no=f"FIRE/{inst['state_code']}/{rng.randint(10000, 99999)}",
        date_key="issue_date",
        keys=dict(institution_name=iname, cert_no="", address=inst["address"], pincode=inst["pincode"],
                  issue_date=iso(fi), valid_to=iso(fi + dt.timedelta(days=1095))),
        labels=dict(institution_name="Premises Name", cert_no="Certificate No.", address="Premises Address",
                    pincode="PIN Code", issue_date="Date of Issue", valid_to="Valid Up To"),
        body=["The premises of {institution_name} were inspected and found to meet the fire safety requirements "
              "in force. This certificate is valid from {issue_date} to {valid_to}."])
    docs["fire_safety_certificate"]["keys"]["cert_no"] = docs["fire_safety_certificate"]["ref_no"]

    docs["noc_state_govt"] = dict(
        title="ESSENTIALITY / NO OBJECTION CERTIFICATE", issuer=f"Department of Higher & Technical Education, {st} (Fictional)",
        issuer_addr="State Secretariat (Fictional)", ref_label="Certificate No.", ref_no=f"ESS/{inst['state_code']}/{rng.randint(1000, 99999)}",
        date_key="issue_date",
        keys=dict(institution_name=iname, trust_name=trust, noc_no="", issue_date=d(rng.randint(30, 300)),
                  total_intake=inst["total_intake"], academic_year=inst["academic_year"]),
        labels=dict(institution_name="Institution", trust_name="Sponsoring Trust / Society", noc_no="Certificate No.",
                    issue_date="Date of Issue", total_intake="Total Intake Covered", academic_year="Academic Year"),
        body=["The State Government has no objection to the establishment of {institution_name}, sponsored by "
              "{trust_name}, for the programmes below in academic year {academic_year}."],
        table=dict(headers=["Programme", "Level", "Duration (yrs)", "Intake"], rows=[r[:] for r in prog_rows], widths=[240, 70, 90, 60]))
    docs["noc_state_govt"]["keys"]["noc_no"] = docs["noc_state_govt"]["ref_no"]

    docs["affiliation_letter"] = dict(
        title="LETTER OF AFFILIATION / CONDITIONAL AFFILIATION", issuer=f"{inst['university']} (Fictional)",
        issuer_addr=f"University Campus, {city}", ref_label="Affiliation No.", ref_no=f"AFF/{inst['state_code']}/{rng.randint(1000, 99999)}",
        date_key="issue_date",
        keys=dict(institution_name=iname, affiliation_no="", issue_date=d(rng.randint(15, 200)),
                  valid_for_ay=inst["academic_year"], total_intake=inst["total_intake"]),
        labels=dict(institution_name="Affiliated Institution", affiliation_no="Affiliation No.", issue_date="Date of Issue",
                    valid_for_ay="Valid for Academic Year", total_intake="Total Sanctioned Intake"),
        body=["Affiliation is granted to {institution_name} for academic year {valid_for_ay} for the programmes "
              "and intake given below."],
        table=dict(headers=["Programme", "Level", "Duration (yrs)", "Intake"], rows=[r[:] for r in prog_rows], widths=[240, 70, 90, 60]))
    docs["affiliation_letter"]["keys"]["affiliation_no"] = docs["affiliation_letter"]["ref_no"]

    fd = dt.date.fromisoformat(d(rng.randint(30, 400)))
    docs["bank_fdr_certificate"] = dict(
        title="FIXED DEPOSIT RECEIPT / BANK CERTIFICATE", issuer=f"{inst['bank']} (Fictional)",
        issuer_addr=f"{inst['branch']} Branch", ref_label="FDR No.", ref_no=f"FDR{rng.randint(10000000, 99999999)}",
        date_key="fdr_date",
        keys=dict(trust_name=trust, institution_name=iname, fdr_no="", fdr_amount=inst["fdr_amount"],
                  fdr_date=iso(fd), maturity_date=iso(fd + dt.timedelta(days=rng.randint(3, 5) * 365)),
                  bank=inst["bank"], branch=inst["branch"]),
        labels=dict(trust_name="Depositor", institution_name="Purpose (Institution)", fdr_no="FDR Number",
                    fdr_amount="Deposit Amount", fdr_date="Date of Deposit", maturity_date="Maturity Date",
                    bank="Bank", branch="Branch"),
        body=["This is to certify that {trust_name} holds a fixed deposit of {fdr_amount} for {institution_name}. "
              "A lien is marked in favour of the approving authority (sample wording)."])
    docs["bank_fdr_certificate"]["keys"]["fdr_no"] = docs["bank_fdr_certificate"]["ref_no"]

    income = rng.randint(8, 60) * 1000000
    spend = int(income * rng.uniform(0.7, 0.95))
    docs["audited_financials"] = dict(
        title="AUDITED INCOME & EXPENDITURE STATEMENT", issuer=f"{inst['auditor']}, Chartered Accountants (Fictional)",
        issuer_addr=f"{city}", ref_label="UDIN", ref_no=f"SYNUDIN{rng.randint(10**9, 10**10 - 1)}", date_key="audit_date",
        keys=dict(trust_name=trust, institution_name=iname, financial_year="2024-25", total_income=income,
                  total_expenditure=spend, surplus=income - spend, udin="", audit_date=f"2025-{rng.randint(8, 10):02d}-{rng.randint(1, 28):02d}",
                  membership_no=inst["ca_membership"]),
        labels=dict(trust_name="Entity Audited", institution_name="Institution", financial_year="Financial Year",
                    total_income="Total Income", total_expenditure="Total Expenditure", surplus="Surplus / (Deficit)",
                    udin="UDIN", audit_date="Date of Audit Report", membership_no="Membership No."),
        body=["We have audited the accounts of {trust_name} for the year {financial_year}, in respect of "
              "{institution_name}. The summary below is a fictional sample."],
        table=dict(headers=["Head", "Amount"], widths=[300, 160], rows=[
            ["Tuition & Other Fees", "₹ " + indian(int(income * .82))], ["Grants / Donations", "₹ " + indian(int(income * .18))],
            ["Salaries & Allowances", "₹ " + indian(int(spend * .6))], ["Maintenance & Utilities", "₹ " + indian(int(spend * .25))],
            ["Other Expenses", "₹ " + indian(spend - int(spend * .6) - int(spend * .25))]]))
    docs["audited_financials"]["keys"]["udin"] = docs["audited_financials"]["ref_no"]

    depts = sorted({p["name"].split(" in ")[-1] for p in inst["programs"]})
    frows = []
    for n in range(inst["faculty_count"]):
        des = rng.choice(DESIGNATIONS)
        frows.append([f"{n + 1}", person(rng), des, rng.choice(QUALS), rng.choice(depts), f"{rng.randint(1, 28)}"])
    docs["faculty_list"] = dict(
        title="LIST OF FACULTY", issuer=iname, issuer_addr=inst["address"], letterhead=True,
        ref_label="Application ID", ref_no=inst["app_id"], date_key=None,
        keys=dict(institution_name=iname, faculty_count=inst["faculty_count"], academic_year=inst["academic_year"]),
        labels=dict(institution_name="Institution", faculty_count="Total Faculty Listed", academic_year="Academic Year"),
        body=["Faculty details below are entirely fictional."],
        table=dict(headers=["#", "Name", "Designation", "Qualification", "Department", "Exp (yrs)"],
                   widths=[24, 110, 100, 70, 130, 44], rows=frows))

    labs = rng.sample(ENG_LABS, min(len(ENG_LABS), rng.randint(4, 8)))
    docs["infrastructure_report"] = dict(
        title="INFRASTRUCTURE & LABORATORY DETAILS", issuer=iname, issuer_addr=inst["address"], letterhead=True,
        ref_label="Application ID", ref_no=inst["app_id"], date_key=None,
        keys=dict(institution_name=iname, built_up_area_sqm=inst["built_up_area_sqm"], classrooms=inst["classrooms"],
                  laboratories=len(labs), library_volumes=inst["library_volumes"], computers=inst["computers"]),
        labels=dict(institution_name="Institution", built_up_area_sqm="Total Built-up Area", classrooms="Classrooms",
                    laboratories="Laboratories", library_volumes="Library Volumes", computers="Computers"),
        body=["The laboratories below are provided for {institution_name}. Figures are fictional."],
        table=dict(headers=["Laboratory", "Area (sq. m)", "Capacity"], widths=[260, 100, 100],
                   rows=[[l, str(rng.randint(60, 180)), str(rng.choice([30, 40, 60]))] for l in labs]))
    return docs


# --------------------------------------------------------------------------------------
# Anomaly injection
# --------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, inst, docs, rng):
        self.inst, self.docs, self.rng = inst, docs, rng
        self.touched, self.dups, self.missing = set(), [], []

    def pick(self, key, among=None):
        c = [d for d, sp in self.docs.items() if key in sp["keys"] and d not in self.touched
             and (among is None or d in among)]
        return self.rng.choice(c) if c else None

    def set(self, doc, key, new):
        old = self.docs[doc]["keys"][key]
        self.docs[doc]["keys"][key] = new
        self.touched.add(doc)
        return dict(doc_type=doc, field=key, expected_value=old, injected_value=new)


def mutate_name(name, rng):
    opts = []
    for a, b in [("Shri", "Shree"), ("Sant", "Saint"), ("Engineering", "Engg."), (" & ", " and "),
                 ("Institute", "Inst."), ("Technology", "Tech")]:
        if a in name:
            opts.append(name.replace(a, b, 1))
    words = name.split()
    if len(words) > 3:
        opts.append(" ".join(words[:-1]))
    w = rng.randrange(len(words))
    if len(words[w]) > 4:
        j = rng.randrange(1, len(words[w]) - 2)
        t = list(words[w]); t[j], t[j + 1] = t[j + 1], t[j]
        opts.append(" ".join(words[:w] + ["".join(t)] + words[w + 1:]))
    opts = [o for o in opts if o != name]
    return rng.choice(opts) if opts else name + " Pvt"


def a_name(c):
    d = c.pick("institution_name", [x for x in DOC_TYPES if x != "application_form"])
    if not d: return None
    new = mutate_name(c.docs[d]["keys"]["institution_name"], c.rng)
    return [c.set(d, "institution_name", new)]


def a_trust(c):
    d = c.pick("trust_name")
    if not d: return None
    old = c.docs[d]["keys"]["trust_name"]
    words = old.split()
    new = " ".join(words[:-2] + [c.rng.choice(LAST)] + words[-1:]) if len(words) > 2 else old + " Trust"
    if new == old: new = old + " (Regd.)"
    return [c.set(d, "trust_name", new)]


def a_regno(c):
    d = c.pick("society_reg_no", ["society_registration"])
    if not d: return None
    old = c.docs[d]["keys"]["society_reg_no"]
    head, num = old.rsplit("/", 1)
    new = f"{head}/{(int(num) + c.rng.randint(11, 900)) % 100000:05d}"
    return [c.set(d, "society_reg_no", new)]


def _shrink(v, rng): return int(round(v * rng.uniform(0.78, 0.9), -1))


def a_land(c):
    d = c.pick("land_area_sqm", ["land_document", "building_plan_approval"])
    if not d: return None
    return [c.set(d, "land_area_sqm", _shrink(c.docs[d]["keys"]["land_area_sqm"], c.rng))]


def a_builtup(c):
    d = c.pick("built_up_area_sqm", ["building_plan_approval", "infrastructure_report"])
    if not d: return None
    return [c.set(d, "built_up_area_sqm", _shrink(c.docs[d]["keys"]["built_up_area_sqm"], c.rng))]


def a_intake(c):
    d = c.pick("total_intake", ["noc_state_govt", "affiliation_letter"])
    if not d: return None
    sp = c.docs[d]
    delta = c.rng.choice([30, 60, -30])
    row = sp["table"]["rows"][0]
    if row[3] + delta <= 0: delta = 30
    row[3] += delta
    return [c.set(d, "total_intake", sp["keys"]["total_intake"] + delta)]


def a_faculty_mismatch(c):
    if "application_form" in c.touched: return None
    k = c.docs["application_form"]["keys"]
    new = max(5, int(k["faculty_count"] * c.rng.choice([1.25, 1.4])))
    if new == k["faculty_count"]: new += 3
    return [c.set("application_form", "faculty_count", new)]


def a_fire_expired(c):
    d = "fire_safety_certificate"
    if d in c.touched: return None
    app = dt.date.fromisoformat(c.inst["application_date"])
    vt = app - dt.timedelta(days=c.rng.randint(10, 300))
    e1 = c.set(d, "valid_to", iso(vt))
    e2 = c.set(d, "issue_date", iso(vt - dt.timedelta(days=1095)))
    return [e1, e2]


def a_future(c):
    d = c.pick("approval_date", ["building_plan_approval"]) or c.pick("issue_date", ["noc_state_govt"])
    if not d: return None
    key = "approval_date" if d == "building_plan_approval" else "issue_date"
    app = dt.date.fromisoformat(c.inst["application_date"])
    return [c.set(d, key, iso(app + dt.timedelta(days=c.rng.randint(30, 200))))]


def a_fdr_low(c):
    d = c.pick("fdr_amount", ["bank_fdr_certificate"])
    if not d: return None
    thr = THRESHOLDS["min_fdr_inr"][c.inst["institution_type"]]
    return [c.set(d, "fdr_amount", int(round(thr * c.rng.uniform(0.4, 0.7), -3)))]


def a_fdr_matured(c):
    d = c.pick("maturity_date", ["bank_fdr_certificate"])
    if not d: return None
    app = dt.date.fromisoformat(c.inst["application_date"])
    m = app - dt.timedelta(days=c.rng.randint(10, 120))
    e1 = c.set(d, "maturity_date", iso(m))
    e2 = c.set(d, "fdr_date", iso(m - dt.timedelta(days=c.rng.randint(3, 4) * 365)))
    return [e1, e2]


def a_ratio(c):
    if {"application_form", "faculty_list"} & c.touched: return None
    thr = THRESHOLDS["max_students_per_faculty"][c.inst["institution_type"]]
    new = max(3, int(c.inst["students"] / thr * 0.6))
    c.docs["faculty_list"]["table"]["rows"] = c.docs["faculty_list"]["table"]["rows"][:new]
    return [c.set("application_form", "faculty_count", new), c.set("faculty_list", "faculty_count", new)]


def a_pin(c):
    d = c.pick("pincode", ["land_document", "building_plan_approval", "fire_safety_certificate"])
    if not d: return None
    old = c.docs[d]["keys"]["pincode"]
    new = old[0] + "".join(str(c.rng.randint(0, 9)) for _ in range(5))
    if new == old: new = old[0] + str((int(old[1:]) + 7919) % 100000).zfill(5)
    return [c.set(d, "pincode", new)]


def a_land_min(c):
    if {"application_form", "land_document", "building_plan_approval"} & c.touched: return None
    thr = THRESHOLDS["min_land_area_sqm"][c.inst["institution_type"]]
    new = int(thr * c.rng.uniform(0.35, 0.8))
    return [c.set(d, "land_area_sqm", new) for d in ("application_form", "land_document", "building_plan_approval")]


def a_pan(c):
    if "application_form" in c.touched: return None
    old = c.docs["application_form"]["keys"]["pan"]
    new = c.rng.choice([old[:-1], old.lower(), old[:5] + old[5:9] + "1", old[:3] + old[4:]])
    return [c.set("application_form", "pan", new)]


def a_missing(c):
    cand = [d for d in DOC_TYPES if d not in c.touched and d in c.docs]
    if not cand: return None
    d = c.rng.choice(cand)
    c.touched.add(d); c.missing.append(d); del c.docs[d]
    return [dict(doc_type=d, field="(document)", expected_value="present", injected_value="absent")]


def a_dup(c):
    cand = [d for d in DOC_TYPES if d not in c.touched and d in c.docs]
    if len(cand) < 2: return None
    src, tgt = c.rng.sample(cand, 2)
    c.touched.update([src, tgt]); c.dups.append((src, tgt))
    return [dict(doc_type=tgt, field="(file content)", expected_value=f"unique {tgt}",
                 injected_value=f"byte-identical copy of {src}")]


# (type, fn, rule_id, severity, description)
ANOMALIES = [
    ("MISSING_DOCUMENT", a_missing, "R001", "critical", "A required document is absent from the application"),
    ("DUPLICATE_FILE", a_dup, "R002", "high", "Same file submitted under two different document types"),
    ("INSTITUTION_NAME_MISMATCH", a_name, "R003", "medium", "Institution name differs from the application form"),
    ("TRUST_NAME_MISMATCH", a_trust, "R004", "high", "Trust/society name differs across documents"),
    ("SOCIETY_REG_NO_MISMATCH", a_regno, "R005", "high", "Society registration number differs from application form"),
    ("LAND_AREA_MISMATCH", a_land, "R006", "high", "Land area differs between application and supporting document"),
    ("BUILT_UP_AREA_MISMATCH", a_builtup, "R007", "medium", "Built-up area differs between application and supporting document"),
    ("INTAKE_MISMATCH", a_intake, "R008", "high", "Programme intake differs from application form"),
    ("FACULTY_COUNT_MISMATCH", a_faculty_mismatch, "R009", "medium", "Declared faculty count differs from faculty list"),
    ("FIRE_CERT_EXPIRED", a_fire_expired, "R010", "high", "Fire safety certificate expired before the application date"),
    ("FUTURE_DATED_DOCUMENT", a_future, "R011", "high", "Document is dated after the application date"),
    ("FDR_BELOW_THRESHOLD", a_fdr_low, "R012", "high", "Deposit is below the configured placeholder threshold"),
    ("FDR_MATURED", a_fdr_matured, "R013", "high", "Fixed deposit matured before the application date"),
    ("FACULTY_RATIO_EXCEEDED", a_ratio, "R014", "high", "Students per faculty exceeds configured placeholder limit"),
    ("PINCODE_MISMATCH", a_pin, "R015", "low", "PIN code differs from application form"),
    ("LAND_BELOW_MINIMUM", a_land_min, "R016", "high", "Land area below configured placeholder minimum (consistent across documents)"),
    ("PAN_FORMAT_INVALID", a_pan, "R017", "medium", "PAN does not match the AAAAA9999A format"),
]
LAST_STAGE = {"DUPLICATE_FILE", "MISSING_DOCUMENT"}


def plan_anomalies(i, forced, rng):
    k = rng.choices([0, 1, 2, 3], [35, 35, 20, 10])[0]
    idx = rng.sample(range(len(ANOMALIES)), k)
    if forced is not None:
        if forced in idx: pass
        elif idx: idx[0] = forced
        else: idx = [forced]
    return sorted(idx, key=lambda j: ANOMALIES[j][0] in LAST_STAGE)


# --------------------------------------------------------------------------------------
# PDF rendering
# --------------------------------------------------------------------------------------
def seal(c, cx, cy, r, rng_seed=0):
    c.saveState(); c.setStrokeColor(colors.HexColor("#1f3a8a")); c.setFillColor(colors.HexColor("#1f3a8a"))
    c.setStrokeAlpha(.8); c.setFillAlpha(.8)
    c.setLineWidth(1.4); c.circle(cx, cy, r, stroke=1, fill=0); c.setLineWidth(.5); c.circle(cx, cy, r - 4, stroke=1, fill=0)
    c.setFont("DV-B", r / 4.2); c.drawCentredString(cx, cy + 3, "SYNTHETIC"); c.drawCentredString(cx, cy - r / 4, "SEAL")
    c.restoreState()


def render_pdf(path, spec, doc_id, logo_path, inst):
    keys = spec["keys"]
    fm = {k: fmt(k, v) for k, v in keys.items()}
    rng = random.Random(doc_id)
    c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    c.setTitle(spec["title"]); c.setAuthor("Synthetic Dataset Generator (fictional)")
    c.setSubject("SYNTHETIC - NOT AN OFFICIAL DOCUMENT"); c.setCreator("generate_dataset.py " + GENERATOR_VERSION)
    M, st = 50, {"y": 0, "page": 1}

    def chrome():
        c.setStrokeColor(colors.HexColor("#444444")); c.setLineWidth(1.2); c.rect(30, 30, W - 60, H - 60)
        c.setLineWidth(.4); c.rect(34, 34, W - 68, H - 68)
        c.saveState(); c.setFillColor(colors.grey); c.setFillAlpha(.13); c.translate(W / 2, H / 2); c.rotate(42)
        c.setFont("DV-B", 30); c.drawCentredString(0, 0, WATERMARK); c.restoreState()
        c.setFont("DV", 6.5); c.setFillColor(colors.HexColor("#555555"))
        c.drawString(M, 40, f"SYNTHETIC DATA - FICTIONAL - NOT AN OFFICIAL DOCUMENT  |  Doc ID: {doc_id}")
        c.drawRightString(W - M, 40, f"Page {st['page']}")

    def header():
        top = H - 52
        if spec.get("letterhead") and logo_path:
            c.drawImage(str(logo_path), M, top - 62, 62, 62, mask="auto")
        else:
            seal(c, M + 31, top - 31, 29)
        c.setFillColor(colors.HexColor("#111111")); c.setFont("DVS-B", 13)
        y = top - 12
        for ln in simpleSplit(spec["issuer"], "DVS-B", 13, W - 2 * M - 160):
            c.drawCentredString(W / 2 + 25, y, ln); y -= 16
        c.setFont("DV", 8); c.drawCentredString(W / 2 + 25, y - 1, spec["issuer_addr"])
        c.setFont("DV-I", 6.5); c.setFillColor(colors.HexColor("#a02020"))
        c.drawCentredString(W / 2 + 25, y - 12, "Generated for software testing. Not issued by any real authority.")
        c.setFillColor(colors.black)
        c.setStrokeColor(colors.HexColor("#222222")); c.setLineWidth(.8); c.line(M, top - 72, W - M, top - 72)
        return top - 92

    def new_page(first=False):
        if not first:
            c.showPage(); st["page"] += 1
        chrome()
        st["y"] = header() if first else H - 70

    def ensure(space):
        if st["y"] - space < 75:
            new_page()

    new_page(True)
    c.setFont("DV-B", 11.5)
    for ln in simpleSplit(spec["title"], "DV-B", 11.5, W - 2 * M):
        c.drawCentredString(W / 2, st["y"], ln); st["y"] -= 15
    st["y"] -= 6
    c.setFont("DV", 8.5)
    c.drawString(M, st["y"], f"{spec['ref_label']}: {spec['ref_no']}")
    if spec.get("date_key"):
        c.drawRightString(W - M, st["y"], f"Date: {fm[spec['date_key']]}")
    st["y"] -= 18

    # key-value table
    lw, vw = 175, W - 2 * M - 175
    for k, v in fm.items():
        label = spec["labels"].get(k, k)
        lines = simpleSplit(v, "DV", 8.5, vw - 10) or [""]
        h = max(18, len(lines) * 11 + 7)
        ensure(h)
        y0 = st["y"]
        c.setStrokeColor(colors.HexColor("#999999")); c.setLineWidth(.4)
        c.setFillColor(colors.HexColor("#f1f1f1")); c.rect(M, y0 - h, lw, h, fill=1)
        c.setFillColor(colors.white); c.rect(M + lw, y0 - h, vw, h, fill=1)
        c.setFillColor(colors.black); c.setFont("DV-B", 8); c.drawString(M + 5, y0 - 12, label)
        c.setFont("DV", 8.5)
        for n, ln in enumerate(lines):
            c.drawString(M + lw + 5, y0 - 12 - n * 11, ln)
        st["y"] -= h
    st["y"] -= 14

    # body
    for p in spec.get("body", []):
        text = p.format(**fm)
        for ln in simpleSplit(text, "DV", 9, W - 2 * M):
            ensure(14); c.setFont("DV", 9); c.setFillColor(colors.black); c.drawString(M, st["y"], ln); st["y"] -= 13
        st["y"] -= 6

    # data table
    tb = spec.get("table")
    if tb:
        widths = tb["widths"]
        def draw_row(cells, bold=False, fill=None):
            wrapped = [simpleSplit(str(x), "DV-B" if bold else "DV", 8, widths[j] - 8) or [""] for j, x in enumerate(cells)]
            h = max(len(w) for w in wrapped) * 10 + 8
            ensure(h)
            x, y0 = M, st["y"]
            for j, w in enumerate(wrapped):
                c.setStrokeColor(colors.HexColor("#888888")); c.setLineWidth(.4)
                c.setFillColor(fill or colors.white); c.rect(x, y0 - h, widths[j], h, fill=1)
                c.setFillColor(colors.black); c.setFont("DV-B" if bold else "DV", 8)
                for n, ln in enumerate(w):
                    c.drawString(x + 4, y0 - 11 - n * 10, ln)
                x += widths[j]
            st["y"] -= h
        draw_row(tb["headers"], True, colors.HexColor("#dde4f0"))
        for r in tb["rows"]:
            if st["y"] - 20 < 75:
                new_page(); draw_row(tb["headers"], True, colors.HexColor("#dde4f0"))
            draw_row(r)
        st["y"] -= 16

    # signature block + QR
    ensure(110)
    y0 = st["y"] - 70
    p = c.beginPath(); sx = W - M - 190; p.moveTo(sx, y0)
    for n in range(6):
        p.curveTo(sx + n * 14 + rng.uniform(0, 6), y0 + rng.uniform(-14, 14), sx + n * 14 + 8, y0 + rng.uniform(-16, 16),
                  sx + (n + 1) * 14, y0 + rng.uniform(-6, 6))
    c.setStrokeColor(colors.HexColor("#1a2a8c")); c.setLineWidth(1.1); c.drawPath(p, stroke=1, fill=0)
    c.setFillColor(colors.black); c.setFont("DV", 8)
    c.drawString(sx, y0 - 16, "Authorised Signatory (synthetic scribble)")
    c.drawString(sx, y0 - 27, f"Place: {inst['city']}")
    seal(c, M + 160, y0 + 8, 30)
    w = qr.QrCodeWidget(f"{doc_id}|SYNTHETIC"); b = w.getBounds()
    d = Drawing(54, 54, transform=[54. / (b[2] - b[0]), 0, 0, 54. / (b[3] - b[1]), 0, 0]); d.add(w)
    renderPDF.draw(d, c, M, y0 - 24)
    c.showPage(); c.save()
    return st["page"]


# --------------------------------------------------------------------------------------
# Image generation (logos, campus photos, scans)
# --------------------------------------------------------------------------------------
def make_logo(path, inst, rng):
    S = 256
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    col = tuple(rng.randint(20, 150) for _ in range(3)); col2 = tuple(rng.randint(120, 230) for _ in range(3))
    d.ellipse([6, 6, S - 6, S - 6], fill=col2, outline=col, width=10)
    shape = rng.choice(["tri", "sq", "diamond", "star"])
    cx = cy = S // 2
    if shape == "tri": d.polygon([(cx, 40), (S - 50, S - 90), (50, S - 90)], fill=col)
    elif shape == "sq": d.rectangle([60, 60, S - 60, S - 110], fill=col)
    elif shape == "diamond": d.polygon([(cx, 38), (S - 44, cy - 20), (cx, S - 100), (44, cy - 20)], fill=col)
    else:
        pts = []
        for k in range(10):
            r = 78 if k % 2 == 0 else 34; a = math.pi / 5 * k - math.pi / 2
            pts.append((cx + r * math.cos(a), 108 + r * math.sin(a)))
        d.polygon(pts, fill=col)
    ini = "".join(w[0] for w in inst["institution_name"].replace("&", "").split() if w[0].isupper())[:4]
    f = pil_font(46 if len(ini) < 4 else 36, True)
    tw = d.textlength(ini, font=f)
    d.text(((S - tw) / 2, 168), ini, font=f, fill=col)
    d.text((70, 226), "SYNTHETIC", font=pil_font(14, True), fill=(90, 90, 90))
    im.save(path)


def _noise(im, nprng, sigma):
    a = np.asarray(im).astype(np.int16) + nprng.normal(0, sigma, np.asarray(im).shape).astype(np.int16)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _fit_text(d, text, maxw, size, bold=True):
    while size > 10 and d.textlength(text, font=pil_font(size, bold)) > maxw:
        size -= 1
    return pil_font(size, bold)


def make_campus(path, inst, rng, nprng, kind):
    Wd, Ht = 960, 600
    im = Image.new("RGB", (Wd, Ht)); d = ImageDraw.Draw(im)
    if kind == "campus_front":
        gy = int(Ht * .64)
        top = (rng.randint(80, 130), rng.randint(150, 190), rng.randint(215, 250))
        for y in range(gy):
            t = y / gy; d.line([(0, y), (Wd, y)], fill=tuple(int(top[j] * (1 - t) + (220, 238, 250)[j] * t) for j in range(3)))
        d.ellipse([Wd - 150, 40, Wd - 90, 100], fill=(255, 240, 170))
        d.rectangle([0, gy, Wd, Ht], fill=(108, 158, 92))
        d.polygon([(Wd * .38, gy + 6), (Wd * .62, gy + 6), (Wd * .95, Ht), (Wd * .05, Ht)], fill=(96, 96, 102))
        bc = rng.choice([(196, 150, 110), (210, 190, 160), (170, 90, 80), (200, 200, 205), (230, 215, 175)])
        bx0, bx1, by0 = 140, 820, 150
        d.rectangle([bx0, by0, bx1, gy + 4], fill=bc, outline=(70, 60, 50), width=3)
        d.rectangle([bx0 - 10, by0 - 16, bx1 + 10, by0], fill=tuple(max(0, v - 50) for v in bc))
        floors = min(4, inst["floors"] - 0)
        fh = (gy - by0 - 40) // floors
        for fl in range(floors):
            for col in range(10):
                wx = bx0 + 24 + col * 66; wy = by0 + 16 + fl * fh
                d.rectangle([wx, wy, wx + 40, wy + fh - 28], fill=(150, 195, 225), outline=(245, 245, 245), width=3)
                d.line([(wx + 20, wy), (wx + 20, wy + fh - 28)], fill=(245, 245, 245), width=2)
        d.rectangle([Wd // 2 - 55, gy - 78, Wd // 2 + 55, gy + 4], fill=(70, 50, 40))
        d.rectangle([Wd // 2 - 80, gy + 4, Wd // 2 + 80, gy + 18], fill=(190, 190, 190))
        sb = (Wd // 2 - 270, by0 + 8, Wd // 2 + 270, by0 + 52)
        d.rectangle(sb, fill=(20, 40, 100), outline=(255, 255, 255), width=3)
        nm = inst["institution_name"].upper()
        f = _fit_text(d, nm, 500, 24)
        d.text((Wd // 2 - d.textlength(nm, font=f) / 2, by0 + 16), nm, font=f, fill=(255, 255, 255))
        for tx in [60, 90, 890, 925, 40]:
            d.rectangle([tx - 5, gy - 30, tx + 5, gy + 8], fill=(90, 60, 40))
            d.ellipse([tx - 36, gy - 90, tx + 36, gy - 12], fill=(40, rng.randint(110, 150), 50))
        d.line([(Wd - 200, gy + 6), (Wd - 200, 190)], fill=(230, 230, 230), width=4)
        d.rectangle([Wd - 198, 192, Wd - 150, 214], fill=(255, 153, 51))
    elif kind == "computer_lab":
        d.rectangle([0, 0, Wd, Ht], fill=(228, 230, 235))
        d.rectangle([0, 380, Wd, Ht], fill=(170, 165, 155))
        for lx in range(80, Wd, 200):
            d.rectangle([lx, 20, lx + 120, 34], fill=(255, 255, 235))
        d.rectangle([300, 70, 660, 150], fill=(30, 70, 50), outline=(120, 90, 60), width=6)
        t = "COMPUTER LAB"; f = pil_font(30, True)
        d.text((480 - d.textlength(t, font=f) / 2, 94), t, font=f, fill=(240, 240, 240))
        for row in range(3):
            y = 230 + row * 110; sc = 1 + row * .25
            d.rectangle([60, y + 55 * sc, Wd - 60, y + 70 * sc], fill=(120, 90, 60))
            for n in range(6):
                x = 100 + n * 140
                d.rectangle([x, y, x + 70 * sc, y + 45 * sc], fill=(30, 35, 50), outline=(15, 15, 15), width=3)
                d.rectangle([x + 6, y + 6, x + 70 * sc - 6, y + 45 * sc - 6], fill=(60, 120, 190))
                d.rectangle([x + 28 * sc, y + 45 * sc, x + 42 * sc, y + 55 * sc], fill=(40, 40, 40))
                d.rectangle([x + 4, y + 76 * sc, x + 62 * sc, y + 100 * sc], fill=(60, 60, 70))
    else:  # library
        d.rectangle([0, 0, Wd, Ht], fill=(215, 200, 175)); d.rectangle([0, 430, Wd, Ht], fill=(150, 120, 90))
        for s in range(4):
            y = 40 + s * 98
            d.rectangle([40, y, Wd - 40, y + 90], fill=(110, 75, 45))
            x = 48
            while x < Wd - 60:
                bw = rng.randint(10, 24); bh = rng.randint(55, 82)
                d.rectangle([x, y + 86 - bh, x + bw, y + 86], fill=(rng.randint(50, 230), rng.randint(40, 200), rng.randint(40, 200)),
                            outline=(30, 30, 30))
                x += bw + 2
        for tx in [150, 480, 810]:
            d.rectangle([tx - 90, 470, tx + 90, 490], fill=(90, 60, 35)); d.rectangle([tx - 80, 490, tx - 70, 570], fill=(70, 45, 25))
            d.rectangle([tx + 70, 490, tx + 80, 570], fill=(70, 45, 25)); d.ellipse([tx - 15, 440, tx + 15, 470], fill=(250, 230, 120))
        t = "CENTRAL LIBRARY"; f = pil_font(24, True); d.text((480 - d.textlength(t, font=f) / 2, 8), t, font=f, fill=(60, 40, 20))
    d.text((10, Ht - 22), "SYNTHETIC IMAGE - FICTIONAL", font=pil_font(13, True), fill=(255, 255, 255))
    im = _noise(im.filter(ImageFilter.GaussianBlur(.7)), nprng, 4)
    im.save(path, "JPEG", quality=82)


SCAN_PROFILES = {
    "clean": dict(dpi=130, rot=(-.4, .4), sigma=3, blur=0, contrast=1.0, stamp=False, speck=0),
    "skewed": dict(dpi=120, rot=(-2.6, 2.6), sigma=6, blur=.5, contrast=.95, stamp=False, speck=0),
    "noisy_lowres": dict(dpi=90, rot=(-1.2, 1.2), sigma=15, blur=1.0, contrast=.82, stamp=False, speck=250),
    "stamped": dict(dpi=120, rot=(-1.0, 1.0), sigma=7, blur=.4, contrast=.92, stamp=True, speck=40),
}


def make_scan(pdf_path, out_path, rng, nprng, profile, inst):
    p = SCAN_PROFILES[profile]
    with tempfile.TemporaryDirectory() as td:
        pref = os.path.join(td, "pg")
        subprocess.run(["pdftoppm", "-r", str(p["dpi"]), "-f", "1", "-l", "1", "-png", "-singlefile", str(pdf_path), pref],
                       check=True)
        im = Image.open(pref + ".png").convert("RGB")
    if p["stamp"]:
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        cx, cy = int(im.width * rng.uniform(.2, .45)), int(im.height * rng.uniform(.58, .75))
        od.ellipse([cx - 120, cy - 45, cx + 120, cy + 45], outline=(190, 30, 40, 170), width=4)
        f = pil_font(20, True)
        for ln, yy in [("RECEIVED", -22), (inst["application_date"], 0), ("SYNTHETIC", 20)]:
            od.text((cx - od.textlength(ln, font=f) / 2, cy + yy - 10), ln, font=f, fill=(190, 30, 40, 170))
        ov = ov.rotate(rng.uniform(-18, 18), resample=Image.BICUBIC, center=(cx, cy))
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    angle = rng.uniform(*p["rot"])
    im = im.rotate(angle, expand=True, fillcolor=(232, 232, 232), resample=Image.BICUBIC)
    if p["blur"]: im = im.filter(ImageFilter.GaussianBlur(p["blur"]))
    a = np.asarray(im).astype(np.float32)
    a = (a - 128) * p["contrast"] + 128 + 6
    a = a * np.array([1.0, .985, .94])  # warm paper
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    im = _noise(im, nprng, p["sigma"])
    if p["speck"]:
        dd = ImageDraw.Draw(im)
        for _ in range(p["speck"]):
            x, y = rng.randrange(im.width), rng.randrange(im.height); r = rng.choice([1, 1, 2])
            dd.ellipse([x, y, x + r, y + r], fill=(60, 60, 60))
    im.save(out_path, "JPEG", quality=68)
    return round(angle, 2)


# --------------------------------------------------------------------------------------
# Main build
# --------------------------------------------------------------------------------------
RULES = [
    ("R001", "Required documents present", "All 11 required document types must be present", "completeness", None),
    ("R002", "No duplicate files", "No two documents of different types may be byte-identical", "duplicate", None),
    ("R003", "Institution name consistent", "institution_name equals application form value in every document", "cross_document", {"field": "institution_name"}),
    ("R004", "Trust/society name consistent", "trust_name equal across application, registration, land, NOC, FDR, financials", "cross_document", {"field": "trust_name"}),
    ("R005", "Society registration number consistent", "society_reg_no equal between application form and registration certificate", "cross_document", {"field": "society_reg_no"}),
    ("R006", "Land area consistent", "land_area_sqm equal across application, land document, building plan", "cross_document", {"field": "land_area_sqm"}),
    ("R007", "Built-up area consistent", "built_up_area_sqm equal across application, building plan, infrastructure report", "cross_document", {"field": "built_up_area_sqm"}),
    ("R008", "Intake consistent", "total_intake equal across application, NOC and affiliation letter", "cross_document", {"field": "total_intake"}),
    ("R009", "Faculty count consistent", "faculty_count declared equals rows in faculty list", "cross_document", {"field": "faculty_count"}),
    ("R010", "Fire certificate valid", "fire certificate valid_to must be on/after application_date", "date", {"field": "valid_to"}),
    ("R011", "No future-dated documents", "Document dates must not be after application_date", "date", None),
    ("R012", "Deposit meets threshold", "fdr_amount >= min_fdr_inr[institution_type]", "threshold", {"threshold": "min_fdr_inr"}),
    ("R013", "Deposit not matured", "FDR maturity_date must be after application_date", "date", {"field": "maturity_date"}),
    ("R014", "Students-per-faculty ratio", "students / faculty_count <= max_students_per_faculty[type]", "threshold", {"threshold": "max_students_per_faculty"}),
    ("R015", "PIN code consistent", "pincode equal across application, land, plan, fire certificate", "cross_document", {"field": "pincode"}),
    ("R016", "Minimum land area", "land_area_sqm >= min_land_area_sqm[type]", "threshold", {"threshold": "min_land_area_sqm"}),
    ("R017", "PAN format", "pan matches ^[A-Z]{5}[0-9]{4}[A-Z]$", "format", {"regex": "^[A-Z]{5}[0-9]{4}[A-Z]$"}),
]


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def build(n, seed, out):
    out = Path(out).resolve()
    if out.exists(): shutil.rmtree(out)
    for sub in ["documents", "scans", "images", "logos", "data", "database", "config", "generator"]:
        (out / sub).mkdir(parents=True)
    os.chdir(out)  # relative logo paths keep PDF bytes independent of the output location
    master = random.Random(f"{seed}:master")
    forced = dict(zip(master.sample(range(n), min(n, len(ANOMALIES))), range(len(ANOMALIES))))
    used, institutions, programs_rows, doc_rows, field_rows, anom_rows, apps_json = set(), [], [], [], [], [], []
    anom_counter = 0

    for i in range(n):
        inst, rng = make_institution(i, seed, used)
        nprng = np.random.default_rng(abs(hash(("x", seed, i))) % (2 ** 32)) if False else np.random.default_rng(seed * 1000 + i)
        docs = build_docs(inst, rng)
        ctx = Ctx(inst, docs, rng)
        app = inst["app_id"]
        app_gt = []
        for j in plan_anomalies(i, forced.get(i), rng):
            atype, fn, rule, sev, desc = ANOMALIES[j]
            res = fn(ctx)
            if not res: continue
            anom_counter += 1
            for e in res:
                app_gt.append(dict(anomaly_id=f"ANOM-{anom_counter:05d}", app_id=app, anomaly_type=atype, rule_id=rule,
                                   severity=sev, description=desc, **e))
        anom_rows += app_gt

        logo = out / "logos" / f"{app}_logo.png"; make_logo(logo, inst, rng)
        ddir = out / "documents" / app; ddir.mkdir(parents=True)
        rendered = {}
        for n_doc, dtype in enumerate(DOC_TYPES, 1):
            if dtype not in docs: continue
            doc_id = f"{app}-D{n_doc:02d}"; fp = ddir / f"{n_doc:02d}_{dtype}.pdf"
            pages = render_pdf(fp, docs[dtype], doc_id, f"logos/{app}_logo.png", inst)
            rendered[dtype] = dict(doc_id=doc_id, path=fp, pages=pages)
        for src, tgt in ctx.dups:     # byte-identical duplicate under a different document type
            shutil.copyfile(rendered[src]["path"], rendered[tgt]["path"])
            rendered[tgt]["actual"] = src
        for dtype, r in rendered.items():
            actual = r.get("actual", dtype)
            doc_rows.append(dict(doc_id=r["doc_id"], app_id=app, declared_doc_type=dtype, actual_content_type=actual,
                                 file_path=str(r["path"].relative_to(out)), format="pdf", sha256=sha256(r["path"]), pages=r["pages"],
                                 is_scan=0, source_doc_id="", scan_profile="", skew_deg="",
                                 has_injected_anomaly=int(any(a["doc_type"] == dtype for a in app_gt))))
            if actual == dtype:
                for k, v in docs[dtype]["keys"].items():
                    field_rows.append(dict(doc_id=r["doc_id"], app_id=app, doc_type=dtype, field=k, value=v))
        # scans
        sdir = out / "scans" / app; sdir.mkdir(parents=True)
        cands = [d for d in SCAN_CANDIDATES if d in rendered and "actual" not in rendered[d]]
        for dtype in rng.sample(cands, min(3, len(cands))):
            prof = rng.choice(list(SCAN_PROFILES)); r = rendered[dtype]
            sp = sdir / f"{dtype}_scan_{prof}.jpg"
            skew = make_scan(r["path"], sp, rng, nprng, prof, inst)
            doc_rows.append(dict(doc_id=r["doc_id"] + "-S", app_id=app, declared_doc_type=dtype, actual_content_type=dtype,
                                 file_path=str(sp.relative_to(out)), format="jpg", sha256=sha256(sp), pages=1, is_scan=1,
                                 source_doc_id=r["doc_id"], scan_profile=prof, skew_deg=skew,
                                 has_injected_anomaly=int(any(a["doc_type"] == dtype for a in app_gt))))
        # campus images
        idir = out / "images" / app; idir.mkdir(parents=True)
        for kind in ["campus_front", "computer_lab", "library"]:
            ip = idir / f"{kind}.jpg"; make_campus(ip, inst, rng, nprng, kind)
            doc_rows.append(dict(doc_id=f"{app}-IMG-{kind}", app_id=app, declared_doc_type=kind, actual_content_type=kind,
                                 file_path=str(ip.relative_to(out)), format="jpg", sha256=sha256(ip), pages=1, is_scan=0,
                                 source_doc_id="", scan_profile="", skew_deg="", has_injected_anomaly=0))

        flat = {k: v for k, v in inst.items() if not isinstance(v, (list, dict))}
        flat["expected_status"] = "NEEDS_REVIEW" if app_gt else "CLEAN"
        flat["expected_rules_violated"] = ";".join(sorted({a["rule_id"] for a in app_gt}))
        flat["injected_anomaly_count"] = len({a["anomaly_id"] for a in app_gt})
        institutions.append(flat)
        for p in inst["programs"]:
            programs_rows.append(dict(app_id=app, programme=p["name"], level=p["level"], duration_years=p["years"], intake=p["intake"]))
        apps_json.append(dict(application=flat, programmes=inst["programs"],
                              documents=[r for r in doc_rows if r["app_id"] == app], injected_anomalies=app_gt))
        if (i + 1) % 10 == 0: print(f"  generated {i + 1}/{n} applications")

    # ---- data files
    d = out / "data"
    write_csv(d / "institutions.csv", institutions, list(institutions[0].keys()))
    write_csv(d / "programs.csv", programs_rows, ["app_id", "programme", "level", "duration_years", "intake"])
    dcols = ["doc_id", "app_id", "declared_doc_type", "actual_content_type", "file_path", "format", "sha256", "pages",
             "is_scan", "source_doc_id", "scan_profile", "skew_deg", "has_injected_anomaly"]
    write_csv(d / "documents.csv", doc_rows, dcols)
    write_csv(d / "extracted_fields_ground_truth.csv", field_rows, ["doc_id", "app_id", "doc_type", "field", "value"])
    acols = ["anomaly_id", "app_id", "anomaly_type", "rule_id", "severity", "doc_type", "field", "expected_value", "injected_value", "description"]
    write_csv(d / "ground_truth_anomalies.csv", anom_rows, acols)
    (d / "applications.json").write_text(json.dumps(apps_json, indent=2, ensure_ascii=False), encoding="utf-8")
    expected = {a["application"]["app_id"]: dict(status=a["application"]["expected_status"],
                rules_violated=sorted({x["rule_id"] for x in a["injected_anomalies"]})) for a in apps_json}
    (d / "expected_findings.json").write_text(json.dumps(expected, indent=2), encoding="utf-8")

    rules = dict(
        disclaimer="Thresholds are PLACEHOLDERS for testing. They are not taken from the AICTE Approval Process Handbook. "
                   "Map each rule to a Handbook clause and set verified=true only after human verification.",
        thresholds=THRESHOLDS,
        rules=[dict(rule_id=r, name=nm, description=ds, category=cat, params=pr, handbook_reference=None, verified=False)
               for r, nm, ds, cat, pr in RULES])
    (out / "config" / "rules.json").write_text(json.dumps(rules, indent=2), encoding="utf-8")

    # ---- sqlite
    db = sqlite3.connect(out / "database" / "aicte_synthetic.db")
    def table(name, rows, cols):
        db.execute(f"CREATE TABLE {name} ({', '.join(c + ' TEXT' for c in cols)})")
        db.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * len(cols))})", [[r.get(c) for c in cols] for r in rows])
    table("institutions", institutions, list(institutions[0].keys()))
    table("programs", programs_rows, ["app_id", "programme", "level", "duration_years", "intake"])
    table("documents", doc_rows, dcols)
    table("extracted_fields", field_rows, ["doc_id", "app_id", "doc_type", "field", "value"])
    table("ground_truth_anomalies", anom_rows, acols)
    table("rules", [dict(rule_id=r, name=nm, description=ds, category=cat, verified=0) for r, nm, ds, cat, _ in RULES],
          ["rule_id", "name", "description", "category", "verified"])
    db.commit(); db.close()
    return out, institutions, doc_rows, anom_rows


def zip_dir(src, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(Path(src).rglob("*")):
            if p.is_file():
                zi = zipfile.ZipInfo(str(Path(src.name) / p.relative_to(src)), date_time=(2026, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
                z.writestr(zi, p.read_bytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60); ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default="AICTE_Synthetic_Dataset"); ap.add_argument("--zip", action="store_true")
    a = ap.parse_args()
    a.out = str(Path(a.out).resolve())
    out, inst, docs, an = build(a.n, a.seed, a.out)
    print(f"Done: {len(inst)} applications, {len(docs)} files, {len(an)} anomaly rows")
    if a.zip:
        zip_dir(Path(a.out).resolve(), Path(a.out).resolve().parent / (Path(a.out).name + ".zip"))
