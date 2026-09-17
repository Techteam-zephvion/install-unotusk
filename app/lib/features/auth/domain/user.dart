class User {
  final String id;
  final String email;
  final String fullName;
  final String role;
  final String? organizationId;

  const User({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    this.organizationId,
  });

  String get name => fullName.isNotEmpty ? fullName : email.split('@').first;

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? json['name']?.toString() ?? '',
      role: json['role']?.toString() ?? 'member',
      organizationId: json['organization_id']?.toString() ?? json['default_organization_id']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'role': role,
      'organization_id': organizationId,
    };
  }
}
