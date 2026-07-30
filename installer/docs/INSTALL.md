# UNOTUSK Platform Installation Guide

This document describes how to deploy and configure the on-premises **UNOTUSK Platform** using the modular enterprise installer.

---

## System Requirements

| Resource | Minimum | Recommended |
| :--- | :--- | :--- |
| **OS** | Ubuntu 24.04+, Debian 12+, Pop!_OS | Ubuntu 24.04 LTS |
| **Architecture** | amd64 (x86_64), arm64 (aarch64) | amd64 |
| **CPU Cores** | 2 cores | 4+ cores |
| **Memory (RAM)** | 4 GB | 8 GB+ |
| **Storage** | 10 GB | 50 GB+ (SSD) |

---

## Prerequisites

Ensure the following packages are installed on the host:
- `docker-ce` (v24.0+)
- `docker-compose-plugin` (v2.0+)
- `curl`, `openssl`, `nslookup`, `tar`, `gzip`

Ports **80** and **443** must be free on the host interface. All other stack ports are kept inside private Docker container networks.

---

## Installation Steps

### 1. Execute Bootstrap Command
Run the bootstrap curl payload on the target machine:
```bash
curl -fsSL https://install.unotusk.com | sudo bash
```

Alternatively, clone the repository and run the setup script:
```bash
sudo ./install.sh
```

### 2. Setup Wizard Prompts
The interactive wizard will prompt you to enter:
- **Organization Name**
- **License Key**
- **Platform URL** (e.g., `https://platform.unotusk.com:50051`)
- **Host Domain** (used for HTTPS certificate bindings)
- **HTTPS Certificate Type** (Self-Signed, Custom, or Let's Encrypt)
- **Administrator Email and Password**

### 3. Check Service Status
Once the installer finishes, query service health:
```bash
sudo unotusk status
sudo unotusk doctor
```

---

## CLI Console Commands

Operate the platform lifecycle using the global binary wrapper:
- `unotusk start` — Start all services in order.
- `unotusk stop` — Stop all services.
- `unotusk restart` — Safe reboot of all services.
- `unotusk logs` — Tail live docker outputs.
- `unotusk doctor` — Run all diagnostic assertions.
- `unotusk update` — Run platform upgrades.
- `unotusk backup` — Run database and volume backups.
- `unotusk restore <archive>` — Restore state from a backup package.
- `unotusk uninstall` — Remove UNOTUSK from the system.
