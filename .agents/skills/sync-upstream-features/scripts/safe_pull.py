#!/usr/bin/env python3
"""
safe_pull.py - Safe Upstream Pull & Merge with Feature Invariant Protection

Fetches updates from a remote git repository/branch, performs safety checks,
handles conflicts, and verifies that all feature invariants remain intact.
"""

import sys
import subprocess
import argparse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
VERIFY_SCRIPT = SKILL_DIR / "verify_features.py"
REPO_DIR = Path(__file__).resolve().parents[4]


def run_git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git"] + args
    res = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[ERROR] Git command failed: {' '.join(cmd)}")
        if res.stderr:
            print(res.stderr.strip())
        if res.stdout:
            print(res.stdout.strip())
        sys.exit(res.returncode)
    return res


def check_dirty() -> bool:
    res = run_git(["status", "--porcelain"], check=False)
    # Check if tracked files have changes
    lines = [line for line in res.stdout.strip().splitlines() if line and not line.startswith("??")]
    return len(lines) > 0


def main():
    parser = argparse.ArgumentParser(
        description="Safely pull upstream changes while keeping repository feature invariants intact."
    )
    parser.add_argument(
        "--remote",
        default="target",
        help="Git remote name to pull from (default: 'target')",
    )
    parser.add_argument(
        "--branch",
        default="Frontend-sidebar-extended",
        help="Branch to pull from (default: 'Frontend-sidebar-extended')",
    )
    parser.add_argument(
        "--strategy",
        choices=["merge", "rebase", "fetch-only"],
        default="merge",
        help="Pull strategy: merge (default), rebase, or fetch-only",
    )
    parser.add_argument(
        "--stash",
        action="store_true",
        help="Automatically stash uncommitted tracked changes before pulling and pop after",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip post-pull feature verification suite",
    )

    args = parser.parse_args()

    print("=" * 65)
    print("UNOTUSK SAFE PULL & FEATURE INVARIANT PRESERVATION RUNBOOK")
    print("=" * 65)
    print(f"Target Remote : {args.remote}")
    print(f"Target Branch : {args.branch}")
    print(f"Strategy      : {args.strategy}")
    print(f"Working Dir   : {REPO_DIR}")
    print("=" * 65)

    # 1. Check working directory cleanliness
    is_dirty = check_dirty()
    did_stash = False

    if is_dirty:
        if args.stash:
            print("\n[INFO] Stashing uncommitted local changes...")
            run_git(["stash", "save", "safe_pull_pre_stash"])
            did_stash = True
        else:
            print("\n[WARNING] Working directory contains uncommitted tracked changes:")
            res = run_git(["status", "--short"], check=False)
            print(res.stdout.strip())
            print("\nTo proceed safely, either commit your changes, pass --stash, or stash manually.")
            sys.exit(1)

    # 2. Fetch remote branch
    print(f"\n[STEP 1/3] Fetching latest refs from '{args.remote}/{args.branch}'...")
    run_git(["fetch", args.remote, args.branch])
    print("  Fetch completed successfully.")

    if args.strategy == "fetch-only":
        print("\n[INFO] Strategy is 'fetch-only'. Remote references updated without merging.")
        if did_stash:
            print("[INFO] Restoring stashed changes...")
            run_git(["stash", "pop"])
        sys.exit(0)

    # 3. Perform Merge or Rebase
    print(f"\n[STEP 2/3] Performing git {args.strategy} with '{args.remote}/{args.branch}'...")
    if args.strategy == "merge":
        merge_res = run_git(["merge", f"{args.remote}/{args.branch}"], check=False)
        if merge_res.returncode != 0:
            print("\n[CONFLICT] Merge conflicts detected during git merge!")
            print(merge_res.stdout.strip())
            print("\n[ACTION REQUIRED]:")
            print("  1. Resolve conflicts in your editor.")
            print("  2. Consult references/feature_invariants.md to ensure our architectural guards are preserved.")
            print("  3. Run: python .agents/skills/sync-upstream-features/scripts/verify_features.py")
            print("  4. Once all 15 checks pass, stage the resolved files: git add <files>")
            print("  5. Complete the merge: git commit")
            sys.exit(1)
        else:
            print("  Merge succeeded cleanly.")
    elif args.strategy == "rebase":
        rebase_res = run_git(["rebase", f"{args.remote}/{args.branch}"], check=False)
        if rebase_res.returncode != 0:
            print("\n[CONFLICT] Conflicts detected during git rebase!")
            print(rebase_res.stdout.strip())
            print("\n[ACTION REQUIRED]: Resolve conflicts, run verify_features.py, and 'git rebase --continue'.")
            sys.exit(1)
        else:
            print("  Rebase succeeded cleanly.")

    # 4. Pop stash if we stashed
    if did_stash:
        print("\n[INFO] Restoring stashed local changes...")
        pop_res = run_git(["stash", "pop"], check=False)
        if pop_res.returncode != 0:
            print("[WARNING] Conflicts occurred while applying stash. Please resolve manually.")

    # 5. Run Verification Suite
    if not args.skip_verify:
        print("\n[STEP 3/3] Running Feature Invariant Verification Suite...")
        v_res = subprocess.run([sys.executable, str(VERIFY_SCRIPT)], cwd=REPO_DIR)
        if v_res.returncode != 0:
            print("\n[ALERT] One or more feature invariants failed after the pull!")
            print("Please inspect the failed checks and restore the required logic.")
            sys.exit(1)

    print("\n" + "=" * 65)
    print("SUCCESS: Pull completed and all feature invariants verified intact!")
    print("=" * 65)


if __name__ == "__main__":
    main()

