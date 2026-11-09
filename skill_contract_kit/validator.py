"""Validator + contract tester for agent SKILL packages. Stdlib only."""
import os
import re
from dataclasses import dataclass, field

from .parser import parse_frontmatter

MIN_DESCRIPTION_LEN = 20
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# FIXED RULE TABLE (heuristic, labeled as such).
# Each entry: (id, compiled pattern, label). Patterns require a concrete
# file/command object so harmless prose ("write a summary to the user")
# does NOT flag.
RULE_TABLE = [
    ("write-to-file", re.compile(r"\bwrite to the file\b", re.I), "write to the file"),
    ("write-the-file", re.compile(r"\bwrite the file\b", re.I), "write the file"),
    ("edit-the-file", re.compile(r"\bedit the file\b", re.I), "edit the file"),
    ("delete-the", re.compile(r"\bdelete the\b", re.I), "delete the"),
    ("run-the-command", re.compile(r"\brun the command\b", re.I), "run the command"),
    ("run-the-script", re.compile(r"\brun the script\b", re.I), "run the script"),
    ("save-the-file", re.compile(r"\bsave the file\b", re.I), "save the file"),
]

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_PATH_RE = re.compile(r"\b((?:scripts|references|assets)/[A-Za-z0-9_.\-/]+)")
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")


@dataclass
class Issue:
    code: str
    severity: str  # "error" | "warning"
    heuristic: bool
    message: str

    def to_dict(self):
        return {"code": self.code, "severity": self.severity,
                "heuristic": self.heuristic, "message": self.message}


@dataclass
class SkillResult:
    folder_name: str
    issues: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.issues

    def to_dict(self):
        return {"folder_name": self.folder_name,
                "issues": [i.to_dict() for i in self.issues]}


def load_tools_registry(registry):
    """Normalize a registry (dict or list) to {name: kind} where kind in read/write/unknown."""
    out = {}
    if registry is None:
        return out
    tools = registry.get("tools", registry) if isinstance(registry, dict) else registry
    if isinstance(tools, dict):
        for name, meta in tools.items():
            if isinstance(meta, dict):
                out[name] = meta.get("kind") or meta.get("type") or "unknown"
            else:
                out[name] = str(meta)
    elif isinstance(tools, list):
        for item in tools:
            if isinstance(item, str):
                out[item] = "unknown"
            elif isinstance(item, dict) and "name" in item:
                out[item["name"]] = item.get("kind") or item.get("type") or "unknown"
    return out


def extract_references(body):
    refs = set()
    for m in _MD_LINK_RE.finditer(body):
        target = m.group(1).strip().split()[0].strip("<>")
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = target.split("#")[0]
        if target:
            refs.add(target)
    for m in _PATH_RE.finditer(body):
        refs.add(m.group(1).rstrip(".,;:"))
    for m in _BACKTICK_RE.finditer(body):
        inner = m.group(1).strip()
        if _PATH_RE.fullmatch(inner) or re.fullmatch(r"[A-Za-z0-9_.\-/]+\.(?:md|py|json|txt|sh)", inner):
            if not inner.startswith(("http", "#")):
                refs.add(inner)
    return sorted(refs)


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        return [v] if v.strip() else []
    return []


def validate_spec(folder_name, frontmatter, body, files, tools_registry):
    """Validate an in-memory skill spec. files = iterable of relative paths present."""
    issues = []
    files_set = set(files or [])
    registry = load_tools_registry(tools_registry)
    fm = frontmatter or {}

    # 1. Manifest fields
    name = fm.get("name")
    if not isinstance(name, str) or not name.strip():
        issues.append(Issue("MISSING_NAME", "error", False, "frontmatter 'name' is required"))
        name = ""
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        issues.append(Issue("MISSING_DESCRIPTION", "error", False, "frontmatter 'description' is required"))
    elif len(desc.strip()) < MIN_DESCRIPTION_LEN:
        issues.append(Issue("SHORT_DESCRIPTION", "error", False,
                            f"description is too short ({len(desc.strip())} chars, need >= {MIN_DESCRIPTION_LEN})"))
    # 2. Name matches folder
    if name and name.strip() != folder_name:
        issues.append(Issue("NAME_MISMATCH", "error", False,
                            f"name '{name.strip()}' does not match folder '{folder_name}'"))
    # 3. Reference integrity (deterministic)
    for ref in extract_references(body or ""):
        if ref not in files_set:
            issues.append(Issue("BROKEN_REFERENCE", "error", False,
                                f"referenced file not found: {ref}"))
    # 4. Declared tools are real (deterministic)
    allowed = _as_list(fm.get("allowed-tools", fm.get("allowed_tools")))
    for tool in allowed:
        if registry and tool not in registry:
            issues.append(Issue("UNKNOWN_TOOL", "error", False,
                                f"allowed-tools entry not in registry: {tool}"))
    # 5. Body-vs-manifest consistency (HEURISTIC rule table)
    if allowed and registry:
        kinds = [registry.get(t, "unknown") for t in allowed]
        if kinds and all(k == "read" for k in kinds):
            for rule_id, pattern, label in RULE_TABLE:
                if pattern.search(body or ""):
                    issues.append(Issue("READONLY_MUTATING_BODY", "warning", True,
                                        f"[heuristic:{rule_id}] read-only manifest but body says '{label}'"))
    # 6. metadata.version when present must be semver-ish
    metadata = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
    version = metadata.get("version") if isinstance(metadata, dict) else None
    if version is not None and str(version).strip() != "":
        if not SEMVER_RE.match(str(version).strip()):
            issues.append(Issue("MALFORMED_VERSION", "error", False,
                                f"metadata.version '{version}' is not semver x.y.z"))
    # Deterministic ordering
    issues.sort(key=lambda i: (i.code, i.message))
    return SkillResult(folder_name=folder_name, issues=issues)


def validate_folder(skill_dir, tools_registry):
    skill_dir = os.fspath(skill_dir)
    folder_name = os.path.basename(os.path.normpath(skill_dir))
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return SkillResult(folder_name, [Issue("MISSING_SKILL_MD", "error", False, "SKILL.md not found")])
    with open(skill_md, encoding="utf-8") as f:
        text = f.read()
    fm, body = parse_frontmatter(text)
    files = []
    for root, dirs, filenames in os.walk(skill_dir):
        dirs.sort()
        for fn in sorted(filenames):
            rel = os.path.relpath(os.path.join(root, fn), skill_dir).replace(os.sep, "/")
            files.append(rel)
    return validate_spec(folder_name, fm, body, files, tools_registry)


def discover_skills(path):
    """If path contains SKILL.md return [path]; else sorted subdirs containing SKILL.md."""
    path = os.fspath(path)
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        return [path]
    out = []
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            sub = os.path.join(path, name)
            if os.path.isdir(sub) and os.path.isfile(os.path.join(sub, "SKILL.md")):
                out.append(sub)
    return out


def exit_code_for(results):
    if any(i.severity == "error" for r in results for i in r.issues):
        return 2
    if any(i.severity == "warning" for r in results for i in r.issues):
        return 1
    return 0
