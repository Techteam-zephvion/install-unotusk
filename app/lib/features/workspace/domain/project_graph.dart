class ProjectGraphNode {
  final String id;
  final String type; // SERVICE, REPOSITORY, FILE, CLASS, FUNCTION, METHOD, EXTERNAL_PACKAGE, etc.
  final String label;
  final Map<String, dynamic> metadata;

  const ProjectGraphNode({
    required this.id,
    required this.type,
    required this.label,
    this.metadata = const {},
  });

  factory ProjectGraphNode.fromJson(Map<String, dynamic> json) {
    return ProjectGraphNode(
      id: json['id'] as String? ?? '',
      type: json['type'] as String? ?? 'UNKNOWN',
      label: json['label'] as String? ?? '',
      metadata: Map<String, dynamic>.from(json['metadata'] as Map? ?? {}),
    );
  }
}

class ProjectGraphEdge {
  final String id;
  final String source;
  final String target;
  final String type; // CONTAINS, DEFINES, DEPENDS_ON
  final Map<String, dynamic> metadata;

  const ProjectGraphEdge({
    required this.id,
    required this.source,
    required this.target,
    required this.type,
    this.metadata = const {},
  });

  factory ProjectGraphEdge.fromJson(Map<String, dynamic> json) {
    return ProjectGraphEdge(
      id: json['id'] as String? ?? '',
      source: json['source'] as String? ?? '',
      target: json['target'] as String? ?? '',
      type: json['type'] as String? ?? 'DEPENDS_ON',
      metadata: Map<String, dynamic>.from(json['metadata'] as Map? ?? {}),
    );
  }
}

class ProjectGraph {
  final List<ProjectGraphNode> nodes;
  final List<ProjectGraphEdge> edges;
  final String? snapshotId;
  final int totalNodes;
  final int totalEdges;

  const ProjectGraph({
    this.nodes = const [],
    this.edges = const [],
    this.snapshotId,
    this.totalNodes = 0,
    this.totalEdges = 0,
  });

  factory ProjectGraph.fromJson(Map<String, dynamic> json) {
    final nodesList = (json['nodes'] as List?)
            ?.map((e) => ProjectGraphNode.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];
    final edgesList = (json['edges'] as List?)
            ?.map((e) => ProjectGraphEdge.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];

    return ProjectGraph(
      nodes: nodesList,
      edges: edgesList,
      snapshotId: json['snapshot_id'] as String?,
      totalNodes: json['total_nodes'] as int? ?? nodesList.length,
      totalEdges: json['total_edges'] as int? ?? edgesList.length,
    );
  }
}
