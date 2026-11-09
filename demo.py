#!/usr/bin/env python3
"""End-to-end demo: lint the planted corpus and summarise. Stdlib only, exit 0 on success."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_contract_kit.cli import load_registry
from skill_contract_kit.validator import discover_skills, validate_folder

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    registry = load_registry()
    skills = discover_skills(os.path.join(ROOT, "fixtures", "skills"))
    print(f"Demo: linting {len(skills)} fixture skills")
    ok = True
    for s in skills:
        r = validate_folder(s, registry)
        status = "OK" if not r.issues else ", ".join(sorted({i.code for i in r.issues}))
        print(f"  {r.folder_name}: {status}")
        # Valid skills must be clean; defect skills must be flagged.
        if r.folder_name.startswith("valid-") and r.issues:
            ok = False
        if r.folder_name.startswith("defect-") and not r.issues:
            ok = False
    print("Demo result:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
