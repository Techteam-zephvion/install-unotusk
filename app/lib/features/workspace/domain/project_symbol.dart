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
