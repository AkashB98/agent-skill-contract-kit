import hashlib, json, os, subprocess, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run(*args):
    return subprocess.run([sys.executable, "-m", "skill_contract_kit", *args],
                          cwd=ROOT, capture_output=True, text=True, timeout=30)

class TestCli(unittest.TestCase):
    def test_check_valid_exit_0(self):
        p = run("check", os.path.join(ROOT, "fixtures/skills/valid-basic"))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    def test_check_defect_exit_2(self):
        p = run("check", os.path.join(ROOT, "fixtures/skills/defect-unknown-tool"))
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
    def test_check_heuristic_only_exit_1(self):
        p = run("check", os.path.join(ROOT, "fixtures/skills/defect-readonly-mutating"))
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
    def test_lint_runs(self):
        p = run("lint", os.path.join(ROOT, "fixtures/skills/valid-basic"))
        self.assertEqual(p.returncode, 0); self.assertIn("valid-basic", p.stdout)
    def test_demo_exit_0(self):
        p = subprocess.run([sys.executable, "demo.py"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
    def test_no_network_imports(self):
        bad = []
        for dirpath, _, files in os.walk(os.path.join(ROOT, "skill_contract_kit")):
            for f in files:
                if f.endswith(".py"):
                    t = open(os.path.join(dirpath, f), encoding="utf-8").read()
                    for needle in ("import requests", "urllib.request", "import socket"):
                        if needle in t:
                            bad.append((f, needle))
        self.assertEqual(bad, [])
    def test_no_network_guard(self):
        # Hermetic guard: validator runs with socket creation blocked via env-free patch in-process
        import socket
        orig = socket.socket
        class Blocked(orig):
            def connect(self, *a, **k):
                raise AssertionError("network attempted")
        socket.socket = Blocked
        try:
            from skill_contract_kit.validator import validate_folder
            from skill_contract_kit.cli import load_registry
            r = validate_folder(os.path.join(ROOT, "fixtures/skills/valid-basic"), load_registry())
            self.assertEqual(r.issues, [])
        finally:
            socket.socket = orig
    def test_eval_determinism(self):
        out = os.path.join(ROOT, "evals", "eval_report.json")
        subprocess.run([sys.executable, "evals/run_evals.py"], cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
        h1 = hashlib.md5(open(out, "rb").read()).hexdigest()
        subprocess.run([sys.executable, "evals/run_evals.py"], cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
        h2 = hashlib.md5(open(out, "rb").read()).hexdigest()
        self.assertEqual(h1, h2)
    def test_serve_lint_endpoint(self):
        # Start server on an ephemeral port, POST /lint, then terminate.
        import time, urllib.request
        proc = subprocess.Popen([sys.executable, "-m", "skill_contract_kit", "serve", "--port", "18765"],
                                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for _ in range(50):
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18765/health", timeout=1) as r:
                        if r.status == 200:
                            break
                except Exception:
                    time.sleep(0.1)
            spec = {"folder_name": "s", "frontmatter": {"name": "s", "description": "A sufficiently long description here."},
                    "body": "hello", "files": ["SKILL.md"],
                    "tools_registry": json.load(open(os.path.join(ROOT, "fixtures/tools.json")))}
            req = urllib.request.Request("http://127.0.0.1:18765/lint",
                                         data=json.dumps(spec).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as r:
                payload = json.loads(r.read())
            self.assertEqual(payload["issues"], [])
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()

if __name__ == "__main__":
    unittest.main()
