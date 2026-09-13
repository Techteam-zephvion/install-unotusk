import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/project_repository.dart';
import '../domain/project.dart';

final projectsProvider = FutureProvider<List<Project>>((ref) async {
  final repository = ref.watch(projectRepositoryProvider);
  return await repository.getProjects();
});

final selectedProjectProvider = FutureProvider.family<Project, String>((ref, id) async {
  final repository = ref.watch(projectRepositoryProvider);
  return await repository.getProjectById(id);
});
