import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/project_repository.dart';
import '../domain/project_member.dart';

final projectMembersProvider =
    FutureProvider.family<List<ProjectMember>, String>((ref, projectId) async {
  final repository = ref.watch(projectRepositoryProvider);
  return repository.getProjectMembers(projectId);
});

class ProjectMembersNotifier extends StateNotifier<AsyncValue<List<ProjectMember>>> {
  final ProjectRepository _repository;
  final String _projectId;

  ProjectMembersNotifier(this._repository, this._projectId)
      : super(const AsyncValue.loading()) {
    loadMembers();
  }

  Future<void> loadMembers() async {
    state = const AsyncValue.loading();
    try {
      final members = await _repository.getProjectMembers(_projectId);
      state = AsyncValue.data(members);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<bool> addMember({
    String? email,
    String? userId,
    String role = 'MEMBER',
  }) async {
    try {
      await _repository.addProjectMember(
        _projectId,
        email: email,
        userId: userId,
        role: role,
      );
      await loadMembers();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> removeMember(String userId) async {
    try {
      await _repository.removeProjectMember(_projectId, userId);
      await loadMembers();
      return true;
    } catch (_) {
      return false;
    }
  }
}

final projectMembersControllerProvider = StateNotifierProvider.family<
    ProjectMembersNotifier, AsyncValue<List<ProjectMember>>, String>((ref, projectId) {
  final repository = ref.watch(projectRepositoryProvider);
  return ProjectMembersNotifier(repository, projectId);
});
