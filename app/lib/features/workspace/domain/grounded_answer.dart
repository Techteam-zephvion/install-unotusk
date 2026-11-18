class EvidenceItem {
  final String type;
  final String file;
  final String? symbol;
  final String? lines;
  final double relevance;
  final String? snippet;
  final String? commitSha;
  final String? relationshipPath;
  final int? relationshipHop;
  final String? relationshipType;
  final String? retrievalReason;

  const EvidenceItem({
    required this.type,
    required this.file,
    this.symbol,
    this.lines,
    required this.relevance,
    this.snippet,
    this.commitSha,
    this.relationshipPath,
    this.relationshipHop,
    this.relationshipType,
    this.retrievalReason,
  });

  factory EvidenceItem.fromJson(Map<String, dynamic> json) {
    return EvidenceItem(
      type: json['type'] as String? ?? 'file',
      file: json['file'] as String? ?? '',
      symbol: json['symbol'] as String?,
      lines: json['lines'] as String?,
      relevance: (json['relevance'] as num?)?.toDouble() ?? 0.0,
      snippet: json['snippet'] as String?,
      commitSha: json['commit_sha'] as String?,
      relationshipPath: json['relationship_path'] as String?,
      relationshipHop: (json['relationship_hop'] as num?)?.toInt(),
      relationshipType: json['relationship_type'] as String?,
      retrievalReason: json['retrieval_reason'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'file': file,
      'symbol': symbol,
      'lines': lines,
      'relevance': relevance,
      'snippet': snippet,
      if (commitSha != null) 'commit_sha': commitSha,
      if (relationshipPath != null) 'relationship_path': relationshipPath,
      if (relationshipHop != null) 'relationship_hop': relationshipHop,
      if (relationshipType != null) 'relationship_type': relationshipType,
      if (retrievalReason != null) 'retrieval_reason': retrievalReason,
    };
  }
}

class GroundedAnswer {
  final String conversationId;
  final String messageId;
  final String role;
  final String content;
  final List<EvidenceItem> evidence;
  final List<String> relatedEntities;
  final String confidence;
  final DateTime createdAt;
  final Map<String, dynamic>? debugSignals;

  const GroundedAnswer({
    required this.conversationId,
    required this.messageId,
    required this.role,
    required this.content,
    required this.evidence,
    required this.relatedEntities,
    required this.confidence,
    required this.createdAt,
    this.debugSignals,
  });

  String get answer => content;
  List<EvidenceItem> get citations => evidence;
  String get confidenceLevel => confidence;
  String? get reasoning => null;

  String? get routingDecision =>
      debugSignals?['star_rag_routing_decision'] as String? ??
      debugSignals?['routing_decision'] as String?;
  bool get isStarRag =>
      debugSignals?['structure_aware_star_rag_used'] == true ||
      debugSignals?['star_rag_used'] == true;
  double? get topScore => (debugSignals?['top_score'] as num?)?.toDouble();
  int? get candidatesCount => (debugSignals?['candidates_retrieved'] as num?)?.toInt();
  int? get expandedCount => (debugSignals?['candidates_expanded'] as num?)?.toInt();

  factory GroundedAnswer.fromJson(Map<String, dynamic> json) {
    final evidenceList = <EvidenceItem>[];
    if (json['evidence'] is List) {
      for (final item in json['evidence'] as List) {
        if (item is Map) {
          evidenceList.add(EvidenceItem.fromJson(Map<String, dynamic>.from(item)));
        }
      }
    }

    final entities = <String>[];
    if (json['related_entities'] is List) {
      for (final e in json['related_entities'] as List) {
        if (e is String) entities.add(e);
      }
    }

    Map<String, dynamic>? debugSignalsMap;
    if (json['debug_signals'] is Map) {
      debugSignalsMap = Map<String, dynamic>.from(json['debug_signals'] as Map);
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
      debugSignals: debugSignalsMap,
    );
  }
}

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
