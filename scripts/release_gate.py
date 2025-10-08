#!/usr/bin/env python3
# Hard gate for release eligibility, reading /handoff/03_test.json.
# - Fails if tests_passed is false
# - Fails if coverage < MIN_COVERAGE (env MIN_COVERAGE, default 0.90)
# - Optionally assert existence of coverage/junit artifacts
# Usage: release_gate.py [handoff_path]
import json, os, sys, pathlib

def die(msg):
    print(f"RELEASE_GATE: {msg}", file=sys.stderr); sys.exit(1)

def main():
    handoff = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "handoff/03_test.json")
    if not handoff.exists():
        die(f"missing handoff file: {handoff}")

    data = json.loads(handoff.read_text(encoding="utf-8"))
    min_cov = float(os.getenv("MIN_COVERAGE", "0.90"))

    if not data.get("tests_passed", False):
        die("tests_passed=false")

    cov = float(data.get("coverage", 0.0))
    if cov < min_cov:
        die(f"coverage {cov:.3f} < required {min_cov:.3f}")

    arts = data.get("artifacts", {})
    for k in ("coverage_xml", "junit"):
        p = pathlib.Path(arts.get(k, ""))
        if not p.exists():
            die(f"artifact missing: {k} -> {p}")

    print(f"RELEASE_GATE: ok (coverage={cov:.3f} \u2265 {min_cov:.3f})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
