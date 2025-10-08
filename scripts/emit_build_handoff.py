#!/usr/bin/env python3
# Writes /handoff/02_build.json from repo state.
# - commit_sha: HEAD SHA (or GITHUB_SHA env if present)
# - changed: files changed in this commit range (fallback: git ls-files -m/-o)
# - generated_notes: optional, from last commit message
import json, os, subprocess, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HANDOFF = ROOT / "handoff"
HANDOFF.mkdir(exist_ok=True)

def sh(cmd):
    return subprocess.check_output(cmd, shell=True, cwd=ROOT).decode().strip()

def main():
    commit_sha = os.getenv("GITHUB_SHA")
    if not commit_sha:
        commit_sha = sh("git rev-parse HEAD")

    # Prefer diff vs parent on CI PRs; fallback to modified/untracked
    changed = []
    try:
        base = os.getenv("GITHUB_BASE_REF")
        if base:
            merge_base = sh(f"git merge-base origin/{base} {commit_sha}")
            diff_out = sh(f"git diff --name-only {merge_base} {commit_sha}")
        else:
            diff_out = sh("git diff --name-only HEAD~1..HEAD")
        changed = [p for p in diff_out.splitlines() if p]
    except Exception:
        pass
    if not changed:
        # fallback to modified + others
        mod = sh("git ls-files -m").splitlines()
        untracked = sh("git ls-files -o --exclude-standard").splitlines()
        changed = [p for p in (mod + untracked) if p]

    msg = sh("git log -1 --pretty=%B").strip()

    out = {
        "commit_sha": commit_sha[:40],
        "changed": changed or [],
        "generated_notes": msg[:2000] if msg else ""
    }
    out_p = HANDOFF / "02_build.json"
    out_p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_p}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
