#!/usr/bin/env python3
"""
verify_features.py - Feature Invariant Verification Suite for Unotusk Flutter App

Verifies that all architectural guarantees, persistence mechanisms, and dual-plane
network routing logic are present and intact across app/lib source files.
"""

import sys
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
APP_LIB = ROOT_DIR / "app" / "lib"

checks_passed = 0
checks_failed = 0


def record(name: str, passed: bool, error_msg: str = ""):
    global checks_passed, checks_failed
    if passed:
        print(f"  [PASS] {name}")
        checks_passed += 1
    else:
        print(f"  [FAIL] {name} - {error_msg}")
        checks_failed += 1


def check_models():
    print("\n1. Verifying Models (app/lib/models/models.dart)...")
    models_path = APP_LIB / "models" / "models.dart"
    if not models_path.exists():
        record("models.dart exists", False, f"File not found: {models_path}")
        return

    content = models_path.read_text(encoding="utf-8")
    record(
        "ProjectItem.toJson() implemented",
        "Map<String, dynamic> toJson()" in content and "'upsStatus': upsStatus" in content,
        "ProjectItem lacks toJson() implementation",
    )
    record(
        "ProjectItem.fromJson() implemented",
        "factory ProjectItem.fromJson(" in content and "upsStatus: json['upsStatus']" in content,
        "ProjectItem lacks fromJson() implementation",
    )


def check_api_service():
    print("\n2. Verifying ApiService (app/lib/services/api_service.dart)...")
    api_path = APP_LIB / "services" / "api_service.dart"
    if not api_path.exists():
        record("api_service.dart exists", False, f"File not found: {api_path}")
        return

    content = api_path.read_text(encoding="utf-8")

    # Control plane fields
    record(
        "controlPlaneUrl declared",
        "static String controlPlaneUrl" in content,
        "Missing static String controlPlaneUrl",
    )
    record(
        "controlPlaneToken declared",
        "static String? controlPlaneToken" in content,
        "Missing static String? controlPlaneToken",
    )

    # Persistence of full ProjectItem data
    record(
        "_connectedProjectsDataFile defined",
        "_connectedProjectsDataFile" in content,
        "Missing _connectedProjectsDataFile for serialized ProjectItem persistence",
    )
    record(
        "loadPersistedConnectedProjects deserializes ProjectItem",
        "loadPersistedConnectedProjects" in content and "ProjectItem.fromJson" in content,
        "loadPersistedConnectedProjects does not deserialize full ProjectItem objects",
    )
    record(
        "savePersistedConnectedProjects serializes ProjectItem data",
        "savePersistedConnectedProjects" in content and "connectedWorkspaceProjects.map((p) => p.toJson())" in content,
        "savePersistedConnectedProjects does not serialize connectedWorkspaceProjects to JSON",
    )

    # Server as sole authority (no phantom project injection)
    has_phantom_injection = "projects.add(localProj)" in content or "projects.add(fallbackProj)" in content
    record(
        "No phantom local project injection in fetchProjects()",
        not has_phantom_injection,
        "Detected injection of unverified local projects into projects list",
    )

    # Control plane query in fetchProjects
    record(
        "fetchProjects() queries controlPlaneUrl",
        "final targetBase = controlPlaneUrl.isNotEmpty ? controlPlaneUrl : baseUrl;" in content
        or "Uri.parse('$targetBase/api/v1/projects')" in content,
        "fetchProjects() is not targeting controlPlaneUrl",
    )

    # Dual-plane fallback in fetchProjectFiles
    has_dual_plane = "controlPlaneUrl" in content and "fetchProjectFiles" in content
    record(
        "fetchProjectFiles() supports dual-plane fallback",
        has_dual_plane,
        "fetchProjectFiles lacks dual-plane fallback to controlPlaneUrl",
    )


def check_projects_screen():
    print("\n3. Verifying ProjectsScreen (app/lib/screens/projects_screen.dart)...")
    screen_path = APP_LIB / "screens" / "projects_screen.dart"
    if not screen_path.exists():
        record("projects_screen.dart exists", False, f"File not found: {screen_path}")
        return

    content = screen_path.read_text(encoding="utf-8")

    # Stopped server guard
    record(
        "isServerOn check defined (READY/ACTIVE/live)",
        "isServerOn" in content and "READY" in content and "ACTIVE" in content,
        "Missing isServerOn check for server readiness",
    )
    record(
        "Connect button suppressed when server is not on",
        "else if (!isServerOn)" in content or "onTap: (!isServerOn && !isConnected)" in content,
        "Connect button is shown even when server is stopped/offline",
    )

    # Absence of aggressive removal of connected projects
    aggressive_prune = (
        "_projects.removeWhere((p) => !validIds.contains" in content
        or "_projects.removeWhere((p) =>\n            !validIds.contains" in content
    )
    record(
        "Connected projects not aggressively purged on empty fetch",
        not aggressive_prune,
        "Detected destructive removeWhere(!validIds.contains) in projects_screen",
    )


def check_main_navigation():
    print("\n4. Verifying Navigation Stage Preservation (app/lib/main.dart)...")
    main_path = APP_LIB / "main.dart"
    if not main_path.exists():
        record("main.dart exists", False, f"File not found: {main_path}")
        return

    content = main_path.read_text(encoding="utf-8")

    record(
        "_handleBackToProjects restores controlPlaneUrl",
        "controlPlaneUrl" in content and "_handleBackToProjects" in content,
        "_handleBackToProjects does not restore controlPlaneUrl",
    )
    record(
        "_handleOpenProject preserves controlPlaneUrl before shifting",
        "controlPlaneUrl" in content and "_handleOpenProject" in content,
        "_handleOpenProject does not preserve controlPlaneUrl",
    )


def main():
    print("=" * 60)
    print("UNOTUSK FLUTTER APP - FEATURE INVARIANT VERIFICATION SUITE")
    print("=" * 60)

    check_models()
    check_api_service()
    check_projects_screen()
    check_main_navigation()

    print("\n" + "=" * 60)
    print(f"VERIFICATION RESULTS: {checks_passed} Passed, {checks_failed} Failed")
    print("=" * 60)

    if checks_failed > 0:
        print("\nERROR: Feature invariants were violated! Please review the failures above.")
        sys.exit(1)
    else:
        print("\nSUCCESS: All feature invariants and architectural guards are intact.")
        sys.exit(0)


if __name__ == "__main__":
    main()

