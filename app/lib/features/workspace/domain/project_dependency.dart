class ProjectDependency {
  final String id;
  final String sourceFileId;
  final String? targetFileId;
  final String? externalPackage;
  final String dependencyType;
  final int lineNumber;
  final String? sourcePath;
  final String? targetPath;

  const ProjectDependency({
    required this.id,
    required this.sourceFileId,
    this.targetFileId,
    this.externalPackage,
    required this.dependencyType,
    required this.lineNumber,
    this.sourcePath,
    this.targetPath,
  });

  factory ProjectDependency.fromJson(Map<String, dynamic> json) {
    return ProjectDependency(
      id: json['id']?.toString() ?? '',
      sourceFileId: json['source_file_id']?.toString() ?? '',
      targetFileId: json['target_file_id']?.toString(),
      externalPackage: json['external_package']?.toString(),
      dependencyType: json['dependency_type']?.toString() ?? 'IMPORT',
      lineNumber: (json['line_number'] as num?)?.toInt() ?? 0,
      sourcePath: json['source_path']?.toString(),
      targetPath: json['target_path']?.toString(),
    );
  }
}
