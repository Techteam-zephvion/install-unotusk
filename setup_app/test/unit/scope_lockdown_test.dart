import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Phase 4: Server Setup App Scope Lockdown Enforcement Tests', () {
    late Directory setupAppLibDir;

    setUp(() {
      final current = Directory.current.path;
      final root = current.endsWith('setup_app')
          ? current
          : '$current/setup_app';
      setupAppLibDir = Directory('$root/lib');
      expect(setupAppLibDir.existsSync(), isTrue,
          reason: 'setup_app/lib directory must exist');
    });

    test('setup_app contains zero Git, Tree-Sitter, LLM, or AST parsing dependencies', () {
      final pubspec = File('${setupAppLibDir.parent.path}/pubspec.yaml');
      expect(pubspec.existsSync(), isTrue);

      final content = pubspec.readAsStringSync().toLowerCase();
      const forbiddenDependencies = [
        'tree_sitter',
        'git',
        'markdown',
        'anthropic',
        'groq',
        'highlight',
        'syntax_highlighter',
        'flutter_highlight',
      ];

      for (final dep in forbiddenDependencies) {
        expect(
          content.contains('$dep:'),
          isFalse,
          reason: 'setup_app must not depend on $dep. Scope is restricted to host hardware & Docker lifecycle.',
        );
      }
    });

    test('setup_app source code contains zero repository ingestion or workspace intelligence logic', () {
      final dartFiles = setupAppLibDir
          .listSync(recursive: true)
          .whereType<File>()
          .where((f) => f.path.endsWith('.dart'));

      const forbiddenTerms = [
        'TreeSitter',
        'tree_sitter',
        'RepositorySnapshot',
        'IngestionService',
        'ProjectDiscoveryEngine',
        'GroundedContextEngine',
        'ProjectReportEngine',
        'KnowledgeService',
        'RepositoryClient',
        'RepositoryManagerScreen',
      ];

      final violations = <String>[];

      for (final file in dartFiles) {
        final content = file.readAsStringSync();
        for (final term in forbiddenTerms) {
          if (content.contains(term)) {
            violations.add('${file.path} contains forbidden term "$term"');
          }
        }
      }

      expect(violations, isEmpty,
          reason: 'setup_app violated scope lockdown:\n${violations.join('\n')}');
    });

    test('setup_app API networking is strictly confined to health and server project provisioning endpoints', () {
      final dartFiles = setupAppLibDir
          .listSync(recursive: true)
          .whereType<File>()
          .where((f) => f.path.endsWith('.dart'));

      const prohibitedWorkspaceEndpoints = [
        '/api/v1/findings',
        '/api/v1/knowledge',
        '/api/v1/ask',
        '/api/v1/reports',
      ];

      final violations = <String>[];

      for (final file in dartFiles) {
        final content = file.readAsStringSync();
        for (final endpoint in prohibitedWorkspaceEndpoints) {
          if (content.contains(endpoint)) {
            violations.add('${file.path} references prohibited workspace API endpoint "$endpoint"');
          }
        }
      }

      expect(violations, isEmpty,
          reason: 'setup_app must not call workspace analysis APIs (findings, ask, knowledge, reports). Those belong in app/.');
    });

    test('setup_app features are strictly confined to host hardware, network/port checks, Docker engine lifecycle, and project provisioning', () {
      final featureDirs = Directory('${setupAppLibDir.path}/features')
          .listSync()
          .whereType<Directory>()
          .map((d) => d.path.split(Platform.pathSeparator).last)
          .toSet();

      const allowedFeatureModules = {
        'welcome',    // Welcome splash
        'target',     // Local Machine or Remote Linux SSH target
        'validation', // Host hardware, CPU, RAM, disk, Docker daemon checks
        'network',    // Port 28000 validation & LAN IP detection
        'config',     // Port, server name & secret generation for .env
        'deploy',     // Docker Compose generation & container orchestration
        'verify',     // Pre-flight /health readiness probing
        'ready',      // Ready screen, copy server URL & app launcher
        'manager',    // Docker container lifecycle (start/stop/restart/delete)
        'wizard',     // Multi-step linear wizard navigation shell
        'projects',   // Server project provisioning & dedicated port allocation
      };

      final unexpectedModules = featureDirs.difference(allowedFeatureModules);

      expect(unexpectedModules, isEmpty,
          reason: 'Unexpected feature modules found in setup_app: $unexpectedModules');
    });
  });
}
