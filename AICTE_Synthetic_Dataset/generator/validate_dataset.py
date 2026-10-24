#!/usr/bin/env python3
"""
Self-check for the synthetic dataset.

1. Every file listed in documents.csv exists and its SHA-256 matches.
2. Reference implementation of rules R001-R017 runs over the ground-truth fields and
   must reproduce the injected anomalies exactly (precision = recall = 1.0 on the labels).

Usage: python validate_dataset.py [dataset_root]
"""
import csv, json, re, sys, hashlib, datetime as dt
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
rd = lambda n: list(csv.DictReader(open(root / "data" / n, encoding="utf-8")))
inst = {r["app_id"]: r for r in rd("institutions.csv")}
docs = rd("documents.csv")
fields = rd("extracted_fields_ground_truth.csv")
anoms = rd("ground_truth_anomalies.csv")
cfg = json.load(open(root / "config" / "rules.json"))
TH = cfg["thresholds"]
REQUIRED = ["application_form", "society_registration", "land_document", "building_plan_approval",
            "fire_safety_certificate", "noc_state_govt", "affiliation_letter", "bank_fdr_certificate",
            "audited_financials", "faculty_list", "infrastructure_report"]

errors = 0
for d in docs:                                   # 1. file integrity
    p = root / d["file_path"]
    if not p.exists():
        print("MISSING FILE", d["file_path"]); errors += 1; continue
    if hashlib.sha256(p.read_bytes()).hexdigest() != d["sha256"]:
        print("HASH MISMATCH", d["file_path"]); errors += 1

F = defaultdict(lambda: defaultdict(dict))       # app -> doc_type -> field -> value
for r in fields:
    F[r["app_id"]][r["doc_type"]][r["field"]] = r["value"]
pdfs = defaultdict(dict)
for d in docs:
    if d["format"] == "pdf":
        pdfs[d["app_id"]][d["declared_doc_type"]] = d


def check(app):
    v, f, i = set(), F[app], inst[app]
    t = i["institution_type"]
    af = f.get("application_form", {})
    apps_d = dt.date.fromisoformat(i["application_date"])
    present = set(pdfs[app])
    if set(REQUIRED) - present: v.add("R001")
    byhash = defaultdict(set)
    for dtp, d in pdfs[app].items(): byhash[d["sha256"]].add(dtp)
    if any(len(s) > 1 for s in byhash.values()): v.add("R002")

    def differs(rule, field, ref_doc="application_form", among=None):
        ref = f.get(ref_doc, {}).get(field)
        for dtp, kv in f.items():
            if dtp == ref_doc or field not in kv or (among and dtp not in among): continue
            if ref is not None and kv[field] != ref: v.add(rule)
    differs("R003", "institution_name")
    differs("R004", "trust_name")
    differs("R005", "society_reg_no")
    differs("R006", "land_area_sqm")
    differs("R007", "built_up_area_sqm")
    differs("R008", "total_intake")
    differs("R009", "faculty_count")
    differs("R015", "pincode")
    fs = f.get("fire_safety_certificate", {})
    if fs and dt.date.fromisoformat(fs["valid_to"]) < apps_d: v.add("R010")
    for dtp, kv in f.items():
        for k in ("approval_date", "issue_date", "deed_date", "fdr_date", "registration_date"):
            if k in kv and dt.date.fromisoformat(kv[k]) > apps_d: v.add("R011")
    fdr = f.get("bank_fdr_certificate", {})
    if fdr:
        if int(fdr["fdr_amount"]) < TH["min_fdr_inr"][t]: v.add("R012")
        if dt.date.fromisoformat(fdr["maturity_date"]) <= apps_d: v.add("R013")
    if af:
        students = int(i["students"])
        if students / int(af["faculty_count"]) > TH["max_students_per_faculty"][t]: v.add("R014")
        if int(af["land_area_sqm"]) < TH["min_land_area_sqm"][t]: v.add("R016")
        if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", af["pan"]): v.add("R017")
    return v


truth = defaultdict(set)
for a in anoms: truth[a["app_id"]].add(a["rule_id"])
tp = fp = fn = 0
for app in inst:
    got, exp = check(app), truth[app]
    tp += len(got & exp); fp += len(got - exp); fn += len(exp - got)
    if got != exp:
        print(f"{app}: expected {sorted(exp)} got {sorted(got)}"); errors += 1
clean = sum(1 for a in inst if not truth[a])
print(f"applications={len(inst)} clean={clean} with_anomalies={len(inst) - clean} files={len(docs)}")
print(f"reference rules vs labels: TP={tp} FP={fp} FN={fn}")
print("VALIDATION PASSED" if errors == 0 else f"VALIDATION FAILED ({errors} problems)")
sys.exit(1 if errors else 0)
