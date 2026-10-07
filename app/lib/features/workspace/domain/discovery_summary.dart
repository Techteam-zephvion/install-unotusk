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
      startedAt: DateTime.tryParse(json['started_at']?.toString() ?? '') ?? DateTime.now(),
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
          ? DiscoveryRunInfo.fromJson(Map<String, dynamic>.from(json['latest_run']))
          : null,
    );
  }
}
