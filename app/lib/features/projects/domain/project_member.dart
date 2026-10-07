class ProjectMember {
  final String id;
  final String projectId;
  final String userId;
  final String role;
  final DateTime createdAt;
  final String? userName;
  final String? userEmail;

  const ProjectMember({
    required this.id,
    required this.projectId,
    required this.userId,
    required this.role,
    required this.createdAt,
    this.userName,
    this.userEmail,
  });

  bool get isAdmin => role.toUpperCase() == 'ADMIN';
  bool get isMember => !isAdmin;

  String get displayName =>
      (userName != null && userName!.isNotEmpty) ? userName! : (userEmail ?? 'Member');

  factory ProjectMember.fromJson(Map<String, dynamic> json) {
    return ProjectMember(
      id: json['id']?.toString() ?? '',
      projectId: json['project_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      role: json['role']?.toString() ?? 'MEMBER',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
      userName: json['user_name']?.toString(),
      userEmail: json['user_email']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'project_id': projectId,
      'user_id': userId,
      'role': role,
      'created_at': createdAt.toIso8601String(),
      'user_name': userName,
      'user_email': userEmail,
    };
  }
}
