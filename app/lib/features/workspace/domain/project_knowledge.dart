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
  final String? sourceReferenceType;
  final String? sourceReferenceId;
  final String? relatedFilePath;
  final String? relatedSymbol;
  final String? relatedFindingId;
  final String? relatedEntityType;
  final String? relatedEntityId;
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
    this.sourceReferenceType,
    this.sourceReferenceId,
    this.relatedFilePath,
    this.relatedSymbol,
    this.relatedFindingId,
    this.relatedEntityType,
    this.relatedEntityId,
    this.metadata = const {},
    required this.createdAt,
    required this.updatedAt,
  });

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
      sourceReferenceType: json['source_reference_type'] as String?,
      sourceReferenceId: json['source_reference_id'] as String?,
      relatedFilePath: json['related_file_path'] as String?,
      relatedSymbol: json['related_symbol'] as String?,
      relatedFindingId: json['related_finding_id'] as String?,
      relatedEntityType: json['related_entity_type'] as String?,
      relatedEntityId: json['related_entity_id'] as String?,
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

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'project_id': projectId,
      'created_by': createdBy,
      'creator_email': creatorEmail,
      'category': category,
      'title': title,
      'content': content,
      'status': status,
      'source_type': sourceType,
      'source_reference_type': sourceReferenceType,
      'source_reference_id': sourceReferenceId,
      'related_file_path': relatedFilePath,
      'related_symbol': relatedSymbol,
      'related_finding_id': relatedFindingId,
      'related_entity_type': relatedEntityType,
      'related_entity_id': relatedEntityId,
      'knowledge_metadata': metadata,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
