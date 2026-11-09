import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skill_contract_kit.parser import parse_frontmatter

class TestParser(unittest.TestCase):
    def test_basic(self):
        fm, body = parse_frontmatter("---\nname: foo\ndescription: hello world\n---\nBody here.\n")
        self.assertEqual(fm["name"], "foo"); self.assertEqual(body.strip(), "Body here.")
    def test_list_block(self):
        fm, _ = parse_frontmatter("---\nname: x\nallowed-tools:\n  - read_file\n  - search\n---\nB\n")
        self.assertEqual(fm["allowed-tools"], ["read_file", "search"])
    def test_inline_list(self):
        fm, _ = parse_frontmatter("---\nname: x\nallowed-tools: [read_file, search]\n---\nB\n")
        self.assertEqual(fm["allowed-tools"], ["read_file", "search"])
    def test_nested_metadata(self):
        fm, _ = parse_frontmatter("---\nname: x\nmetadata:\n  version: 1.2.3\n---\nB\n")
        self.assertEqual(fm["metadata"]["version"], "1.2.3")
    def test_quoted_value(self):
        fm, _ = parse_frontmatter('---\nname: "my skill"\n---\nB\n')
        self.assertEqual(fm["name"], "my skill")
    def test_no_frontmatter(self):
        fm, body = parse_frontmatter("Just body\n")
        self.assertEqual(fm, {}); self.assertEqual(body, "Just body\n")
    def test_unterminated_frontmatter(self):
        fm, body = parse_frontmatter("---\nname: x\nno end\n")
        self.assertEqual(fm, {})
    def test_comments_and_blanks_ignored(self):
        fm, _ = parse_frontmatter("---\n# comment\n\nname: x\n---\nB\n")
        self.assertEqual(fm, {"name": "x"})
    def test_empty_value_becomes_empty_dict(self):
        fm, _ = parse_frontmatter("---\nname: x\nmetadata:\n---\nB\n")
        self.assertEqual(fm["metadata"], {})

if __name__ == "__main__":
    unittest.main()
