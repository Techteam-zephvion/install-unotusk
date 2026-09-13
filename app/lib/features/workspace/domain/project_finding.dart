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
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
    );
  }
}
