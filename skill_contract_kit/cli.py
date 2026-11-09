"""CLI: lint / check / demo / serve. Stdlib only."""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from .validator import discover_skills, exit_code_for, validate_folder, validate_spec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TOOLS = os.path.join(ROOT, "fixtures", "tools.json")
DEFAULT_SKILLS = os.path.join(ROOT, "fixtures", "skills")


def load_registry(path=None):
    p = path or DEFAULT_TOOLS
    if p and os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _report(results):
    lines = []
    for r in results:
        if not r.issues:
            lines.append(f"{r.folder_name}: OK")
        else:
            lines.append(f"{r.folder_name}: {len(r.issues)} issue(s)")
            for i in r.issues:
                tag = " [heuristic]" if i.heuristic else ""
                lines.append(f"  - [{i.severity}] {i.code}{tag}: {i.message}")
    return "\n".join(lines)


def cmd_lint(args):
    registry = load_registry(args.tools)
    skills = discover_skills(args.path)
    if not skills:
        print(f"No skills found at {args.path}")
        return 2
    results = [validate_folder(s, registry) for s in skills]
    print(_report(results))
    return 0


def cmd_check(args):
    registry = load_registry(args.tools)
    skills = discover_skills(args.path)
    if not skills:
        print(f"No skills found at {args.path}")
        return 2
    results = [validate_folder(s, registry) for s in skills]
    print(_report(results))
    return exit_code_for(results)


def cmd_demo(args):
    # Delegate to demo.py logic inline to avoid import cycles.
    sys.path.insert(0, ROOT)
    import demo as demo_mod
    return demo_mod.main()


def make_handler():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

        def do_POST(self):
            if self.path != "/lint":
                self.send_response(404); self.end_headers(); return
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                spec = json.loads(raw.decode("utf-8"))
            except Exception:
                self.send_response(400); self.end_headers()
                self.wfile.write(b'{"error": "invalid json"}'); return
            # Simpler JSON-spec design (documented in README):
            # {folder_name, frontmatter, body, files[], tools_registry}
            result = validate_spec(
                spec.get("folder_name", ""),
                spec.get("frontmatter", {}),
                spec.get("body", ""),
                spec.get("files", []),
                spec.get("tools_registry", load_registry()),
            )
            payload = json.dumps(result.to_dict(), sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/health":
                payload = b'{"status": "ok"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers(); self.wfile.write(payload); return
            self.send_response(404); self.end_headers()
    return Handler


def cmd_serve(args):
    server = HTTPServer((args.host, args.port), make_handler())
    print(f"Serving on http://{args.host}:{args.port} (POST /lint, GET /health)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="skillkit", description="Skill-folder contract validator")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("lint", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("path", nargs="?", default=DEFAULT_SKILLS)
        sp.add_argument("--tools", default=None)
    sub.add_parser("demo")
    sp = sub.add_parser("serve")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    if args.cmd == "lint":
        return cmd_lint(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "demo":
        return cmd_demo(args)
    if args.cmd == "serve":
        return cmd_serve(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
