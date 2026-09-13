class ApiEndpoints {
  // Health / Connection
  static const String health = '/health';

  // Authentication
  static const String login = '/auth/login';
  static const String signup = '/auth/signup';
  static const String me = '/auth/me';

  // Projects & Workspace Context
  static const String projects = '/projects';
  static String projectById(String id) => '/projects/$id';
  static String projectSnapshots(String projectId) => '/projects/$projectId/snapshots';
  static String projectRepositoryContext(String projectId) => '/projects/$projectId/repository';
  static String projectFiles(String projectId, {int limit = 500}) => '/projects/$projectId/files?limit=$limit';
  static String projectFileDetail(String projectId, String fileId) => '/projects/$projectId/files/$fileId';
  static String projectSymbols(String projectId, {int limit = 500}) => '/projects/$projectId/symbols?limit=$limit';
  static String projectDependencies(String projectId, {int limit = 500}) => '/projects/$projectId/dependencies?limit=$limit';
  static String projectDiscoverStatus(String projectId) => '/projects/$projectId/discover/status';
  static String projectDiscoverTrigger(String projectId) => '/projects/$projectId/discover';
  static String projectFindings(String projectId) => '/projects/$projectId/findings';
  static String projectFindingDetail(String projectId, String findingId) => '/projects/$projectId/findings/$findingId';

  // Knowledge Management
  static String projectKnowledge(String projectId, {String? category, String? status}) {
    final params = <String>[];
    if (category != null) params.add('category=$category');
    if (status != null) params.add('status=$status');
    final query = params.isNotEmpty ? '?${params.join('&')}' : '';
    return '/projects/$projectId/knowledge$query';
  }
  static String projectKnowledgeDetail(String projectId, String knowledgeId) => '/projects/$projectId/knowledge/$knowledgeId';
  static String projectKnowledgeArchive(String projectId, String knowledgeId) => '/projects/$projectId/knowledge/$knowledgeId/archive';
  static String projectKnowledgeRestore(String projectId, String knowledgeId) => '/projects/$projectId/knowledge/$knowledgeId/restore';

  // Grounded Ask & Intelligence
  static String projectAsk(String projectId) => '/projects/$projectId/ask';
  static String projectConversations(String projectId) => '/projects/$projectId/conversations';
  static String projectConversationDetail(String projectId, String conversationId) => '/projects/$projectId/conversations/$conversationId';
  static String projectConversationMessages(String projectId, String conversationId) => '/projects/$projectId/conversations/$conversationId/messages';
}
