import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../domain/project.dart';

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
    if (data is List) {
      return data.map((item) => Project.fromJson(Map<String, dynamic>.from(item))).toList();
    } else if (data is Map && data['items'] is List) {
      return (data['items'] as List)
          .map((item) => Project.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<Project> getProjectById(String id) async {
    final response = await _apiClient.get(ApiEndpoints.projectById(id));
    return Project.fromJson(Map<String, dynamic>.from(response.data));
  }
}
