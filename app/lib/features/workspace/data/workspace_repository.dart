import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../domain/discovery_summary.dart';
import '../domain/file_detail.dart';
import '../domain/grounded_answer.dart';
import '../domain/project_dependency.dart';
import '../domain/project_file.dart';
import '../domain/project_finding.dart';
import '../domain/project_knowledge.dart';
import '../domain/project_symbol.dart';
import '../domain/repository_context.dart';

final workspaceRepositoryProvider = Provider<WorkspaceRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkspaceRepository(apiClient);
});

class WorkspaceRepository {
  final ApiClient _apiClient;

  WorkspaceRepository(this._apiClient);

  Future<ProjectRepositoryContext> getProjectRepositoryContext(String projectId) async {
    final response = await _apiClient.get(ApiEndpoints.projectRepositoryContext(projectId));
    return ProjectRepositoryContext.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<List<ProjectFile>> getProjectFiles(String projectId, {int limit = 500}) async {
    final response = await _apiClient.get(ApiEndpoints.projectFiles(projectId, limit: limit));
    final data = response.data;
    if (data is List) {
      return data
          .map((item) => ProjectFile.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<FileDetail> getFileDetail(String projectId, String fileId) async {
    final response = await _apiClient.get(ApiEndpoints.projectFileDetail(projectId, fileId));
    return FileDetail.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<List<ProjectSymbol>> getProjectSymbols(String projectId, {int limit = 500}) async {
    final response = await _apiClient.get(ApiEndpoints.projectSymbols(projectId, limit: limit));
    final data = response.data;
    if (data is List) {
      return data
          .map((item) => ProjectSymbol.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<List<ProjectDependency>> getProjectDependencies(String projectId, {int limit = 500}) async {
    final response = await _apiClient.get(ApiEndpoints.projectDependencies(projectId, limit: limit));
    final data = response.data;
    if (data is List) {
      return data
          .map((item) => ProjectDependency.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<DiscoverySummary> getDiscoverySummary(String projectId) async {
    final response = await _apiClient.get(ApiEndpoints.projectDiscoverStatus(projectId));
    return DiscoverySummary.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<List<ProjectFinding>> getFindings(
    String projectId, {
    String? severity,
    String? status,
    String? category,
  }) async {
    final queryParams = <String, dynamic>{};
    if (severity != null) queryParams['severity'] = severity;
    if (status != null) queryParams['status'] = status;
    if (category != null) queryParams['category'] = category;

    final response = await _apiClient.get(
      ApiEndpoints.projectFindings(projectId),
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
    final data = response.data;
    if (data is List) {
      return data
          .map((item) => ProjectFinding.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<ProjectFinding> getFinding(String projectId, String findingId) async {
    final response = await _apiClient.get(ApiEndpoints.projectFindingDetail(projectId, findingId));
    return ProjectFinding.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<ProjectFinding> updateFindingStatus(String projectId, String findingId, String status) async {
    final response = await _apiClient.patch(
      ApiEndpoints.projectFindingDetail(projectId, findingId),
      data: {'status': status},
    );
    return ProjectFinding.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<void> triggerDiscovery(String projectId) async {
    await _apiClient.post(ApiEndpoints.projectDiscoverTrigger(projectId));
  }

  // Knowledge Management
  Future<List<ProjectKnowledge>> getKnowledge(
    String projectId, {
    String? category,
    String? status,
  }) async {
    final response = await _apiClient.get(
      ApiEndpoints.projectKnowledge(projectId, category: category, status: status),
    );
    final data = response.data;
    if (data is Map && data['items'] is List) {
      return (data['items'] as List)
          .map((item) => ProjectKnowledge.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<ProjectKnowledge> getKnowledgeItem(String projectId, String knowledgeId) async {
    final response = await _apiClient.get(ApiEndpoints.projectKnowledgeDetail(projectId, knowledgeId));
    return ProjectKnowledge.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<ProjectKnowledge> createKnowledge(
    String projectId, {
    required String category,
    required String title,
    required String content,
    String? relatedFilePath,
    String? relatedSymbol,
    String? relatedFindingId,
  }) async {
    final payload = <String, dynamic>{
      'category': category,
      'title': title,
      'content': content,
    };
    if (relatedFilePath != null) payload['related_file_path'] = relatedFilePath;
    if (relatedSymbol != null) payload['related_symbol'] = relatedSymbol;
    if (relatedFindingId != null) payload['related_finding_id'] = relatedFindingId;

    final response = await _apiClient.post(
      ApiEndpoints.projectKnowledge(projectId),
      data: payload,
    );
    return ProjectKnowledge.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<ProjectKnowledge> updateKnowledge(
    String projectId,
    String knowledgeId, {
    String? category,
    String? title,
    String? content,
    String? status,
  }) async {
    final payload = <String, dynamic>{};
    if (category != null) payload['category'] = category;
    if (title != null) payload['title'] = title;
    if (content != null) payload['content'] = content;
    if (status != null) payload['status'] = status;

    final response = await _apiClient.patch(
      ApiEndpoints.projectKnowledgeDetail(projectId, knowledgeId),
      data: payload,
    );
    return ProjectKnowledge.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<ProjectKnowledge> archiveKnowledge(String projectId, String knowledgeId) async {
    final response = await _apiClient.post(
      ApiEndpoints.projectKnowledgeArchive(projectId, knowledgeId),
    );
    return ProjectKnowledge.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<ProjectKnowledge> restoreKnowledge(String projectId, String knowledgeId) async {
    final response = await _apiClient.post(
      ApiEndpoints.projectKnowledgeRestore(projectId, knowledgeId),
    );
    return ProjectKnowledge.fromJson(Map<String, dynamic>.from(response.data));
  }

  // Grounded Ask & Intelligence
  Future<GroundedAnswer> askQuestion(
    String projectId,
    String question, {
    String? conversationId,
  }) async {
    final payload = <String, dynamic>{
      'question': question,
    };
    if (conversationId != null) payload['conversation_id'] = conversationId;

    final response = await _apiClient.post(
      ApiEndpoints.projectAsk(projectId),
      data: payload,
    );
    return GroundedAnswer.fromJson(Map<String, dynamic>.from(response.data));
  }

  Future<List<ConversationThread>> getConversations(String projectId) async {
    final response = await _apiClient.get(ApiEndpoints.projectConversations(projectId));
    final data = response.data;
    if (data is List) {
      return data
          .map((item) => ConversationThread.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }

  Future<ConversationThread> createConversation(
    String projectId, {
    String? title,
    String? initialQuestion,
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.projectConversations(projectId),
      data: {
        'title': title,
        'initial_question': initialQuestion,
      },
    );
    return ConversationThread.fromJson(Map<String, dynamic>.from(response.data));
  }
}
