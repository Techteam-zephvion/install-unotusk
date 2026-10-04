#!/usr/bin/env python3
"""
session_helper.py — Utility for Unotusk-MVP Session Recording Skill

Finds the most recent session file in sessions/, computes git commits,
modified files, and context delta since that session, and outputs
a structured markdown draft for the new session note.
"""

import os
import re
import glob
import subprocess
from datetime import datetime

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, text=True, capture_output=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return ""

def get_latest_session_file():
    session_files = sorted(glob.glob("sessions/*.md"), key=os.path.getmtime, reverse=True)
    if not session_files:
        return None, None
    latest = session_files[0]
    mtime = datetime.fromtimestamp(os.path.getmtime(latest))
    return latest, mtime

def get_git_info_since(mtime):
    iso_time = mtime.strftime("%Y-%m-%d %H:%M:%S")
    commits = run_cmd(f'git log --since="{iso_time}" --oneline')
    changed_files = run_cmd(f'git log --since="{iso_time}" --name-only --pretty=format:"" | sort -u')
    current_head = run_cmd("git rev-parse --short HEAD")
    branch = run_cmd("git branch --show-current")
    return {
        "commits": commits.splitlines() if commits else [],
        "changed_files": [f for f in changed_files.splitlines() if f],
        "head": current_head,
        "branch": branch
    }

def main():
    latest_file, mtime = get_latest_session_file()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"=== Last Session File: {latest_file} ===")
    if mtime:
        print(f"Recorded Timestamp: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    git_info = get_git_info_since(mtime) if mtime else {}
    print(f"\n=== Branch: {git_info.get('branch', 'main')} (HEAD: {git_info.get('head', 'unknown')}) ===")
    print(f"Commits since last session ({len(git_info.get('commits', []))} found):")
    for c in git_info.get('commits', []):
        print(f"  - {c}")
        
    print(f"\nFiles modified/touched ({len(git_info.get('changed_files', []))} files):")
    for f in git_info.get('changed_files', []):
        print(f"  - {f}")

if __name__ == "__main__":
    main()
