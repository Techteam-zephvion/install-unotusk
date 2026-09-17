class EvidenceItem {
  final String type;
  final String file;
  final String? symbol;
  final String? lines;
  final double relevance;
  final String? snippet;

  const EvidenceItem({
    required this.type,
    required this.file,
    this.symbol,
    this.lines,
    required this.relevance,
    this.snippet,
  });

  factory EvidenceItem.fromJson(Map<String, dynamic> json) {
    return EvidenceItem(
      type: json['type'] as String? ?? 'file',
      file: json['file'] as String? ?? '',
      symbol: json['symbol'] as String?,
      lines: json['lines'] as String?,
      relevance: (json['relevance'] as num?)?.toDouble() ?? 0.0,
      snippet: json['snippet'] as String?,
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

  String get answer => content;
  List<EvidenceItem> get citations => evidence;
  String get confidenceLevel => confidence;
  String? get reasoning => null;

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
