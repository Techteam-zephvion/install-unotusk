class OrganizationMember {
  final String id;
  final String organizationId;
  final String userId;
  final String userName;
  final String userEmail;
  final String role;
  final DateTime createdAt;

  const OrganizationMember({
    required this.id,
    required this.organizationId,
    required this.userId,
    required this.userName,
    required this.userEmail,
    required this.role,
    required this.createdAt,
  });

  bool get isOwner => role.toUpperCase() == 'OWNER';
  bool get isAdmin => role.toUpperCase() == 'ADMIN' || isOwner;
  bool get isMember => !isAdmin;

  String get displayName =>
      userName.isNotEmpty ? userName : userEmail.split('@').first;

  factory OrganizationMember.fromJson(Map<String, dynamic> json) {
    return OrganizationMember(
      id: json['id']?.toString() ?? '',
      organizationId: json['organization_id']?.toString() ?? '',
      userId: json['user_id']?.toString() ?? '',
      userName: json['user_name']?.toString() ?? '',
      userEmail: json['user_email']?.toString() ?? '',
      role: json['role']?.toString() ?? 'MEMBER',
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'organization_id': organizationId,
      'user_id': userId,
      'user_name': userName,
      'user_email': userEmail,
      'role': role,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
