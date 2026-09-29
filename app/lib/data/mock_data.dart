import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';

class MockData {
  // ─── Real Pilot Accounts from LAN_PILOT_MATRIX.md & LAN_PILOT_RUNBOOK.md ───
  static const Map<String, Map<String, String>> pilotAccounts = {
    'lead@acme.com': {
      'name': 'Tech Lead',
      'role': 'Admin / Pilot Lead',
      'node': 'WIN-04 (Windows 11 x64)',
      'ip': '10.0.0.104',
      'password': 'adminpassword123',
    },
    'dev1@acme.com': {
      'name': 'Developer 1',
      'role': 'Member / Frontend',
      'node': 'WIN-01 (Windows 11 x64)',
      'ip': '10.0.0.101',
      'password': 'password123',
    },
    'dev2@acme.com': {
      'name': 'Developer 2',
      'role': 'Member / Backend',
      'node': 'WIN-02 (Windows 11 x64)',
      'ip': '10.0.0.102',
      'password': 'password123',
    },
    'dev3@acme.com': {
      'name': 'Developer 3',
      'role': 'Member / macOS Client',
      'node': 'MAC-01 (macOS 14 Apple Silicon)',
      'ip': '10.0.0.105',
      'password': 'password123',
    },
    'dev4@acme.com': {
      'name': 'Developer 4',
      'role': 'Member / macOS Client',
      'node': 'MAC-02 (macOS 13 Intel/M-series)',
      'ip': '10.0.0.106',
      'password': 'password123',
    },
    'qa1@acme.com': {
      'name': 'QA Engineer',
      'role': 'Member / QA Lead',
      'node': 'WIN-03 (Windows 10 x64)',
      'ip': '10.0.0.103',
      'password': 'password123',
    },
  };

  // ─── Notifications (Real LAN Pilot Telemetry) ───
  static List<NotificationItem> get initialNotifications => [
        NotificationItem(
          id: 'n1',
          type: 'success',
          title: 'Ingestion completed',
          body: 'Unotusk Core API — 847 AST symbols & endpoints indexed across 3 sources',
          time: '14 min ago',
          read: false,
        ),
        NotificationItem(
          id: 'n2',
          type: 'success',
          title: 'Signal Gate passed',
          body: 'Server LAN Hardening — 100/100 tests passed, 0 ruff errors, 0 analyze issues',
          time: '1h ago',
          read: false,
        ),
        NotificationItem(
          id: 'n3',
          type: 'info',
          title: 'LAN Pilot Matrix signed off',
          body: 'Topology verified: SRV-01 (10.0.0.59:8000) active across 6 employee nodes',
          time: '2h ago',
          read: false,
        ),
        NotificationItem(
          id: 'n4',
          type: 'info',
          title: 'Multi-OS Packages Ready',
          body: 'Windows x64 (.zip), macOS (.tar.gz), Linux x64 (.tar.gz) SHA256 checksums valid',
          time: '3h ago',
          read: true,
        ),
        NotificationItem(
          id: 'n5',
          type: 'success',
          title: 'Zero-Secret Redaction Audit',
          body: 'Universal regex sanitizer verified across Python and Flutter client loggers',
          time: 'Yesterday',
          read: true,
        ),
      ];

  // ─── Real Projects from LAN Pilot Task Sheet ───
  static List<ProjectItem> get initialProjects => const [
        ProjectItem(
          id: 'p1',
          name: 'Unotusk Core API',
          upsStatus: 'active',
          ingestionStatus: 'live',
          lastIngestion: '14 min ago',
          fpr: 0.88,
          days: 67,
        ),
        ProjectItem(
          id: 'p2',
          name: 'Unotusk Employee Client',
          upsStatus: 'active',
          ingestionStatus: 'live',
          lastIngestion: '1h ago',
          fpr: 0.94,
          days: 34,
        ),
        ProjectItem(
          id: 'p3',
          name: 'SyncGuard',
          upsStatus: 'active',
          ingestionStatus: 'live',
          lastIngestion: '2h ago',
          fpr: 0.91,
          days: 42,
        ),
        ProjectItem(
          id: 'p4',
          name: 'ORCA Engine',
          upsStatus: 'active',
          ingestionStatus: 'live',
          lastIngestion: '4h ago',
          fpr: 0.86,
          days: 28,
        ),
        ProjectItem(
          id: 'p5',
          name: 'Server Setup App',
          upsStatus: 'active',
          ingestionStatus: 'live',
          lastIngestion: '1d ago',
          fpr: 0.96,
          days: 18,
        ),
      ];

  // ─── Real Activity Stream from LAN Pilot Runbook ───
  static List<ActivityItem> get recentActivities => const [
        ActivityItem(
          id: 'a1',
          icon: '↑',
          text: '847 AST symbols indexed — Unotusk Core API (MVP_build branch)',
          time: '14 min ago',
          color: Color(0xFF6EC8B8),
        ),
        ActivityItem(
          id: 'a2',
          icon: '✓',
          text: 'Signal Gate passed — 100/100 pytest passed in 44.6s · 0 ruff errors',
          time: '1h ago',
          color: Color(0xFF6EC8B8),
        ),
        ActivityItem(
          id: 'a3',
          icon: '↑',
          text: 'LAN Server connected — 10.0.0.59:8000 (v0.1.0) latency 28ms across 6 nodes',
          time: '2h ago',
          color: Color(0xFF6EC8B8),
        ),
        ActivityItem(
          id: 'a4',
          icon: '✓',
          text: 'Silent session restoration confirmed on WIN-01 and MAC-01',
          time: '3h ago',
          color: Color(0xFFD4909A),
        ),
        ActivityItem(
          id: 'a5',
          icon: '!',
          text: 'Docker port isolation verified: Postgres 5432 & Redis 6379 internal only',
          time: '4h ago',
          color: Color(0xFF6EC8B8),
        ),
        ActivityItem(
          id: 'a6',
          icon: '↑',
          text: 'Diagnostic bundle exported with SHA256 verification (57a7fdb1...) in diagnostics/',
          time: '1d ago',
          color: Color(0xFF6EC8B8),
        ),
      ];

  // ─── Recent Chats from LAN Pilot Runbook Step 9 & Matrix ───
  static List<RecentChat> get recentChats => const [
        RecentChat(
          id: 1,
          title: 'What are the primary components in this repository?',
          ago: '20 min ago',
          time: '14:02',
        ),
        RecentChat(
          id: 2,
          title: 'Explain Docker services port isolation and security',
          ago: '1h ago',
          time: '13:15',
        ),
        RecentChat(
          id: 3,
          title: 'Summarize the LAN pilot topology and device assignments',
          ago: '3h ago',
          time: '11:20',
        ),
        RecentChat(
          id: 4,
          title: 'How does AST parsing and symbol extraction work?',
          ago: '1d ago',
          time: '09:41',
        ),
      ];

  // ─── Archived Chats ───
  static List<ArchivedChat> get initialArchivedChats => [
        const ArchivedChat(
          id: 101,
          title: 'Clean server reset & volume safety audit (TASK-LAN-001)',
          date: '2026-09-18',
          messages: 14,
        ),
        const ArchivedChat(
          id: 102,
          title: 'Multi-OS packaging & SHA256 checksum verification',
          date: '2026-09-18',
          messages: 12,
        ),
        const ArchivedChat(
          id: 103,
          title: 'RFC 1918 LAN CORS & dynamic IP resolution audit',
          date: '2026-09-17',
          messages: 22,
        ),
        const ArchivedChat(
          id: 104,
          title: 'pgvector AST symbol extraction benchmark',
          date: '2026-09-16',
          messages: 18,
        ),
      ];

  // ─── Spec History (Tasks from LAN_PILOT_TEST_PREPARATION_TASK_SHEET.md) ───
  static List<SpecHistoryItem> get specHistoryList => const [
        SpecHistoryItem(
          id: 'sh-001',
          query: 'TASK-LAN-001: Clean Server Reset & Reinstallation Utility',
          timestamp: 'Sep 18 · 14:00',
          ago: 'Today',
          isoDate: '2026-09-18',
          queryType: 'cold',
          confidence: 'confirmed',
          score: 0.98,
          fprDelta: null,
          hasBDD: true,
        ),
        SpecHistoryItem(
          id: 'sh-002',
          query: 'TASK-LAN-002: LAN Server Configuration & Dynamic IP Discovery',
          timestamp: 'Sep 18 · 11:30',
          ago: 'Today',
          isoDate: '2026-09-18',
          queryType: 'warm',
          confidence: 'confirmed',
          score: 0.96,
          fprDelta: 0.02,
          hasBDD: true,
        ),
        SpecHistoryItem(
          id: 'sh-003',
          query: 'TASK-LAN-003: Multi-OS Employee Client Packaging',
          timestamp: 'Sep 18 · 09:45',
          ago: 'Today',
          isoDate: '2026-09-18',
          queryType: 'hot',
          confidence: 'confirmed',
          score: 0.95,
          fprDelta: null,
          hasBDD: false,
        ),
        SpecHistoryItem(
          id: 'sh-004',
          query: 'TASK-LAN-005: Structured Application Logging & Secret Sanitization',
          timestamp: 'Sep 17 · 16:20',
          ago: '1d ago',
          isoDate: '2026-09-17',
          queryType: 'cold',
          confidence: 'confirmed',
          score: 0.94,
          fprDelta: null,
          hasBDD: true,
        ),
        SpecHistoryItem(
          id: 'sh-005',
          query: 'TASK-LAN-008: 5-Point LAN Connectivity Preflight Check',
          timestamp: 'Sep 17 · 10:15',
          ago: '1d ago',
          isoDate: '2026-09-17',
          queryType: 'warm',
          confidence: 'confirmed',
          score: 0.99,
          fprDelta: null,
          hasBDD: true,
        ),
      ];

  // ─── Spec Chat Threads ───
  static Map<String, List<Map<String, String>>> get specChatThreads => {
        'sh-001': [
          {
            'role': 'user',
            'text': 'TASK-LAN-001: Clean Server Reset & Reinstallation Utility'
          },
          {
            'role': 'ai',
            'text':
                '[CONFIRMED · score 0.98] Implemented clean_server_reset.py with strict isolation:\n\nFeature: Clean Server Reset\n  Scenario: Reset preserving persistent databases\n    Given the Unotusk Docker Compose stack is running\n    When the operator executes ./scripts/clean_server_reset.sh\n    Then unotusk-api and unotusk-worker containers are stopped and rebuilt\n    And unotusk-postgres and unotusk-redis data volumes remain preserved\n    And all 24 foreign containers on the host machine remain 100% untouched\n\n  Scenario: Factory wipe with mandatory confirmation\n    Given persistent data needs to be wiped\n    When the operator executes ./scripts/clean_server_reset.sh --wipe-data\n    Then an explicit prompt requires typing confirmation\n    And fresh database migrations run deterministically'
          }
        ],
        'sh-002': [
          {
            'role': 'user',
            'text': 'TASK-LAN-002: LAN Server Configuration & Dynamic IP Discovery'
          },
          {
            'role': 'ai',
            'text':
                '[CONFIRMED · score 0.96] Dynamic LAN IP resolver implemented via lan_detector.dart:\n- Automatically scans RFC 1918 private IPv4 ranges (10.x, 172.16-31.x, 192.168.x).\n- Automatically ignores virtual bridges (docker0, br-*, virbr*, tun*).\n- Displays active LAN URL: http://10.0.0.59:8000 with green "LAN REACHABLE" badge.'
          }
        ],
        'sh-004': [
          {
            'role': 'user',
            'text': 'TASK-LAN-005: Structured Application Logging & Secret Sanitization'
          },
          {
            'role': 'ai',
            'text':
                '[CONFIRMED · score 0.94] 24 distinct operational event types with 500-event circular buffer and automated regex redaction for Bearer tokens, raw JWTs, passwords, and database connection strings.'
          }
        ],
      };

  // ─── Real Topology Ontology Graph ───
  static List<OntologyNode> get ontologyNodes => const [
        OntologyNode(
            id: 0, cx: 120, cy: 150, label: 'SRV-01 (10.0.0.59)', type: 'Service'),
        OntologyNode(
            id: 1, cx: 280, cy: 80, label: 'unotusk-api (8000)', type: 'Service'),
        OntologyNode(
            id: 2, cx: 280, cy: 220, label: 'unotusk-worker', type: 'Service'),
        OntologyNode(
            id: 3, cx: 440, cy: 60, label: 'unotusk-postgres (5432)', type: 'Service'),
        OntologyNode(
            id: 4, cx: 440, cy: 150, label: 'unotusk-redis (6379)', type: 'Service'),
        OntologyNode(
            id: 5, cx: 600, cy: 80, label: 'WIN-04 (lead@acme.com)', type: 'Person'),
        OntologyNode(
            id: 6, cx: 600, cy: 170, label: 'WIN-01 (dev1@acme.com)', type: 'Person'),
        OntologyNode(
            id: 7, cx: 600, cy: 260, label: 'MAC-01 (dev3@acme.com)', type: 'Person'),
        OntologyNode(
            id: 8, cx: 440, cy: 250, label: 'MVP_build branch', type: 'Commit'),
      ];

  static List<List<int>> get ontologyEdges => const [
        [0, 1], // Server -> API
        [0, 2], // Server -> Worker
        [1, 3], // API -> Postgres
        [1, 4], // API -> Redis
        [2, 3], // Worker -> Postgres
        [2, 4], // Worker -> Redis
        [1, 5], // API <- WIN-04 Admin
        [1, 6], // API <- WIN-01 Dev1
        [1, 7], // API <- MAC-01 Dev3
        [2, 8], // Worker indexes MVP_build branch
      ];

  // ─── Hero Cards (Real Questions from LAN_PILOT_RUNBOOK.md Step 9) ───
  static List<HeroCardItem> get heroCards => const [
        HeroCardItem(
          title: 'What are the primary components in this repository?',
          tag: 'Runbook Step 9 · Architecture',
          icon: LucideIcons.boxes,
        ),
        HeroCardItem(
          title: 'Explain Docker services port isolation and security',
          tag: 'Matrix §3 · Security',
          icon: LucideIcons.shieldCheck,
        ),
        HeroCardItem(
          title: 'Summarize the LAN pilot topology and device assignments',
          tag: 'Matrix §2 · Hardware',
          icon: LucideIcons.network,
        ),
        HeroCardItem(
          title: 'How does AST parsing and symbol extraction work?',
          tag: 'Task Sheet §4 · Ingestion',
          icon: LucideIcons.cpu,
        ),
      ];

  static List<String> get querySuggestions => const [
        'What are the primary components in this repository?',
        'Explain Docker services port isolation and security',
        'Summarize the LAN pilot topology and device assignments',
        'How does AST parsing and symbol extraction work?',
      ];

  // ─── Fallback Response ───
  static QueryResponseData get fallbackResponse => cannedResponses[
          'What are the primary components in this repository?'] ??
      const QueryResponseData(
        segments: [
          ResponseSegment(
            text:
                'The Unotusk MVP comprises 4 Docker services on the Linux host (API on port 8000, Worker, pgvector Postgres on 5432, and Redis on 6379), connecting to native Employee Client apps over LAN (10.0.0.59:8000).',
            tag: 'CONFIRMED',
          ),
        ],
        meta: 'LAN Pilot Telemetry · http://10.0.0.59:8000 · Verified',
        queryType: 'warm',
        confidence: 'confirmed',
      );

  // ─── Canned Grounded Intelligence Responses ───
  static Map<String, QueryResponseData> get cannedResponses => {
        'What are the primary components in this repository?':
            const QueryResponseData(
          segments: [
            ResponseSegment(
              text:
                  'The Unotusk MVP repository comprises 4 core Docker backend services orchestrated via Docker Compose:\n\n'
                  '1. unotusk-api (FastAPI): Bound to port 8000 on host (0.0.0.0:8000). Provides REST endpoints, JWT authentication (HS256), request correlation middleware (X-Request-ID), and LAN CORS validation.\n'
                  '2. unotusk-worker: Background ingestion engine executing AST parsing, symbol extraction, git diff+commit pairing, and semantic embedding generation.\n'
                  '3. unotusk-postgres: PostgreSQL database with pgvector extension for high-dimensional code retrieval. Internal port 5432 only (strictly unmapped to host).\n'
                  '4. unotusk-redis: High-throughput task queue and caching layer. Internal port 6379 only (isolated from LAN).\n\n'
                  'Frontend clients include the Flutter Employee App (Windows, macOS, Linux native desktop bundles) and the Server Setup App (host manager with dynamic RFC 1918 LAN IP discovery).',
              tag: 'CONFIRMED',
            ),
          ],
          meta:
              'Query resolved · 310ms · 4 sources · LAN_PILOT_RUNBOOK.md · LAN_PILOT_MATRIX.md · docker-compose.yml',
          queryType: 'warm',
          confidence: 'confirmed',
          reasoning: ReasoningModel(
            compositeScore: 0.98,
            components: [
              ScoreComponent(label: 'P_class', score: 0.99),
              ScoreComponent(label: 'S_auth', score: 0.97),
              ScoreComponent(label: 'T_match', score: 0.98),
              ScoreComponent(label: 'D_atom', score: 0.96),
              ScoreComponent(label: 'R_ragas', score: 0.99),
            ],
            routingPath: [
              'Warm query',
              'AST & service manifest index',
              'Confirmed gate (≥0.80)',
              'Output'
            ],
            ontologyEdges: [
              'composed_of',
              'orchestrates',
              'exposes',
              'isolates'
            ],
            citations: [
              'LAN_PILOT_RUNBOOK.md §1',
              'LAN_PILOT_MATRIX.md §1',
              'docker-compose.yml',
              'TASK-LAN-001'
            ],
          ),
        ),

        'Explain Docker services port isolation and security':
            const QueryResponseData(
          segments: [
            ResponseSegment(
              text:
                  'The Unotusk MVP LAN deployment enforces strict zero-trust network boundaries:\n\n'
                  '• Exposed Boundary: ONLY Port 8000 (unotusk-api) is bound to 0.0.0.0:8000 to serve employee desktop clients on the LAN.\n'
                  '• Database & Redis Isolation: unotusk-postgres (5432) and unotusk-redis (6379) are attached solely to the private Docker bridge network ("unotusk-network"). Their host port bindings are null, rendering them completely unreachable from any laptop on the LAN.\n'
                  '• CORS LAN Whitelisting: The FastAPI backend enforces an allow_origin_regex strictly limiting traffic to RFC 1918 private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) and localhost.\n'
                  '• Zero-Secret Logging: Both the Python server and Flutter clients execute automatic regex sanitization across log streams, stripping JWTs, Bearer headers, API keys, and connection strings.',
              tag: 'CONFIRMED',
            ),
          ],
          meta:
              'Query resolved · 280ms · 3 sources · LAN_PILOT_MATRIX.md §3 · TASK-LAN-002 · TASK-LAN-006',
          queryType: 'warm',
          confidence: 'confirmed',
          reasoning: ReasoningModel(
            compositeScore: 0.97,
            components: [
              ScoreComponent(label: 'P_class', score: 0.98),
              ScoreComponent(label: 'S_auth', score: 0.96),
              ScoreComponent(label: 'T_match', score: 0.97),
              ScoreComponent(label: 'D_atom', score: 0.95),
              ScoreComponent(label: 'R_ragas', score: 0.98),
            ],
            routingPath: [
              'Warm query',
              'Network security topology',
              'Confirmed gate (≥0.80)',
              'Output'
            ],
            ontologyEdges: [
              'protects',
              'isolates',
              'sanitizes',
              'validates'
            ],
            citations: [
              'LAN_PILOT_MATRIX.md §3',
              'TASK-LAN-002',
              'TASK-LAN-006',
              'main.py'
            ],
          ),
        ),

        'Summarize the LAN pilot topology and device assignments':
            const QueryResponseData(
          segments: [
            ResponseSegment(
              text:
                  'The LAN Pilot operates on a private subnet (10.0.0.0/24) with 7 designated hardware nodes:\n\n'
                  '• Node 1 (SRV-01): Linux x86_64 host (IP 10.0.0.59) running Docker stack (API, Worker, Postgres, Redis).\n'
                  '• Nodes 2-4: Windows 10/11 laptops (10.0.0.101-103) running unotusk-employee-windows-x64.zip for dev1@acme.com, dev2@acme.com, and qa1@acme.com.\n'
                  '• Node 5 (WIN-04): Windows 11 laptop (10.0.0.104) assigned to lead@acme.com (Admin) for codebase ingestion.\n'
                  '• Nodes 6-7 (MAC-01/02): macOS laptops (10.0.0.105-106) running unotusk-employee-macos.tar.gz for dev3@acme.com and dev4@acme.com.\n\n'
                  'All 6 client nodes communicate directly with http://10.0.0.59:8000 with sub-100ms response times.',
              tag: 'CONFIRMED',
            ),
          ],
          meta:
              'Query resolved · 350ms · 2 sources · LAN_PILOT_MATRIX.md §2 · LAN_PILOT_RUNBOOK.md §8',
          queryType: 'warm',
          confidence: 'confirmed',
          reasoning: ReasoningModel(
            compositeScore: 0.99,
            components: [
              ScoreComponent(label: 'P_class', score: 1.0),
              ScoreComponent(label: 'S_auth', score: 0.98),
              ScoreComponent(label: 'T_match', score: 0.99),
              ScoreComponent(label: 'D_atom', score: 0.98),
              ScoreComponent(label: 'R_ragas', score: 0.99),
            ],
            routingPath: [
              'Warm query',
              'Hardware topology map',
              'Confirmed gate',
              'Output'
            ],
            ontologyEdges: ['allocates', 'assigns', 'routes'],
            citations: ['LAN_PILOT_MATRIX.md §2', 'LAN_PILOT_RUNBOOK.md §8'],
          ),
        ),

        'How does AST parsing and symbol extraction work?':
            const QueryResponseData(
          segments: [
            ResponseSegment(
              text:
                  'When a codebase is linked (e.g. Unotusk Core API on MVP_build branch), unotusk-worker triggers multi-pass ingestion:\n\n'
                  '1. AST Extraction: Traverses Python/Dart/TS source files to extract classes, methods, decorators, route handlers, and call hierarchies.\n'
                  '2. Commit Correlation: Indexes Git commit histories and diff chunks, associating code modifications with architectural decisions.\n'
                  '3. Vector Indexing: Generates dense semantic embeddings stored in PostgreSQL with pgvector, enabling sub-second natural language code retrieval.\n'
                  '4. Zero Cross-Talk: The background worker isolates project graphs per organization so multiple clients can query concurrently without data bleed.',
              tag: 'CONFIRMED',
            ),
          ],
          meta:
              'Query resolved · 420ms · 3 sources · LAN_PILOT_TASK_SHEET.md §4 · unotusk-worker',
          queryType: 'warm',
          confidence: 'confirmed',
          reasoning: ReasoningModel(
            compositeScore: 0.95,
            components: [
              ScoreComponent(label: 'P_class', score: 0.96),
              ScoreComponent(label: 'S_auth', score: 0.94),
              ScoreComponent(label: 'T_match', score: 0.95),
              ScoreComponent(label: 'D_atom', score: 0.93),
              ScoreComponent(label: 'R_ragas', score: 0.96),
            ],
            routingPath: [
              'Warm query',
              'AST engine specifications',
              'Confirmed gate',
              'Output'
            ],
            ontologyEdges: ['extracts', 'indexes', 'embeds'],
            citations: ['TASK-LAN-005', 'LAN_PILOT_RUNBOOK.md §9'],
          ),
        ),
      };

  // ─── Domain Rules from LAN Pilot Security Matrix ───
  static const Set<String> blockedDomains = {
    'gmail.com',
    'yahoo.com',
    'hotmail.com',
    'outlook.com',
    'icloud.com',
    'proton.me',
    'me.com',
    'live.com',
    'aol.com',
    'ymail.com',
  };

  static const Map<String, Map<String, String>> knownOrganizations = {
    'acme.com': {
      'name': 'Acme Corp',
      'provider': 'Acme Enterprise OIDC (10.0.0.59:8000)',
      'issuer': 'http://10.0.0.59:8000/auth',
      'type': 'custom',
    },
    'unotusk.com': {
      'name': 'Unotusk Internal',
      'provider': 'Unotusk Local LAN SSO (10.0.0.59:8000)',
      'issuer': 'http://10.0.0.59:8000',
      'type': 'google',
    },
    'meta.com': {
      'name': 'Meta Platforms',
      'provider': 'Okta Workforce Identity OIDC',
      'issuer': 'https://auth.meta.com',
      'type': 'okta',
    },
    'microsoft.com': {
      'name': 'Microsoft Enterprise',
      'provider': 'Microsoft Entra ID (Azure AD)',
      'issuer': 'https://login.microsoftonline.com',
      'type': 'microsoft',
    },
  };
}
