import 'package:flutter/material.dart';

class UserModel {
  final String name;
  final String org;
  final String email;
  final String role;
  final String? id;

  const UserModel({
    required this.name,
    required this.org,
    this.email = 'lead@acme.com',
    this.role = 'Admin / Pilot Lead',
    this.id,
  });

  bool get isManager {
    final lowerRole = role.toLowerCase();
    final lowerEmail = email.toLowerCase();
    return lowerRole.contains('manager') ||
        lowerRole.contains('admin') ||
        lowerRole.contains('lead') ||
        lowerRole.contains('owner') ||
        lowerEmail.contains('manager') ||
        lowerEmail.contains('lead') ||
        lowerEmail.contains('admin');
  }

  bool get isEmployee => !isManager;
}

class NotificationItem {
  final String id;
  final String type; // success, info, warning, error
  final String title;
  final String body;
  final String time;
  bool read;

  NotificationItem({
    required this.id,
    required this.type,
    required this.title,
    required this.body,
    required this.time,
    required this.read,
  });
}

class ProjectItem {
  final String id;
  final String name;
  final String upsStatus; // active, offline, READY, CREATED
  final String ingestionStatus; // live, stale, ingesting, ready
  final String lastIngestion;
  final double fpr;
  final int days;
  final String? organizationId;
  final String? slug;
  final String? description;
  final int? port;
  final String? role;
  final String? repositoryName;

  const ProjectItem({
    required this.id,
    required this.name,
    required this.upsStatus,
    required this.ingestionStatus,
    required this.lastIngestion,
    required this.fpr,
    required this.days,
    this.organizationId,
    this.slug,
    this.description,
    this.port,
    this.role,
    this.repositoryName,
  });
}

class ActivityItem {
  final String id;
  final String icon;
  final String text;
  final String time;
  final Color color;

  const ActivityItem({
    required this.id,
    required this.icon,
    required this.text,
    required this.time,
    required this.color,
  });
}

class RecentChat {
  final dynamic id;
  String title;
  final String ago;
  final String time;
  final int messageCount;
  bool isPinned;
  String? projectId;

  RecentChat({
    required this.id,
    required this.title,
    required this.ago,
    required this.time,
    this.messageCount = 0,
    this.isPinned = false,
    this.projectId,
  });

  String get idString => id.toString();
}

class ArchivedChat {
  final dynamic id;
  final String title;
  final String date;
  final int messages;

  const ArchivedChat({
    required this.id,
    required this.title,
    required this.date,
    required this.messages,
  });

  String get idString => id.toString();
}

class EvidenceItem {
  final String type;
  final String file;
  final String? lines;
  final double relevance;
  final String? snippet;
  final String? symbol;

  const EvidenceItem({
    required this.type,
    required this.file,
    this.lines,
    required this.relevance,
    this.snippet,
    this.symbol,
  });

  factory EvidenceItem.fromJson(Map<String, dynamic> json) {
    return EvidenceItem(
      type: json['type']?.toString() ?? 'symbol',
      file: json['file']?.toString() ?? '',
      lines: json['lines']?.toString(),
      relevance: (json['relevance'] as num?)?.toDouble() ?? 1.0,
      snippet: json['snippet']?.toString(),
      symbol: json['symbol']?.toString(),
    );
  }
}

class SpecHistoryItem {
  final String id;
  final String query;
  final String timestamp;
  final String ago;
  final String isoDate;
  final String queryType; // cold, warm, hot, COUPLING, etc.
  final String confidence; // confirmed, uncertain, insufficient, HIGH, etc.
  final double score;
  final double? fprDelta;
  final bool hasBDD;
  final String? category;
  final String? description;
  final String? whyItMatters;
  final String? recommendation;
  final String? severity;
  final List<EvidenceItem> evidence;

  const SpecHistoryItem({
    required this.id,
    required this.query,
    required this.timestamp,
    required this.ago,
    required this.isoDate,
    required this.queryType,
    required this.confidence,
    required this.score,
    this.fprDelta,
    required this.hasBDD,
    this.category,
    this.description,
    this.whyItMatters,
    this.recommendation,
    this.severity,
    this.evidence = const [],
  });
}

class ResponseSegment {
  final String text;
  final String? tag; // CONFIRMED, INFERRED
  final String? note;

  const ResponseSegment({
    required this.text,
    this.tag,
    this.note,
  });
}

class ScoreComponent {
  final String label;
  final double score;

  const ScoreComponent({required this.label, required this.score});
}

class ReasoningModel {
  final double compositeScore;
  final List<ScoreComponent> components;
  final List<String> routingPath;
  final List<String> ontologyEdges;
  final List<String> citations;
  final List<EvidenceItem> evidence;
  final Map<String, dynamic>? debugSignals;

  const ReasoningModel({
    required this.compositeScore,
    required this.components,
    required this.routingPath,
    required this.ontologyEdges,
    required this.citations,
    this.evidence = const [],
    this.debugSignals,
  });
}

class TestCase {
  final int id;
  final String desc;

  const TestCase({required this.id, required this.desc});
}

class RiskItem {
  final String tag;
  final String text;

  const RiskItem({required this.tag, required this.text});
}

class BddSpec {
  final String given;
  final String when;
  final String then;
  final String kpi;
  final String kpiTag;
  final String? kpiNote;
  final List<TestCase> testCases;
  final List<RiskItem> risks;

  const BddSpec({
    required this.given,
    required this.when,
    required this.then,
    required this.kpi,
    required this.kpiTag,
    this.kpiNote,
    required this.testCases,
    required this.risks,
  });
}

class QueryResponseData {
  final List<ResponseSegment> segments;
  final String meta;
  final String queryType;
  final String confidence;
  final ReasoningModel? reasoning;
  final BddSpec? bdd;
  final String? conversationId;

  const QueryResponseData({
    required this.segments,
    required this.meta,
    required this.queryType,
    required this.confidence,
    this.reasoning,
    this.bdd,
    this.conversationId,
  });
}

enum MessageKind { query, generating, response }

class ChatMessage {
  final String id;
  final MessageKind kind;
  final String? text;
  final String? phase; // ingesting, scoring, deepScoring
  final QueryResponseData? data;

  const ChatMessage({
    required this.id,
    required this.kind,
    this.text,
    this.phase,
    this.data,
  });

  ChatMessage copyWith({
    String? id,
    MessageKind? kind,
    String? text,
    String? phase,
    QueryResponseData? data,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      kind: kind ?? this.kind,
      text: text ?? this.text,
      phase: phase ?? this.phase,
      data: data ?? this.data,
    );
  }
}

class OntologyNode {
  final int id;
  final double cx;
  final double cy;
  final String label;
  final String type; // Service, Decision, Commit, Ticket, Thread, Person, Symbol, File, Dependency
  final String? subtitle;

  const OntologyNode({
    required this.id,
    required this.cx,
    required this.cy,
    required this.label,
    required this.type,
    this.subtitle,
  });
}

class HeroCardItem {
  final String title;
  final String tag;
  final IconData icon;

  const HeroCardItem({
    required this.title,
    required this.tag,
    required this.icon,
  });
}
