/// Workspace domain models ported from install-unotusk repo.
/// These models represent the rich data structures for the workspace features.
library;

// ─── Project File ───────────────────────────────────────
class ProjectFile {
  final String id;
  final String snapshotId;
  final String path;
  final String filename;
  final String extension;
  final String language;
  final int sizeBytes;
  final String contentHash;
  final bool isBinary;
  final bool isGenerated;
  final bool isTest;
  final int lineCount;
  final bool parserSupported;

  const ProjectFile({
    required this.id,
    required this.snapshotId,
    required this.path,
    required this.filename,
    required this.extension,
    required this.language,
    required this.sizeBytes,
    required this.contentHash,
    required this.isBinary,
    required this.isGenerated,
    required this.isTest,
    required this.lineCount,
    required this.parserSupported,
  });

  factory ProjectFile.fromJson(Map<String, dynamic> json) {
    return ProjectFile(
      id: json['id']?.toString() ?? '',
      snapshotId: json['snapshot_id']?.toString() ?? '',
      path: json['path']?.toString() ?? '',
      filename: json['filename']?.toString() ?? '',
      extension: json['extension']?.toString() ?? '',
      language: json['language']?.toString() ?? 'UNKNOWN',
      sizeBytes: (json['size_bytes'] as num?)?.toInt() ?? 0,
      contentHash: json['content_hash']?.toString() ?? '',
      isBinary: json['is_binary'] == true,
      isGenerated: json['is_generated'] == true,
      isTest: json['is_test'] == true,
      lineCount: (json['line_count'] as num?)?.toInt() ?? 0,
      parserSupported: json['parser_supported'] == true,
    );
  }
}

// ─── File Node (Tree) ───────────────────────────────────
class FileNode {
  final String name;
  final String path;
  final bool isDirectory;
  final ProjectFile? file;
  final List<FileNode> children;

  FileNode({
    required this.name,
    required this.path,
    required this.isDirectory,
    this.file,
    List<FileNode>? children,
  }) : children = children ?? [];

  static List<FileNode> buildTree(List<ProjectFile> files) {
    final Map<String, dynamic> rootMap = {};
    for (final file in files) {
      final segments = file.path
          .replaceAll('\\', '/')
          .split('/')
          .where((s) => s.isNotEmpty)
          .toList();
      Map<String, dynamic> current = rootMap;
      for (int i = 0; i < segments.length; i++) {
        final segment = segments[i];
        final isLast = i == segments.length - 1;
        if (isLast) {
          current[segment] = file;
        } else {
          current[segment] = current[segment] ?? <String, dynamic>{};
          current = current[segment] as Map<String, dynamic>;
        }
      }
    }

    List<FileNode> convertMap(Map<String, dynamic> map, String currentPath) {
      final List<FileNode> nodes = [];
      for (final entry in map.entries) {
        final nodePath =
            currentPath.isEmpty ? entry.key : '$currentPath/${entry.key}';
        if (entry.value is ProjectFile) {
          nodes.add(FileNode(
            name: entry.key,
            path: nodePath,
            isDirectory: false,
            file: entry.value as ProjectFile,
          ));
        } else if (entry.value is Map<String, dynamic>) {
          final childNodes =
              convertMap(entry.value as Map<String, dynamic>, nodePath);
          nodes.add(FileNode(
            name: entry.key,
            path: nodePath,
            isDirectory: true,
            children: childNodes,
          ));
        }
      }
      nodes.sort((a, b) {
        if (a.isDirectory && !b.isDirectory) return -1;
        if (!a.isDirectory && b.isDirectory) return 1;
        return a.name.toLowerCase().compareTo(b.name.toLowerCase());
      });
      return nodes;
    }

    return convertMap(rootMap, '');
  }

  static List<FileNode> filterTree(List<FileNode> nodes, String query) {
    if (query.trim().isEmpty) return nodes;
    final lowerQuery = query.toLowerCase().trim();
    final List<FileNode> result = [];
    for (final node in nodes) {
      if (node.isDirectory) {
        final filteredChildren = filterTree(node.children, query);
        if (filteredChildren.isNotEmpty ||
            node.name.toLowerCase().contains(lowerQuery)) {
          result.add(FileNode(
            name: node.name,
            path: node.path,
            isDirectory: true,
            children: filteredChildren,
          ));
        }
      } else {
        if (node.name.toLowerCase().contains(lowerQuery) ||
            node.path.toLowerCase().contains(lowerQuery)) {
          result.add(node);
        }
      }
    }
    return result;
  }
}

// ─── Project Symbol ─────────────────────────────────────
class ProjectSymbol {
  final String id;
  final String fileId;
  final String name;
  final String symbolType;
  final String qualifiedName;
  final int startLine;
  final int endLine;
  final String? parentSymbolId;
  final String? filePath;
  final Map<String, dynamic> metadata;

  const ProjectSymbol({
    required this.id,
    required this.fileId,
    required this.name,
    required this.symbolType,
    required this.qualifiedName,
    required this.startLine,
    required this.endLine,
    this.parentSymbolId,
    this.filePath,
    this.metadata = const {},
  });

  factory ProjectSymbol.fromJson(Map<String, dynamic> json) {
    return ProjectSymbol(
      id: json['id']?.toString() ?? '',
      fileId: json['file_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      symbolType: json['symbol_type']?.toString() ?? 'OTHER',
      qualifiedName: json['qualified_name']?.toString() ?? '',
      startLine: (json['start_line'] as num?)?.toInt() ?? 0,
      endLine: (json['end_line'] as num?)?.toInt() ?? 0,
      parentSymbolId: json['parent_symbol_id']?.toString(),
      filePath: json['file_path']?.toString(),
      metadata: json['symbol_metadata'] is Map
          ? Map<String, dynamic>.from(json['symbol_metadata'])
          : const {},
    );
  }
}

// ─── Project Dependency ─────────────────────────────────
class ProjectDependency {
  final String id;
  final String sourceFileId;
  final String? targetFileId;
  final String? externalPackage;
  final String dependencyType;
  final int lineNumber;
  final String? sourcePath;
  final String? targetPath;

  const ProjectDependency({
    required this.id,
    required this.sourceFileId,
    this.targetFileId,
    this.externalPackage,
    required this.dependencyType,
    required this.lineNumber,
    this.sourcePath,
    this.targetPath,
  });

  factory ProjectDependency.fromJson(Map<String, dynamic> json) {
    return ProjectDependency(
      id: json['id']?.toString() ?? '',
      sourceFileId: json['source_file_id']?.toString() ?? '',
      targetFileId: json['target_file_id']?.toString(),
      externalPackage: json['external_package']?.toString(),
      dependencyType: json['dependency_type']?.toString() ?? 'IMPORT',
      lineNumber: (json['line_number'] as num?)?.toInt() ?? 0,
      sourcePath: json['source_path']?.toString(),
      targetPath: json['target_path']?.toString(),
    );
  }
}

// ─── Code Chunk ─────────────────────────────────────────
class CodeChunk {
  final String id;
  final String chunkType;
  final String name;
  final String path;
  final String content;
  final int startLine;
  final int endLine;

  const CodeChunk({
    required this.id,
    required this.chunkType,
    required this.name,
    required this.path,
    required this.content,
    required this.startLine,
    required this.endLine,
  });

  factory CodeChunk.fromJson(Map<String, dynamic> json) {
    return CodeChunk(
      id: json['id']?.toString() ?? '',
      chunkType: json['chunk_type']?.toString() ?? 'code',
      name: json['name']?.toString() ?? '',
      path: json['path']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      startLine: (json['start_line'] as num?)?.toInt() ?? 0,
      endLine: (json['end_line'] as num?)?.toInt() ?? 0,
    );
  }
}

// ─── File Detail ────────────────────────────────────────
class FileDetail {
  final ProjectFile file;
  final List<ProjectSymbol> symbols;
  final List<ProjectDependency> outgoingDependencies;
  final List<ProjectDependency> incomingReferences;
  final List<CodeChunk> chunks;
  final String? fullContent;

  const FileDetail({
    required this.file,
    this.symbols = const [],
    this.outgoingDependencies = const [],
    this.incomingReferences = const [],
    this.chunks = const [],
    this.fullContent,
  });

  factory FileDetail.fromJson(Map<String, dynamic> json) {
    final rawSymbols = json['symbols'];
    final rawOutDeps = json['outgoing_dependencies'];
    final rawInRefs = json['incoming_references'];
    final rawChunks = json['chunks'];

    return FileDetail(
      file: ProjectFile.fromJson(Map<String, dynamic>.from(json['file'])),
      symbols: rawSymbols is List
          ? rawSymbols
              .map((s) =>
                  ProjectSymbol.fromJson(Map<String, dynamic>.from(s)))
              .toList()
          : const [],
      outgoingDependencies: rawOutDeps is List
          ? rawOutDeps
              .map((d) =>
                  ProjectDependency.fromJson(Map<String, dynamic>.from(d)))
              .toList()
          : const [],
      incomingReferences: rawInRefs is List
          ? rawInRefs
              .map((d) =>
                  ProjectDependency.fromJson(Map<String, dynamic>.from(d)))
              .toList()
          : const [],
      chunks: rawChunks is List
          ? rawChunks
              .map(
                  (c) => CodeChunk.fromJson(Map<String, dynamic>.from(c)))
              .toList()
          : const [],
      fullContent: json['full_content']?.toString(),
    );
  }
}

// ─── Component Node (Architecture Graph) ────────────────
class ComponentNode {
  final String path;
  final String name;
  final String? fileId;
  final String? language;
  final List<ProjectDependency> incomingCallers;
  final List<ProjectDependency> outgoingDependencies;

  const ComponentNode({
    required this.path,
    required this.name,
    this.fileId,
    this.language,
    this.incomingCallers = const [],
    this.outgoingDependencies = const [],
  });

  String get id => path;

  String get layer {
    final lower = path.toLowerCase();
    if (lower.contains('/presentation/') ||
        lower.contains('/screens/') ||
        lower.contains('/widgets/') ||
        lower.contains('/ui/')) {
      return 'PRESENTATION';
    }
    if (lower.contains('/domain/') ||
        lower.contains('/models/') ||
        lower.contains('/entities/')) {
      return 'DOMAIN';
    }
    if (lower.contains('/data/') ||
        lower.contains('/services/') ||
        lower.contains('/repositories/') ||
        lower.contains('/network/')) {
      return 'DATA';
    }
    return 'CORE';
  }

  int get fileCount => 1;

  List<ProjectDependency> get incomingDependencies => incomingCallers;

  int get callerCount => incomingCallers.length;
  int get dependencyCount => outgoingDependencies.length;

  static List<ComponentNode> aggregateComponents({
    required List<ProjectDependency> dependencies,
    required List<ProjectFile> files,
  }) {
    final Map<String, ProjectFile> fileMap = {
      for (final f in files) f.path: f,
    };

    final Map<String, List<ProjectDependency>> incoming = {};
    final Map<String, List<ProjectDependency>> outgoing = {};
    final Set<String> allPaths = {};

    for (final f in files) {
      allPaths.add(f.path);
    }
    for (final dep in dependencies) {
      if (dep.sourcePath != null) {
        allPaths.add(dep.sourcePath!);
        outgoing.putIfAbsent(dep.sourcePath!, () => []).add(dep);
      }
      if (dep.targetPath != null) {
        allPaths.add(dep.targetPath!);
        incoming.putIfAbsent(dep.targetPath!, () => []).add(dep);
      }
    }

    final List<ComponentNode> nodes = [];
    for (final path in allPaths) {
      final file = fileMap[path];
      final name = path.split('/').last;
      nodes.add(ComponentNode(
        path: path,
        name: name,
        fileId: file?.id,
        language: file?.language ?? 'UNKNOWN',
        incomingCallers: incoming[path] ?? [],
        outgoingDependencies: outgoing[path] ?? [],
      ));
    }

    nodes.sort((a, b) {
      final cmp = b.callerCount.compareTo(a.callerCount);
      if (cmp != 0) return cmp;
      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });

    return nodes;
  }
}

// ─── Project Finding ────────────────────────────────────
class ProjectFinding {
  final String id;
  final String projectId;
  final String snapshotId;
  final String? discoveryRunId;
  final String category;
  final String title;
  final String description;
  final String whyItMatters;
  final String severity;
  final String confidence;
  final String status;
  final double score;
  final String recommendation;
  final List<Map<String, dynamic>> evidence;
  final List<String> relatedEntities;
  final DateTime createdAt;

  const ProjectFinding({
    required this.id,
    required this.projectId,
    required this.snapshotId,
    this.discoveryRunId,
    required this.category,
    required this.title,
    required this.description,
    required this.whyItMatters,
    required this.severity,
    required this.confidence,
    required this.status,
    required this.score,
    required this.recommendation,
    this.evidence = const [],
    this.relatedEntities = const [],
    required this.createdAt,
  });

  String? get filePath {
    if (relatedEntities.isNotEmpty) return relatedEntities.first;
    if (evidence.isNotEmpty) {
      final ep = evidence.first['file_path'] ?? evidence.first['filePath'];
      if (ep != null) return ep.toString();
    }
    return null;
  }

  int? get lineStart {
    if (evidence.isNotEmpty) {
      final l = evidence.first['line_start'] ?? evidence.first['lineStart'] ?? evidence.first['line'];
      if (l is num) return l.toInt();
    }
    return null;
  }

  int? get lineEnd {
    if (evidence.isNotEmpty) {
      final l = evidence.first['line_end'] ?? evidence.first['lineEnd'];
      if (l is num) return l.toInt();
    }
    return null;
  }

  factory ProjectFinding.fromJson(Map<String, dynamic> json) {
    final rawEvidence = json['evidence'];
    final List<Map<String, dynamic>> parsedEvidence = [];
    if (rawEvidence is List) {
      for (final item in rawEvidence) {
        if (item is Map) {
          parsedEvidence.add(Map<String, dynamic>.from(item));
        }
      }
    }

    final rawEntities = json['related_entities'];
    final List<String> parsedEntities = [];
    if (rawEntities is List) {
      for (final item in rawEntities) {
        if (item != null) parsedEntities.add(item.toString());
      }
    }

    return ProjectFinding(
      id: json['id']?.toString() ?? '',
      projectId: json['project_id']?.toString() ?? '',
      snapshotId: json['snapshot_id']?.toString() ?? '',
      discoveryRunId: json['discovery_run_id']?.toString(),
      category: json['category']?.toString() ?? 'ARCHITECTURE',
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      whyItMatters: json['why_it_matters']?.toString() ?? '',
      severity: json['severity']?.toString() ?? 'MEDIUM',
      confidence: json['confidence']?.toString() ?? 'HIGH',
      status: json['status']?.toString() ?? 'OPEN',
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      recommendation: json['recommendation']?.toString() ?? '',
      evidence: parsedEvidence,
      relatedEntities: parsedEntities,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ??
          DateTime.now(),
    );
  }
}

// ─── Project Knowledge ──────────────────────────────────
class ProjectKnowledge {
  final String id;
  final String projectId;
  final String? createdBy;
  final String? creatorEmail;
  final String category;
  final String title;
  final String content;
  final String status;
  final String sourceType;
  final String? relatedFilePath;
  final String? relatedSymbol;
  final String? relatedFindingId;
  final Map<String, dynamic> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  const ProjectKnowledge({
    required this.id,
    required this.projectId,
    this.createdBy,
    this.creatorEmail,
    required this.category,
    required this.title,
    required this.content,
    required this.status,
    this.sourceType = 'CUSTOMER',
    this.relatedFilePath,
    this.relatedSymbol,
    this.relatedFindingId,
    this.metadata = const {},
    required this.createdAt,
    required this.updatedAt,
  });

  String get author => createdBy?.isNotEmpty == true
      ? createdBy!
      : (creatorEmail?.isNotEmpty == true ? creatorEmail! : 'Automated');

  factory ProjectKnowledge.fromJson(Map<String, dynamic> json) {
    return ProjectKnowledge(
      id: json['id'] as String? ?? '',
      projectId: json['project_id'] as String? ?? '',
      createdBy: json['created_by'] as String?,
      creatorEmail: json['creator_email'] as String?,
      category: json['category'] as String? ?? 'OTHER',
      title: json['title'] as String? ?? '',
      content: json['content'] as String? ?? '',
      status: json['status'] as String? ?? 'ACTIVE',
      sourceType: json['source_type'] as String? ?? 'CUSTOMER',
      relatedFilePath: json['related_file_path'] as String?,
      relatedSymbol: json['related_symbol'] as String?,
      relatedFindingId: json['related_finding_id'] as String?,
      metadata: json['knowledge_metadata'] is Map
          ? Map<String, dynamic>.from(json['knowledge_metadata'] as Map)
          : {},
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

// ─── Discovery Summary ──────────────────────────────────
class DiscoveryRunInfo {
  final String id;
  final String status;
  final int progress;
  final int findingsCount;
  final String? errorMessage;
  final DateTime startedAt;
  final DateTime? completedAt;

  const DiscoveryRunInfo({
    required this.id,
    required this.status,
    required this.progress,
    required this.findingsCount,
    this.errorMessage,
    required this.startedAt,
    this.completedAt,
  });

  factory DiscoveryRunInfo.fromJson(Map<String, dynamic> json) {
    return DiscoveryRunInfo(
      id: json['id']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PENDING',
      progress: (json['progress'] as num?)?.toInt() ?? 0,
      findingsCount: (json['findings_count'] as num?)?.toInt() ?? 0,
      errorMessage: json['error_message']?.toString(),
      startedAt:
          DateTime.tryParse(json['started_at']?.toString() ?? '') ??
              DateTime.now(),
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'].toString())
          : null,
    );
  }
}

class DiscoverySummary {
  final int totalFindings;
  final int criticalCount;
  final int highCount;
  final int mediumCount;
  final int lowCount;
  final DiscoveryRunInfo? latestRun;

  const DiscoverySummary({
    this.totalFindings = 0,
    this.criticalCount = 0,
    this.highCount = 0,
    this.mediumCount = 0,
    this.lowCount = 0,
    this.latestRun,
  });

  factory DiscoverySummary.fromJson(Map<String, dynamic> json) {
    return DiscoverySummary(
      totalFindings: (json['total_findings'] as num?)?.toInt() ?? 0,
      criticalCount: (json['critical_count'] as num?)?.toInt() ?? 0,
      highCount: (json['high_count'] as num?)?.toInt() ?? 0,
      mediumCount: (json['medium_count'] as num?)?.toInt() ?? 0,
      lowCount: (json['low_count'] as num?)?.toInt() ?? 0,
      latestRun: json['latest_run'] != null
          ? DiscoveryRunInfo.fromJson(
              Map<String, dynamic>.from(json['latest_run']))
          : null,
    );
  }
}

// ─── Repository Context ─────────────────────────────────
class ProjectContextMetrics {
  final int totalFiles;
  final int languagesCount;
  final int symbolsCount;
  final int dependenciesCount;
  final int totalSloc;
  final int totalFindings;
  final Map<String, int> languageDistribution;

  const ProjectContextMetrics({
    this.totalFiles = 0,
    this.totalSloc = 0,
    this.languagesCount = 0,
    this.symbolsCount = 0,
    this.dependenciesCount = 0,
    this.totalFindings = 0,
    this.languageDistribution = const {},
  });

  int get totalSymbols => symbolsCount;
  int get totalDependencies => dependenciesCount;

  factory ProjectContextMetrics.fromJson(Map<String, dynamic> json) {
    final rawDist = json['language_distribution'];
    final Map<String, int> dist = {};
    if (rawDist is Map) {
      rawDist.forEach((key, value) {
        dist[key.toString()] = (value as num?)?.toInt() ?? 0;
      });
    }
    return ProjectContextMetrics(
      totalFiles: (json['total_files'] as num?)?.toInt() ?? 0,
      totalSloc: (json['total_sloc'] as num?)?.toInt() ??
          ((json['total_files'] as num?)?.toInt() ?? 0) * 85,
      languagesCount: (json['languages_count'] as num?)?.toInt() ?? 0,
      symbolsCount: (json['symbols_count'] as num?)?.toInt() ?? 0,
      dependenciesCount:
          (json['dependencies_count'] as num?)?.toInt() ?? 0,
      totalFindings: (json['total_findings'] as num?)?.toInt() ?? 0,
      languageDistribution: dist,
    );
  }
}

class RepositoryInfo {
  final String id;
  final String name;
  final String fullName;
  final String? defaultBranch;
  final String? htmlUrl;

  const RepositoryInfo({
    required this.id,
    required this.name,
    required this.fullName,
    this.defaultBranch,
    this.htmlUrl,
  });

  factory RepositoryInfo.fromJson(Map<String, dynamic> json) {
    return RepositoryInfo(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      defaultBranch: json['default_branch']?.toString(),
      htmlUrl: json['html_url']?.toString(),
    );
  }
}

class ActiveSnapshot {
  final String id;
  final String repositoryId;
  final String commitHash;
  final String branch;
  final String status;
  final int totalFiles;
  final int totalBytes;
  final DateTime? createdAt;

  const ActiveSnapshot({
    required this.id,
    required this.repositoryId,
    required this.commitHash,
    required this.branch,
    required this.status,
    required this.totalFiles,
    required this.totalBytes,
    this.createdAt,
  });

  factory ActiveSnapshot.fromJson(Map<String, dynamic> json) {
    return ActiveSnapshot(
      id: json['id']?.toString() ?? '',
      repositoryId: json['repository_id']?.toString() ?? '',
      commitHash: json['commit_hash']?.toString() ?? '',
      branch: json['branch']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PENDING',
      totalFiles: (json['total_files'] as num?)?.toInt() ?? 0,
      totalBytes: (json['total_bytes'] as num?)?.toInt() ?? 0,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString())
          : null,
    );
  }
}

class ProjectRepositoryContext {
  final RepositoryInfo? repository;
  final ActiveSnapshot? activeSnapshot;
  final ProjectContextMetrics metrics;

  const ProjectRepositoryContext({
    this.repository,
    this.activeSnapshot,
    this.metrics = const ProjectContextMetrics(),
  });

  factory ProjectRepositoryContext.fromJson(Map<String, dynamic> json) {
    return ProjectRepositoryContext(
      repository: json['repository'] != null
          ? RepositoryInfo.fromJson(
              Map<String, dynamic>.from(json['repository']))
          : null,
      activeSnapshot: json['active_snapshot'] != null
          ? ActiveSnapshot.fromJson(
              Map<String, dynamic>.from(json['active_snapshot']))
          : null,
      metrics: json['metrics'] != null
          ? ProjectContextMetrics.fromJson(
              Map<String, dynamic>.from(json['metrics']))
          : const ProjectContextMetrics(),
    );
  }
}

// ─── Grounded Answer (Ask/Chat) ─────────────────────────
class GroundedAnswer {
  final String conversationId;
  final String messageId;
  final String role;
  final String content;
  final List<GroundedEvidence> evidence;
  final List<String> relatedEntities;
  final String confidence;
  final DateTime createdAt;

  const GroundedAnswer({
    required this.conversationId,
    required this.messageId,
    required this.role,
    required this.content,
    required this.evidence,
    required this.relatedEntities,
    required this.confidence,
    required this.createdAt,
  });

  factory GroundedAnswer.fromJson(Map<String, dynamic> json) {
    final evidenceList = <GroundedEvidence>[];
    if (json['evidence'] is List) {
      for (final item in json['evidence'] as List) {
        if (item is Map) {
          evidenceList
              .add(GroundedEvidence.fromJson(Map<String, dynamic>.from(item)));
        }
      }
    }

    final entities = <String>[];
    if (json['related_entities'] is List) {
      for (final e in json['related_entities'] as List) {
        if (e is String) entities.add(e);
      }
    }

    return GroundedAnswer(
      conversationId: json['conversation_id'] as String? ?? '',
      messageId: json['message_id'] as String? ?? '',
      role: json['role'] as String? ?? 'assistant',
      content: json['content'] as String? ?? '',
      evidence: evidenceList,
      relatedEntities: entities,
      confidence: json['confidence'] as String? ?? 'HIGH',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class GroundedEvidence {
  final String type;
  final String file;
  final String? symbol;
  final String? lines;
  final double relevance;
  final String? snippet;

  const GroundedEvidence({
    required this.type,
    required this.file,
    this.symbol,
    this.lines,
    required this.relevance,
    this.snippet,
  });

  factory GroundedEvidence.fromJson(Map<String, dynamic> json) {
    return GroundedEvidence(
      type: json['type'] as String? ?? 'file',
      file: json['file'] as String? ?? '',
      symbol: json['symbol'] as String?,
      lines: json['lines'] as String?,
      relevance: (json['relevance'] as num?)?.toDouble() ?? 0.0,
      snippet: json['snippet'] as String?,
    );
  }
}

// ─── Conversation Thread ────────────────────────────────
class ConversationThread {
  final String id;
  final String projectId;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;
  final int messageCount;

  const ConversationThread({
    required this.id,
    required this.projectId,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
    this.messageCount = 0,
  });

  factory ConversationThread.fromJson(Map<String, dynamic> json) {
    return ConversationThread(
      id: json['id'] as String? ?? '',
      projectId: json['project_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      messageCount: json['message_count'] as int? ?? 0,
    );
  }
}

// ─── Project Member (Workspace RBAC) ────────────────────
enum WorkspaceRole { admin, member, viewer }

class ProjectMember {
  final String id;
  final String projectId;
  final String userId;
  final String role; // ADMIN, MEMBER, VIEWER
  final DateTime createdAt;
  final String? userName;
  final String? userEmail;

  const ProjectMember({
    required this.id,
    required this.projectId,
    required this.userId,
    required this.role,
    required this.createdAt,
    this.userName,
    this.userEmail,
  });

  bool get isAdmin => role.toUpperCase() == 'ADMIN';
  bool get isMember => role.toUpperCase() == 'MEMBER';
  bool get isViewer => role.toUpperCase() == 'VIEWER';

  factory ProjectMember.fromJson(Map<String, dynamic> json) {
    return ProjectMember(
      id: json['id']?.toString() ?? '',
      projectId: json['project_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      role: json['role']?.toString().toUpperCase() ?? 'MEMBER',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      userName: json['user_name']?.toString(),
      userEmail: json['user_email']?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'project_id': projectId,
        'user_id': userId,
        'role': role,
        'created_at': createdAt.toIso8601String(),
        if (userName != null) 'user_name': userName,
        if (userEmail != null) 'user_email': userEmail,
      };
}

// ─── Data Plane Status (Phase 2 Isolation) ───────────────
class ProjectDataPlaneStatus {
  final bool exists;
  final String? containerId;
  final String status;
  final int? port;
  final bool isRunning;
  final String? url;

  const ProjectDataPlaneStatus({
    required this.exists,
    this.containerId,
    required this.status,
    this.port,
    required this.isRunning,
    this.url,
  });

  factory ProjectDataPlaneStatus.fromJson(Map<String, dynamic> json) {
    final assignedPort = json['port'] is num ? (json['port'] as num).toInt() : null;
    return ProjectDataPlaneStatus(
      exists: json['exists'] == true,
      containerId: json['container_id']?.toString(),
      status: json['status']?.toString() ?? 'unknown',
      port: assignedPort,
      isRunning: json['is_running'] == true,
      url: assignedPort != null ? 'http://localhost:$assignedPort' : null,
    );
  }
}

