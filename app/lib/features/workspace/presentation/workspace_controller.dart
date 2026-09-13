import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/workspace_repository.dart';
import '../domain/discovery_summary.dart';
import '../domain/file_detail.dart';
import '../domain/grounded_answer.dart';
import '../domain/project_dependency.dart';
import '../domain/project_file.dart';
import '../domain/project_finding.dart';
import '../domain/project_knowledge.dart';
import '../domain/project_symbol.dart';
import '../domain/repository_context.dart';

final projectContextProvider = FutureProvider.family<ProjectRepositoryContext, String>((ref, projectId) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getProjectRepositoryContext(projectId);
});

final projectFilesProvider = FutureProvider.family<List<ProjectFile>, String>((ref, projectId) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getProjectFiles(projectId);
});

final projectFileDetailProvider = FutureProvider.family<FileDetail, ({String projectId, String fileId})>((ref, arg) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getFileDetail(arg.projectId, arg.fileId);
});

final projectSymbolsProvider = FutureProvider.family<List<ProjectSymbol>, String>((ref, projectId) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getProjectSymbols(projectId);
});

final projectDependenciesProvider = FutureProvider.family<List<ProjectDependency>, String>((ref, projectId) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getProjectDependencies(projectId);
});

final projectDiscoverySummaryProvider = FutureProvider.family<DiscoverySummary, String>((ref, projectId) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getDiscoverySummary(projectId);
});

final projectCriticalFindingsProvider = FutureProvider.family<List<ProjectFinding>, String>((ref, projectId) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getFindings(projectId, severity: 'CRITICAL', status: 'OPEN');
});

final projectFindingsListProvider = FutureProvider.family<List<ProjectFinding>, ({String projectId, String? severity, String? status, String? category})>((ref, arg) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getFindings(
    arg.projectId,
    severity: arg.severity,
    status: arg.status,
    category: arg.category,
  );
});

final projectFindingDetailProvider = FutureProvider.family<ProjectFinding, ({String projectId, String findingId})>((ref, arg) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getFinding(arg.projectId, arg.findingId);
});

final projectKnowledgeListProvider = FutureProvider.family<List<ProjectKnowledge>, ({String projectId, String? category, String? status})>((ref, arg) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getKnowledge(
    arg.projectId,
    category: arg.category,
    status: arg.status,
  );
});

final projectConversationsProvider = FutureProvider.family<List<ConversationThread>, String>((ref, projectId) async {
  final repository = ref.watch(workspaceRepositoryProvider);
  return repository.getConversations(projectId);
});
