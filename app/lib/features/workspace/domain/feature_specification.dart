import 'grounded_answer.dart';
import '../presentation/widgets/bdd_contract_card.dart';

class BDDScenario {
  final int id;
  final String title;
  final String given;
  final String when;
  final String then;
  final List<String> citedFiles;
  final List<String> citedSymbols;

  const BDDScenario({
    required this.id,
    required this.title,
    required this.given,
    required this.when,
    required this.then,
    this.citedFiles = const [],
    this.citedSymbols = const [],
  });

  factory BDDScenario.fromJson(Map<String, dynamic> json) {
    return BDDScenario(
      id: json['id'] as int? ?? 1,
      title: json['title'] as String? ?? 'Scenario',
      given: json['given'] as String? ?? '',
      when: json['when'] as String? ?? '',
      then: json['then'] as String? ?? '',
      citedFiles: (json['cited_files'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      citedSymbols: (json['cited_symbols'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'given': given,
      'when': when,
      'then': then,
      'cited_files': citedFiles,
      'cited_symbols': citedSymbols,
    };
  }
}

class FeatureSpecification {
  final String projectId;
  final String featureName;
  final String intent;
  final String confidence;
  final List<String> confirmedCodeFacts;
  final List<String> inferredRequirements;
  final List<BDDScenario> scenarios;
  final List<EvidenceItem> evidence;
  final List<String> citedFiles;
  final List<String> citedSymbols;
  final bool hasSupersededPrecursors;
  final String? warning;
  final Map<String, dynamic> debugSignals;
  final DateTime createdAt;

  const FeatureSpecification({
    required this.projectId,
    required this.featureName,
    required this.intent,
    required this.confidence,
    this.confirmedCodeFacts = const [],
    this.inferredRequirements = const [],
    this.scenarios = const [],
    this.evidence = const [],
    this.citedFiles = const [],
    this.citedSymbols = const [],
    this.hasSupersededPrecursors = false,
    this.warning,
    this.debugSignals = const {},
    required this.createdAt,
  });

  factory FeatureSpecification.fromJson(Map<String, dynamic> json) {
    final scenariosList = <BDDScenario>[];
    if (json['scenarios'] is List) {
      for (final s in json['scenarios'] as List) {
        if (s is Map) {
          scenariosList.add(BDDScenario.fromJson(Map<String, dynamic>.from(s)));
        }
      }
    }

    final evidenceList = <EvidenceItem>[];
    if (json['evidence'] is List) {
      for (final e in json['evidence'] as List) {
        if (e is Map) {
          evidenceList.add(EvidenceItem.fromJson(Map<String, dynamic>.from(e)));
        }
      }
    }

    return FeatureSpecification(
      projectId: json['project_id']?.toString() ?? '',
      featureName: json['feature_name'] as String? ?? 'Feature Specification',
      intent: json['intent'] as String? ?? '',
      confidence: json['confidence'] as String? ?? 'HIGH',
      confirmedCodeFacts: (json['confirmed_code_facts'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      inferredRequirements: (json['inferred_requirements'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      scenarios: scenariosList,
      evidence: evidenceList,
      citedFiles: (json['cited_files'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      citedSymbols: (json['cited_symbols'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? const [],
      hasSupersededPrecursors: json['has_superseded_precursors'] as bool? ?? false,
      warning: json['warning'] as String?,
      debugSignals: json['debug_signals'] is Map ? Map<String, dynamic>.from(json['debug_signals'] as Map) : const {},
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now() : DateTime.now(),
    );
  }

  BDDContractData toBDDContractData({String? tier}) {
    final primaryGiven = scenarios.isNotEmpty ? scenarios.first.given : 'Codebase context for $featureName';
    final primaryWhen = scenarios.isNotEmpty ? scenarios.first.when : intent;
    final primaryThen = scenarios.isNotEmpty ? scenarios.first.then : 'Grounded requirements are satisfied';

    final testCases = scenarios.map((s) => BDDTestCase(
      id: s.id,
      desc: '${s.title}: Given ${s.given}, When ${s.when}, Then ${s.then}',
    )).toList();

    final risks = <BDDRiskItem>[];
    for (final fact in confirmedCodeFacts) {
      risks.add(BDDRiskItem(tag: 'CONFIRMED', text: fact));
    }
    for (final req in inferredRequirements) {
      risks.add(BDDRiskItem(tag: 'INFERRED', text: req));
    }
    if (warning != null && warning!.isNotEmpty) {
      risks.add(BDDRiskItem(tag: 'INFERRED', text: 'Diagnostic Warning: $warning'));
    }

    final kpiTag = confidence == 'HIGH' ? 'CONFIRMED' : 'INFERRED';
    final kpiNote = warning ?? (citedFiles.isNotEmpty ? 'Cited: ${citedFiles.join(", ")}' : null);

    return BDDContractData(
      given: primaryGiven,
      when: primaryWhen,
      then: primaryThen,
      kpi: 'Grounding confidence: $confidence',
      kpiTag: kpiTag,
      kpiNote: kpiNote,
      testCases: testCases.isNotEmpty ? testCases : [
        BDDTestCase(id: 1, desc: '$featureName acceptance criterion')
      ],
      risks: risks.isNotEmpty ? risks : [
        BDDRiskItem(tag: kpiTag, text: intent)
      ],
      tier: tier ?? 'WARM TIER',
      confidence: confidence,
      warning: warning,
      featureName: featureName,
      citedFiles: citedFiles,
      citedSymbols: citedSymbols,
    );
  }
}
