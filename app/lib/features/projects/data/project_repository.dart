import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../domain/project.dart';
import '../domain/project_member.dart';

final projectRepositoryProvider = Provider<ProjectRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ProjectRepository(apiClient);
});

class ProjectRepository {
  final ApiClient _apiClient;

  ProjectRepository(this._apiClient);

  Future<List<Project>> getProjects() async {
    final response = await _apiClient.get(ApiEndpoints.projects);
    final data = response.data;
    List<Project> list = [];
    if (data is List) {
      list = data.map((item) => Project.fromJson(Map<String, dynamic>.from(item))).toList();
    } else if (data is Map && data['items'] is List) {
      list = (data['items'] as List)
          .map((item) => Project.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    for (final p in list) {
      if (p.port != null) {
        _apiClient.registerProjectPort(p.id, p.port!);
      }
    }
    return list;
  }

  Future<Project> getProjectById(String id) async {
    final response = await _apiClient.get(ApiEndpoints.projectById(id));
    final proj = Project.fromJson(Map<String, dynamic>.from(response.data));
    if (proj.port != null) {
      _apiClient.registerProjectPort(proj.id, proj.port!);
    }
    return proj;
  }

  Future<Project> createProject({
    required String name,
    required String organizationId,
    String? description,
    String? slug,
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.projects,
      data: {
        'name': name.trim(),
        'organization_id': organizationId,
        if (description != null && description.trim().isNotEmpty)
          'description': description.trim(),
        if (slug != null && slug.trim().isNotEmpty) 'slug': slug.trim(),
      },
    );
    return Project.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<Map<String, dynamic>> selectRepository({
    required String projectId,
    required String url,
    required String name,
    required String owner,
    String defaultBranch = 'main',
    bool isPrivate = false,
    String? description,
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.projectSelectRepository(projectId),
      data: {
        'external_id': '$owner/$name',
        'owner': owner,
        'name': name,
        'full_name': '$owner/$name',
        'default_branch': defaultBranch,
        'url': url,
        'is_private': isPrivate,
        'description': description,
      },
    );
    return Map<String, dynamic>.from(response.data);
  }

  Future<String> triggerIngestion({
    required String projectId,
    required String repositoryId,
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.projectTriggerIngest(projectId, repositoryId),
    );
    final data = response.data as Map<String, dynamic>;
    return data['snapshot_id']?.toString() ?? data['id']?.toString() ?? '';
  }

  Future<Map<String, dynamic>> getIngestionStatus({
    required String projectId,
    required String ingestionId,
  }) async {
    final response = await _apiClient.get(
      ApiEndpoints.projectIngestionStatus(projectId, ingestionId),
    );
    return Map<String, dynamic>.from(response.data);
  }

  Future<List<ProjectMember>> getProjectMembers(String projectId) async {
    final response = await _apiClient.get(ApiEndpoints.projectMembers(projectId));
    final data = response.data;
    if (data is List) {
      return data
          .map((item) => ProjectMember.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<ProjectMember> addProjectMember(
    String projectId, {
    String? email,
    String? userId,
    String role = 'MEMBER',
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.projectMembers(projectId),
      data: {
        if (email != null && email.trim().isNotEmpty) 'email': email.trim(),
        if (userId != null && userId.trim().isNotEmpty) 'user_id': userId.trim(),
        'role': role,
      },
    );
    return ProjectMember.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<void> removeProjectMember(String projectId, String userId) async {
    await _apiClient.delete(ApiEndpoints.projectMemberDelete(projectId, userId));
  }
}

