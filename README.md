# agent-skill-contract-kit

**Hiring signal:** I build the contract tests for agent tooling itself — not just agents that call tools, but the validator that catches a skill package lying about what it does before it ever runs in production.

A skill package is prose plus files plus a manifest. When the manifest says "read-only" but the instructions tell the agent to edit files, or the body links to a reference that was never shipped, nothing in a normal test suite notices. This kit notices.

## What this is not — and what it is

- A **tool-schema-linter** checks the shape of one tool's JSON schema: are the fields typed correctly?
- A **tool-contract-checker** checks whether a tool's contract changed between versions: did the schema drift?
- **This kit** checks whether a skill *folder* — its prose instructions and every file it references — matches what its own manifest declares: name, description, tools, and version.

Different layer, different failure mode. Skills fail by inconsistency, not by syntax.

## Checks (flag-only, no autofix)

| # | Check | Kind |
|---|-------|------|
| 1 | Manifest fields present: `name` + `description` required, description non-trivial (≥20 chars) | deterministic |
| 2 | `name` matches folder name | deterministic |
| 3 | **Reference integrity (headline):** every file referenced in the body — markdown links, `` `scripts/...` ``, `references/...` paths — actually exists in the folder tree | deterministic |
| 4 | Declared tools are real: `allowed-tools` entries must exist in a supplied `tools.json` registry (fixture: fictional Helios Home tools) | deterministic |
| 5 | Body-vs-manifest consistency via a **fixed rule table** (see below) | **heuristic** |
| 6 | `metadata.version`, *when present*, must be semver-ish `x.y.z`. Missing version is **not** flagged — no version-pinning requirement | deterministic |

Frontmatter is parsed with a small hand-written stdlib parser for the `key: value` / list / one-level-nested subset (`skill_contract_kit/parser.py`). PyYAML is not stdlib, so it is not used.

### The heuristic rule table — honestly labeled

Check 5 is a **heuristic**, not a proof. If `allowed-tools` contains *only* read tools (`read_file`, `search`, `run_query` in the fixture registry), a fixed table of concrete patterns flags mutating instructions: `write to the file`, `write the file`, `edit the file`, `delete the`, `run the command`, `run the script`, `save the file`.

The patterns require a concrete file/command object on purpose: harmless prose like *"write a summary to the user"* must not flag. Two planted valid skills (`valid-write-summary`, `valid-write-report`) use "write" harmlessly as false-positive traps, and the evals report false positives for the heuristic table **separately** from the deterministic checks — so you can see exactly where the heuristic stands.

## Quick start

```bash
python -m skill_contract_kit lint fixtures/skills          # human report
python -m skill_contract_kit check fixtures/skills/valid-basic   # CI gate
python demo.py                                              # end-to-end demo, exit 0
python evals/run_evals.py                                   # writes evals/eval_report.json
python -m unittest discover -s tests -v
```

`check` exit codes: `0` clean · `1` warnings only · `2` errors.

## Server

```bash
python -m skill_contract_kit serve --host 127.0.0.1 --port 8765
```

Design choice (the simpler of the two options): `POST /lint` accepts a JSON skill spec — no filesystem upload, no zip handling:

```json
{
  "folder_name": "my-skill",
  "frontmatter": {"name": "my-skill", "description": "...", "allowed-tools": ["read_file"]},
  "body": "Write a summary to the user.",
  "files": ["SKILL.md", "references/guide.md"],
  "tools_registry": {"tools": {"read_file": {"kind": "read"}}}
}
```

`files[]` is the existence set that reference integrity checks against. `GET /health` returns `{"status": "ok"}`. Binds to `127.0.0.1` by default.

## Planted corpus (`fixtures/skills/`)

Valid: `valid-basic`, `valid-writer`, plus the two FP traps `valid-write-summary` and `valid-write-report`.
One per defect class: `defect-missing-description`, `defect-name-mismatch`, `defect-broken-reference`, `defect-unknown-tool`, `defect-readonly-mutating`, `defect-malformed-version`.

All data is fictional. No secrets, no personal data, no network calls. Python stdlib only.

## Scope limits

- The rule table is a fixed heuristic list — it will miss novel phrasings of mutating instructions, and that limit is stated, not hidden.
- Reference extraction covers markdown links and `scripts/` / `references/` / `assets/` style paths; arbitrary prose mentions of filenames are out of scope.
- The frontmatter parser covers the simple subset above, not full YAML (no anchors, flow mappings beyond inline lists, or multi-line strings).

## Validated design decisions

- Inline-list and nested `metadata:` parsing were exercised against parser edge-case tests (quoted values, unterminated frontmatter, comments) rather than assumed.
- FP traps were planted *before* finalising the rule-table patterns, so the patterns were tuned against concrete counter-examples, not intuition.

## License

MIT — see `LICENSE`. Copyright Akash Bhargava.
