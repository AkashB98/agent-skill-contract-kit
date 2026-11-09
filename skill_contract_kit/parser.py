"""Hand-written stdlib parser for the simple YAML-like frontmatter subset.

Supports:
  key: value
  key:
    - list item
  key: [a, b]
  key:
    nested: value   (one level, e.g. metadata.version)
Comments (# ...) and blank lines are ignored. No PyYAML — not stdlib.
"""
import re

_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def _strip_quotes(v):
    v = v.strip()
    if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
        return v[1:-1]
    return v


def _inline_list(v):
    inner = v.strip()[1:-1].strip()
    if not inner:
        return []
    return [_strip_quotes(p.strip()) for p in inner.split(",") if p.strip()]


def parse_frontmatter(text):
    """Return (frontmatter_dict, body_str). If no frontmatter, ({}, text)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end = i
            break
    if end is None:
        return {}, text
    body = "\n".join(lines[end + 1:])
    return parse_frontmatter_lines(lines[1:end]), body


def parse_frontmatter_lines(fm_lines):
    result = {}
    current_key = None      # top-level key currently collecting children
    current_is_container = False
    for raw in fm_lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if stripped.startswith("- ") or stripped == "-":
            item = _strip_quotes(stripped[1:].strip())
            if current_key is None:
                continue
            cur = result.get(current_key)
            if not isinstance(cur, list):
                result[current_key] = []
            result[current_key].append(item)
            continue
        m = _KEY_RE.match(stripped)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if indent >= 2 and current_key is not None and current_is_container:
            # nested scalar under a container key (e.g. metadata -> version)
            if not isinstance(result.get(current_key), dict):
                result[current_key] = {}
            if value.startswith("[") and value.endswith("]"):
                result[current_key][key] = _inline_list(value)
            elif value == "":
                result[current_key][key] = {}
            else:
                result[current_key][key] = _strip_quotes(value)
            continue
        # top-level key
        current_key = key
        if value == "":
            result[key] = {}
            current_is_container = True
        elif value.startswith("[") and value.endswith("]"):
            result[key] = _inline_list(value)
            current_is_container = False
        else:
            result[key] = _strip_quotes(value)
            current_is_container = False
    # Containers that collected list items were converted to list above;
    # containers with no children stay {}.
    return result
