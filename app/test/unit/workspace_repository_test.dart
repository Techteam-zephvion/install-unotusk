import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/core/network/api_client.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/workspace/data/workspace_repository.dart';
import 'package:app/features/workspace/domain/discovery_summary.dart';
import 'package:app/features/workspace/domain/project_dependency.dart';
import 'package:app/features/workspace/domain/project_file.dart';
import 'package:app/features/workspace/domain/project_finding.dart';
import 'package:app/features/workspace/domain/project_symbol.dart';
import 'package:app/features/workspace/domain/repository_context.dart';

class MockApiClient extends ApiClient {
  MockApiClient(super.storage);

  dynamic mockResponseData;
  String? lastPath;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
    ProgressCallback? onReceiveProgress,
  }) async {
    lastPath = path;
    return Response<T>(
      data: mockResponseData as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: path),
    );
  }
}

void main() {
  late StorageService storage;
  late MockApiClient mockClient;
  late WorkspaceRepository repository;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    storage = StorageService(prefs);
    mockClient = MockApiClient(storage);
    repository = WorkspaceRepository(mockClient);
  });

  group('Workspace Models Deserialization', () {
    test('ProjectRepositoryContext deserializes correctly from backend JSON', () {
      final json = {
        "repository": {
          "id": "repo-123",
          "name": "requests",
          "full_name": "psf/requests",
          "default_branch": "main",
          "html_url": "https://github.com/psf/requests"
        },
        "active_snapshot": {
          "id": "snap-456",
          "repository_id": "repo-123",
          "commit_hash": "a1b2c3d4",
          "branch": "main",
          "status": "COMPLETED",
          "total_files": 121,
          "total_bytes": 1048576,
          "created_at": "2026-09-12T12:00:00Z"
        },
        "metrics": {
          "total_files": 121,
          "languages_count": 2,
          "symbols_count": 450,
          "dependencies_count": 310,
          "language_distribution": {"Python": 115, "TOML": 6}
        }
      };

      final context = ProjectRepositoryContext.fromJson(json);
      expect(context.repository?.name, 'requests');
      expect(context.repository?.fullName, 'psf/requests');
      expect(context.activeSnapshot?.commitHash, 'a1b2c3d4');
      expect(context.metrics.totalFiles, 121);
      expect(context.metrics.symbolsCount, 450);
      expect(context.metrics.dependenciesCount, 310);
      expect(context.metrics.languageDistribution['Python'], 115);
    });

    test('ProjectFile deserializes correctly from backend JSON', () {
      final json = {
        "id": "file-123",
        "snapshot_id": "snap-456",
        "path": "src/requests/sessions.py",
        "filename": "sessions.py",
        "extension": ".py",
        "language": "Python",
        "size_bytes": 28400,
        "content_hash": "hash123",
        "is_binary": false,
        "is_generated": false,
        "is_test": false,
        "line_count": 780,
        "parser_supported": true
      };

      final file = ProjectFile.fromJson(json);
      expect(file.id, 'file-123');
      expect(file.filename, 'sessions.py');
      expect(file.language, 'Python');
      expect(file.lineCount, 780);
      expect(file.isTest, isFalse);
    });

    test('ProjectSymbol deserializes correctly from backend JSON', () {
      final json = {
        "id": "sym-123",
        "file_id": "file-123",
        "name": "Session",
        "symbol_type": "CLASS",
        "qualified_name": "requests.sessions.Session",
        "start_line": 350,
        "end_line": 620,
        "file_path": "src/requests/sessions.py",
        "symbol_metadata": {"methods_count": 14}
      };

      final symbol = ProjectSymbol.fromJson(json);
      expect(symbol.name, 'Session');
      expect(symbol.symbolType, 'CLASS');
      expect(symbol.startLine, 350);
      expect(symbol.endLine, 620);
      expect(symbol.filePath, 'src/requests/sessions.py');
      expect(symbol.metadata['methods_count'], 14);
    });

    test('ProjectDependency deserializes correctly from backend JSON', () {
      final json = {
        "id": "dep-123",
        "source_file_id": "file-123",
        "target_file_id": "file-789",
        "external_package": null,
        "dependency_type": "IMPORT",
        "line_number": 24,
        "source_path": "src/requests/sessions.py",
        "target_path": "src/requests/adapters.py"
      };

      final dep = ProjectDependency.fromJson(json);
      expect(dep.sourceFileId, 'file-123');
      expect(dep.dependencyType, 'IMPORT');
      expect(dep.lineNumber, 24);
      expect(dep.sourcePath, 'src/requests/sessions.py');
      expect(dep.targetPath, 'src/requests/adapters.py');
    });

    test('DiscoverySummary deserializes correctly from backend JSON', () {
      final json = {
        "total_findings": 12,
        "critical_count": 2,
        "high_count": 4,
        "medium_count": 5,
        "low_count": 1,
        "latest_run": {
          "id": "run-123",
          "project_id": "proj-1",
          "snapshot_id": "snap-1",
          "status": "COMPLETED",
          "progress": 100,
          "findings_count": 12,
          "started_at": "2026-09-12T12:00:00Z"
        }
      };

      final summary = DiscoverySummary.fromJson(json);
      expect(summary.totalFindings, 12);
      expect(summary.criticalCount, 2);
      expect(summary.highCount, 4);
      expect(summary.latestRun?.status, 'COMPLETED');
    });

    test('ProjectFinding deserializes correctly from backend JSON', () {
      final json = {
        "id": "find-123",
        "project_id": "proj-1",
        "snapshot_id": "snap-1",
        "category": "ARCHITECTURE",
        "title": "Circular Dependency Detected",
        "description": "sessions.py and adapters.py depend on each other",
        "why_it_matters": "Increases coupling and complicates testing",
        "severity": "CRITICAL",
        "confidence": "HIGH",
        "status": "OPEN",
        "score": 0.95,
        "recommendation": "Extract common interface to a shared module",
        "evidence": [
          {"type": "import", "line": 24, "file": "sessions.py"}
        ],
        "related_entities": ["requests.sessions", "requests.adapters"],
        "created_at": "2026-09-12T12:00:00Z"
      };

      final finding = ProjectFinding.fromJson(json);
      expect(finding.id, 'find-123');
      expect(finding.severity, 'CRITICAL');
      expect(finding.evidence.length, 1);
      expect(finding.relatedEntities.length, 2);
    });
  });

  group('WorkspaceRepository Methods', () {
    test('getProjectRepositoryContext fetches and parses context', () async {
      mockClient.mockResponseData = {
        "repository": {"id": "r1", "name": "requests", "full_name": "psf/requests"},
        "active_snapshot": {"id": "s1", "repository_id": "r1", "commit_hash": "c1", "branch": "main", "status": "COMPLETED", "total_files": 10, "total_bytes": 1000},
        "metrics": {"total_files": 10, "languages_count": 1, "symbols_count": 50, "dependencies_count": 20, "language_distribution": {"Python": 10}}
      };

      final ctx = await repository.getProjectRepositoryContext('proj-1');
      expect(mockClient.lastPath, '/projects/proj-1/repository');
      expect(ctx.repository?.name, 'requests');
      expect(ctx.metrics.totalFiles, 10);
    });

    test('getProjectFiles fetches list of files', () async {
      mockClient.mockResponseData = [
        {
          "id": "f1",
          "snapshot_id": "s1",
          "path": "a.py",
          "filename": "a.py",
          "extension": ".py",
          "language": "Python",
          "size_bytes": 100,
          "content_hash": "h1",
          "is_binary": false,
          "is_generated": false,
          "is_test": false,
          "line_count": 10,
          "parser_supported": true
        }
      ];

      final files = await repository.getProjectFiles('proj-1');
      expect(mockClient.lastPath, contains('/projects/proj-1/files'));
      expect(files.length, 1);
      expect(files.first.filename, 'a.py');
    });

    test('getFindings fetches filtered findings', () async {
      mockClient.mockResponseData = [
        {
          "id": "f1",
          "project_id": "p1",
          "snapshot_id": "s1",
          "category": "ARCHITECTURE",
          "title": "Finding 1",
          "description": "Desc",
          "why_it_matters": "Why",
          "severity": "CRITICAL",
          "confidence": "HIGH",
          "status": "OPEN",
          "score": 0.9,
          "recommendation": "Fix",
          "created_at": "2026-09-12T12:00:00Z"
        }
      ];

      final findings = await repository.getFindings('p1', severity: 'CRITICAL', status: 'OPEN');
      expect(mockClient.lastPath, '/projects/p1/findings');
      expect(findings.length, 1);
      expect(findings.first.severity, 'CRITICAL');
    });
  });
}
