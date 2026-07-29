#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Release Script
#  Usage: ./scripts/release.sh v1.2.0
#
#  What it does:
#    1. Validates the version tag format
#    2. Builds the installer tarball
#    3. Generates SHA-256 checksum
#    4. Creates a git tag
#    5. Pushes tag (triggers GitHub Actions release workflow)
# ==============================================================================
set -Eeuo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "  ${CYAN}→${RESET} $*"; }
success() { echo -e "  ${GREEN}✔${RESET} $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; }
fail()    { echo -e "  ${RED}✘${RESET} $*"; exit 1; }

VERSION="${1:-}"
[[ -z "$VERSION" ]] && fail "Usage: $0 <version>  (e.g. v1.2.0)"
[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || fail "Version must be in format: v1.2.0"

# Must be run from repo root
[[ -f "vercel.json" ]] || fail "Run from the repository root."

echo ""
echo -e "${BOLD}UNOTUSK Release — ${VERSION}${RESET}"
echo ""

# ── Check working tree is clean ────────────────────────────────────────────────
if ! git diff --quiet || ! git diff --cached --quiet; then
  fail "Working tree has uncommitted changes. Commit or stash them first."
fi
success "Working tree is clean."

# ── Build tarball ─────────────────────────────────────────────────────────────
DIST_DIR="dist"
TARBALL="${DIST_DIR}/unotusk-installer.tar.gz"
mkdir -p "$DIST_DIR"

info "Building installer tarball..."
tar -czf "$TARBALL" \
  --transform "s|^|installer/|" \
  --exclude="*.DS_Store" \
  installer/install.sh \
  installer/uninstall.sh \
  installer/update.sh \
  installer/doctor.sh \
  installer/backup.sh \
  installer/restore.sh \
  installer/verify.sh \
  installer/rollback.sh

success "Tarball: $TARBALL ($(du -sh "$TARBALL" | cut -f1))"

# ── Generate checksum ─────────────────────────────────────────────────────────
sha256sum "$TARBALL" > "${TARBALL}.sha256"
CHECKSUM=$(awk '{print $1}' "${TARBALL}.sha256")
success "SHA-256: $CHECKSUM"

# ── Tag and push ──────────────────────────────────────────────────────────────
info "Creating git tag: $VERSION"
git tag -a "$VERSION" -m "Release $VERSION"
success "Tag created."

info "Pushing tag to origin..."
git push origin "$VERSION"
success "Tag pushed — GitHub Actions will create the release and upload assets."

echo ""
echo -e "${BOLD}Release ${VERSION} triggered.${RESET}"
echo "  Monitor: https://github.com/unotusk/install/actions"
echo "  Release: https://github.com/unotusk/install/releases/tag/${VERSION}"
echo ""
echo "  Bootstrap URL: https://install.unotusk.com"
echo "  Direct asset:  https://github.com/unotusk/install/releases/download/${VERSION}/unotusk-installer.tar.gz"
echo ""
