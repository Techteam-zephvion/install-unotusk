---
name: record-session
description: Creates a structured, standardized session log in the root sessions/ folder documenting all achievements, architectural decisions, git commits, code modifications, and pending tasks since the previous session. Use whenever the user asks to create session notes, save session notes, record progress, or document what was done since the last session in Unotusk-MVP.
---

# Session Recording Skill — Unotusk MVP

This skill guides the agent in generating high-fidelity, standardized session notes in the root [`sessions/`](file:///home/devils/PRO/Unotusk-MVP/sessions/) directory, capturing everything accomplished **since the previous session log**.

---

## 1. Discovery: Identify the Last Session

Before writing any new notes, determine what was already documented to avoid redundant summaries:

1. Run the helper script to identify the latest session file and changes since then:
   ```bash
   python3 .agents/skills/record-session/scripts/session_helper.py
   ```
2. Read the latest session file in `sessions/` (e.g. `sessions/session_YYYY_MM_DD.md` or `sessions/YYYY-MM-DD_HH-MM-SS_chat.md`) to establish the previous boundary.
3. Review `git log` and `git diff` since the timestamp of that last session file.

---

## 2. File Naming Conventions

Session logs are stored directly in `sessions/`:
- **Default naming**: `sessions/session_YYYY_MM_DD.md` (using today's date).
- **If a session file already exists for today**:
  - If the previous file was from earlier in the day and covered a distinct phase, name the new file:
    `sessions/session_YYYY_MM_DD_part2.md` or `sessions/session_YYYY_MM_DD_<topic>.md` (e.g. `sessions/session_2026_10_04_workflows.md`).
  - If the user prefers a single consolidated daily log, append the new phase to today's existing session file under a new `## Phase` section.

---

## 3. Mandatory Invariants & Repository Rules

When writing any session notes in this repository:
1. **Corporate Entity**: Always use `Unotusk Pvt. Ltd.` (never `Zephvion`).
2. **Zero External Project Bleed**: Strictly exclude any mentions of unrelated external projects (specifically, **zero** references to FlyAway parking or non-Unotusk code).
3. **No Leaked Internal Links**: Do not expose raw internal repository URLs or tokens.
4. **Clickable Links**: All referenced files and code symbols must have valid Markdown links using the `file://` scheme (e.g., `[filename](file:///path/to/file)`).
5. **Factual Engineering Tone**: Keep the record crisp, technical, structured, and factual.

---

## 4. Standard Session Note Structure

Every session file generated must follow this canonical template:

```markdown
# Conversation Session Log — YYYY-MM-DD

**Session Date**: YYYY-MM-DD  
**Workspace**: `/home/devils/PRO/Unotusk-MVP`  
**Primary Focus**: <1-line summary of primary engineering objectives>

---

## 1. Executive Summary of Achievements
<Numbered list of core technical achievements completed in this session>

---

## 2. Chronological Log of Actions, Decisions & Bug Fixes
<Grouped into clear phases or technical topics>

### Phase / Topic A: <Title>
- **Problem / Requirement**: <Context>
- **Architectural Decision**: <Rationale>
- **Implementation**: <Exact files modified and changes made>
- **Verification**: <Commands run, tests executed, outputs verified>

---

## 3. Files Created, Modified & Deleted
| Action | File Path | Purpose |
| :--- | :--- | :--- |
| Created | `path/to/file` | <Summary> |
| Modified | `path/to/file` | <Summary> |
| Deleted | `path/to/file` | <Summary> |

---

## 4. Active Infrastructure & Verification Status
- **Git State**: Current branch, HEAD commit hash, and sync status with `origin`.
- **Live Deployments**: Status of `https://install.unotusk.com` and `https://docs.unotusk.com`.
- **Test Suite Status**: Pytest, Ruff linting, Flutter desktop test/analyze results.
- **Workflow / CI Pipeline**: Active triggers and release automation status.

---

## 5. Outstanding & Pending Tasks
<Bullet points of what remains open or recommended for the next session>
```

---

## 5. Execution Workflow

When the user asks to record or create session notes:
1. Run `.agents/skills/record-session/scripts/session_helper.py` to inspect recent git commits and modified files.
2. Read the latest session file to ensure no duplicate entries.
3. Synthesize the new session log covering only the delta since that boundary.
4. Write the file to `sessions/`.
5. Report the created session file path to the user with a concise summary.
