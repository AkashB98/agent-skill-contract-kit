#!/usr/bin/env python3
"""Deterministic evals: per-defect-class detection + FP split heuristic vs deterministic.

Writes evals/eval_report.json byte-stable (sort_keys, indent=2, no timestamps).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skill_contract_kit.cli import load_registry
from skill_contract_kit.validator import validate_folder

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "fixtures", "skills")

# defect class -> (skill folder, expected code)
DEFECTS = {
    "broken_reference": ("defect-broken-reference", "BROKEN_REFERENCE"),
    "malformed_version": ("defect-malformed-version", "MALFORMED_VERSION"),
    "missing_description": ("defect-missing-description", "MISSING_DESCRIPTION"),
    "name_mismatch": ("defect-name-mismatch", "NAME_MISMATCH"),
    "readonly_mutating_body": ("defect-readonly-mutating", "READONLY_MUTATING_BODY"),
    "unknown_tool": ("defect-unknown-tool", "UNKNOWN_TOOL"),
}
VALID = ["valid-basic", "valid-write-report", "valid-write-summary", "valid-writer"]


def main():
    registry = load_registry()
    classes = {}
    found_total = 0
    for cls in sorted(DEFECTS):
        folder, code = DEFECTS[cls]
        r = validate_folder(os.path.join(SKILLS, folder), registry)
        found = 1 if any(i.code == code for i in r.issues) else 0
        found_total += found
        classes[cls] = {"detected": bool(found), "expected_code": code,
                        "found": found, "skill": folder, "total": 1}
    # False positives on valid skills, split by heuristic vs deterministic
    det_fp = 0
    heur_fp = 0
    valid_detail = {}
    for folder in sorted(VALID):
        r = validate_folder(os.path.join(SKILLS, folder), registry)
        d = sum(1 for i in r.issues if not i.heuristic)
        h = sum(1 for i in r.issues if i.heuristic)
        det_fp += d
        heur_fp += h
        valid_detail[folder] = {"deterministic_issues": d, "heuristic_issues": h}
    report = {
        "defect_classes": classes,
        "false_positives": {
            "deterministic": det_fp,
            "heuristic": heur_fp,
            "total_valid_skills": len(VALID),
        },
        "summary": {
            "defect_found": found_total,
            "defect_total": len(DEFECTS),
            "valid_skills": len(VALID),
        },
        "valid_skills_detail": valid_detail,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_report.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"defects {found_total}/{len(DEFECTS)}  FP deterministic={det_fp} heuristic={heur_fp}")
    print(f"Wrote {out}")
    return 0 if found_total == len(DEFECTS) and det_fp == 0 and heur_fp == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
