class ProjectContextMetrics {
  final int totalFiles;
  final int languagesCount;
  final int symbolsCount;
  final int dependenciesCount;
  final Map<String, int> languageDistribution;

  const ProjectContextMetrics({
    this.totalFiles = 0,
    this.languagesCount = 0,
    this.symbolsCount = 0,
    this.dependenciesCount = 0,
    this.languageDistribution = const {},
  });

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
      languagesCount: (json['languages_count'] as num?)?.toInt() ?? 0,
      symbolsCount: (json['symbols_count'] as num?)?.toInt() ?? 0,
      dependenciesCount: (json['dependencies_count'] as num?)?.toInt() ?? 0,
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
    DateTime? parsedCreated;
    if (json['created_at'] != null) {
      parsedCreated = DateTime.tryParse(json['created_at'].toString());
    }

    return ActiveSnapshot(
      id: json['id']?.toString() ?? '',
      repositoryId: json['repository_id']?.toString() ?? '',
      commitHash: json['commit_hash']?.toString() ?? '',
      branch: json['branch']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PENDING',
      totalFiles: (json['total_files'] as num?)?.toInt() ?? 0,
      totalBytes: (json['total_bytes'] as num?)?.toInt() ?? 0,
      createdAt: parsedCreated,
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
          ? RepositoryInfo.fromJson(Map<String, dynamic>.from(json['repository']))
          : null,
      activeSnapshot: json['active_snapshot'] != null
          ? ActiveSnapshot.fromJson(Map<String, dynamic>.from(json['active_snapshot']))
          : null,
      metrics: json['metrics'] != null
          ? ProjectContextMetrics.fromJson(Map<String, dynamic>.from(json['metrics']))
          : const ProjectContextMetrics(),
    );
  }
}
