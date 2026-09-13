import 'project_dependency.dart';
import 'project_file.dart';
import 'project_symbol.dart';

class CodeChunk {
  final String id;
  final String chunkType;
  final String name;
  final String path;
  final String content;
  final int startLine;
  final int endLine;

  const CodeChunk({
    required this.id,
    required this.chunkType,
    required this.name,
    required this.path,
    required this.content,
    required this.startLine,
    required this.endLine,
  });

  factory CodeChunk.fromJson(Map<String, dynamic> json) {
    return CodeChunk(
      id: json['id']?.toString() ?? '',
      chunkType: json['chunk_type']?.toString() ?? 'code',
      name: json['name']?.toString() ?? '',
      path: json['path']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      startLine: (json['start_line'] as num?)?.toInt() ?? 0,
      endLine: (json['end_line'] as num?)?.toInt() ?? 0,
    );
  }
}

class FileDetail {
  final ProjectFile file;
  final List<ProjectSymbol> symbols;
  final List<ProjectDependency> outgoingDependencies;
  final List<ProjectDependency> incomingReferences;
  final List<CodeChunk> chunks;
  final String? fullContent;

  const FileDetail({
    required this.file,
    this.symbols = const [],
    this.outgoingDependencies = const [],
    this.incomingReferences = const [],
    this.chunks = const [],
    this.fullContent,
  });

  factory FileDetail.fromJson(Map<String, dynamic> json) {
    final rawSymbols = json['symbols'];
    final rawOutDeps = json['outgoing_dependencies'];
    final rawInRefs = json['incoming_references'];
    final rawChunks = json['chunks'];

    return FileDetail(
      file: ProjectFile.fromJson(Map<String, dynamic>.from(json['file'])),
      symbols: rawSymbols is List
          ? rawSymbols
              .map((s) => ProjectSymbol.fromJson(Map<String, dynamic>.from(s)))
              .toList()
          : const [],
      outgoingDependencies: rawOutDeps is List
          ? rawOutDeps
              .map((d) => ProjectDependency.fromJson(Map<String, dynamic>.from(d)))
              .toList()
          : const [],
      incomingReferences: rawInRefs is List
          ? rawInRefs
              .map((d) => ProjectDependency.fromJson(Map<String, dynamic>.from(d)))
              .toList()
          : const [],
      chunks: rawChunks is List
          ? rawChunks
              .map((c) => CodeChunk.fromJson(Map<String, dynamic>.from(c)))
              .toList()
          : const [],
      fullContent: json['full_content']?.toString(),
    );
  }
}
