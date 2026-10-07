class ProjectFile {
  final String id;
  final String snapshotId;
  final String path;
  final String filename;
  final String extension;
  final String language;
  final int sizeBytes;
  final String contentHash;
  final bool isBinary;
  final bool isGenerated;
  final bool isTest;
  final int lineCount;
  final bool parserSupported;

  const ProjectFile({
    required this.id,
    required this.snapshotId,
    required this.path,
    required this.filename,
    required this.extension,
    required this.language,
    required this.sizeBytes,
    required this.contentHash,
    required this.isBinary,
    required this.isGenerated,
    required this.isTest,
    required this.lineCount,
    required this.parserSupported,
  });

  factory ProjectFile.fromJson(Map<String, dynamic> json) {
    return ProjectFile(
      id: json['id']?.toString() ?? '',
      snapshotId: json['snapshot_id']?.toString() ?? '',
      path: json['path']?.toString() ?? '',
      filename: json['filename']?.toString() ?? '',
      extension: json['extension']?.toString() ?? '',
      language: json['language']?.toString() ?? 'UNKNOWN',
      sizeBytes: (json['size_bytes'] as num?)?.toInt() ?? 0,
      contentHash: json['content_hash']?.toString() ?? '',
      isBinary: json['is_binary'] == true,
      isGenerated: json['is_generated'] == true,
      isTest: json['is_test'] == true,
      lineCount: (json['line_count'] as num?)?.toInt() ?? 0,
      parserSupported: json['parser_supported'] == true,
    );
  }
}
