import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/logging/app_logger.dart';
import '../data/project_repository.dart';
import '../domain/project.dart';

final projectsProvider = FutureProvider<List<Project>>((ref) async {
  final repository = ref.watch(projectRepositoryProvider);
  final logger = ref.watch(appLoggerProvider);
  logger.info(AppLogEvent.projectLoadStart);
  try {
    final projects = await repository.getProjects();
    logger.info(
      AppLogEvent.projectLoadSuccess,
      metadata: {'count': projects.length},
    );
    return projects;
  } catch (e) {
    logger.error(
      AppLogEvent.projectLoadFailure,
      message: e.toString(),
    );
    rethrow;
  }
});

final selectedProjectProvider = FutureProvider.family<Project, String>((ref, id) async {
  final repository = ref.watch(projectRepositoryProvider);
  return await repository.getProjectById(id);
});
