# UNOTUSK MVP Release Manifest

## Version Information
- **Version**: v1.0.0
- **Release Branch**: main
- **Commit**: `55296384b3401703b94643e8bc259e4433c54738`

## Server Images (GHCR)
- `ghcr.io/techteam-zephvion/unotusk-api:v1.0.0`
- `ghcr.io/techteam-zephvion/unotusk-worker:v1.0.0`

## Downloadable Artifacts (GitHub Release Assets)
- `unotusk-server-linux-x64.tar.gz` (Setup App/Server Manager for Linux)
- `unotusk-employee-linux-x64.tar.gz` (Employee Client for Linux)
- `unotusk-employee-windows-x64.msi` (Employee Client for Windows)
- `unotusk-employee-macos.dmg` (Employee Client for macOS)

## Supported Platforms
- **Server Deployment**: Linux x64
- **Employee Client**: Windows x64, macOS, Linux x64

## Cryptographic Guarantees
- All release assets are accompanied by `.sha256` checksum files generated within the CI pipeline.
- GitHub Personal Access Tokens (PATs) provisioned through the Server Manager are symmetrically encrypted at rest in PostgreSQL using AES-128 via Fernet encryption tied to the deployed server's `AUTH_SECRET`.
