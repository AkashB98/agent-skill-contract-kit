import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skill_contract_kit.cli import load_registry
from skill_contract_kit.validator import validate_folder, validate_spec, extract_references

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "fixtures", "skills")
REG = load_registry()

def codes(folder):
    r = validate_folder(os.path.join(SKILLS, folder), REG)
    return {i.code for i in r.issues}, r

class TestValidator(unittest.TestCase):
    def test_valid_basic_clean(self):
        c, _ = codes("valid-basic"); self.assertEqual(c, set())
    def test_fp_trap_write_summary(self):
        c, _ = codes("valid-write-summary"); self.assertEqual(c, set())
    def test_fp_trap_write_report(self):
        c, _ = codes("valid-write-report"); self.assertEqual(c, set())
    def test_valid_writer_clean(self):
        c, _ = codes("valid-writer"); self.assertEqual(c, set())
    def test_missing_description(self):
        c, _ = codes("defect-missing-description"); self.assertIn("MISSING_DESCRIPTION", c)
    def test_name_mismatch(self):
        c, _ = codes("defect-name-mismatch"); self.assertIn("NAME_MISMATCH", c)
    def test_broken_reference(self):
        c, _ = codes("defect-broken-reference"); self.assertIn("BROKEN_REFERENCE", c)
    def test_unknown_tool(self):
        c, _ = codes("defect-unknown-tool"); self.assertIn("UNKNOWN_TOOL", c)
    def test_readonly_mutating_is_heuristic(self):
        _, r = codes("defect-readonly-mutating")
        hits = [i for i in r.issues if i.code == "READONLY_MUTATING_BODY"]
        self.assertTrue(hits); self.assertTrue(all(i.heuristic for i in hits))
    def test_malformed_version(self):
        c, _ = codes("defect-malformed-version"); self.assertIn("MALFORMED_VERSION", c)
    def test_missing_version_not_flagged(self):
        # valid-write-report has no metadata.version — must be clean
        c, _ = codes("valid-write-report"); self.assertNotIn("MALFORMED_VERSION", c)
    def test_short_description(self):
        r = validate_spec("x", {"name": "x", "description": "short"}, "", [], REG)
        self.assertIn("SHORT_DESCRIPTION", {i.code for i in r.issues})
    def test_extract_references(self):
        refs = extract_references("See [g](references/guide.md) and `scripts/a.py` and [web](https://example.com/x.md)")
        self.assertIn("references/guide.md", refs); self.assertIn("scripts/a.py", refs)
        self.assertFalse(any(r.startswith("http") for r in refs))
    def test_spec_mode_broken_ref(self):
        r = validate_spec("s", {"name": "s", "description": "A sufficiently long description here."},
                          "Use scripts/nope.py", ["SKILL.md"], REG)
        self.assertIn("BROKEN_REFERENCE", {i.code for i in r.issues})
    def test_harmless_write_spec_no_flag(self):
        r = validate_spec("s", {"name": "s", "description": "A sufficiently long description here.",
                                "allowed-tools": ["read_file"]},
                          "Write a summary to the user.", ["SKILL.md"], REG)
        self.assertNotIn("READONLY_MUTATING_BODY", {i.code for i in r.issues})

if __name__ == "__main__":
    unittest.main()
