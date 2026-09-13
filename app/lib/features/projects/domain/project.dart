class Project {
  final String id;
  final String name;
  final String slug;
  final String? description;
  final String status;
  final DateTime? updatedAt;
  final String? repositoryName;

  const Project({
    required this.id,
    required this.name,
    required this.slug,
    this.description,
    required this.status,
    this.updatedAt,
    this.repositoryName,
  });

  factory Project.fromJson(Map<String, dynamic> json) {
    return Project(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      slug: json['slug']?.toString() ?? '',
      description: json['description']?.toString(),
      status: json['status']?.toString() ?? 'CREATED',
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'].toString())
          : null,
      repositoryName: json['repository']?['full_name']?.toString(),
    );
  }
}
