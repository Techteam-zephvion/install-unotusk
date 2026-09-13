import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/desktop_scaffold.dart';
import '../../../core/widgets/empty_state_view.dart';
import '../../../core/widgets/error_state_view.dart';
import '../../../core/widgets/loading_state_view.dart';
import '../../../core/widgets/status_badge.dart';
import '../domain/project.dart';
import 'projects_controller.dart';

class ProjectsScreen extends ConsumerStatefulWidget {
  const ProjectsScreen({super.key});

  @override
  ConsumerState<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends ConsumerState<ProjectsScreen> {
  final _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final projectsAsync = ref.watch(projectsProvider);

    return DesktopScaffold(
      currentRoute: '/projects',
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Page Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Projects', style: AppTextStyles.h1),
                    const SizedBox(height: 4),
                    Text(
                      'Software projects available in your workspace',
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
                Row(
                  children: [
                    AppButton(
                      text: 'Refresh',
                      icon: Icons.refresh,
                      variant: AppButtonVariant.secondary,
                      onPressed: () => ref.refresh(projectsProvider),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Search Bar
            SizedBox(
              width: 320,
              child: AppTextField(
                controller: _searchController,
                hint: 'Filter projects...',
                prefixIcon: const Icon(Icons.search, size: 16),
                onChanged: (val) {
                  setState(() {
                    _searchQuery = val.trim().toLowerCase();
                  });
                },
              ),
            ),
            const SizedBox(height: 16),

            // Project List Area
            Expanded(
              child: projectsAsync.when(
                loading: () => const LoadingStateView(message: 'Loading projects...'),
                error: (err, stack) => ErrorStateView(
                  message: err.toString(),
                  onRetry: () => ref.refresh(projectsProvider),
                ),
                data: (projects) {
                  final filtered = projects.where((p) {
                    if (_searchQuery.isEmpty) return true;
                    return p.name.toLowerCase().contains(_searchQuery) ||
                        (p.description?.toLowerCase().contains(_searchQuery) ?? false) ||
                        (p.repositoryName?.toLowerCase().contains(_searchQuery) ?? false);
                  }).toList();

                  if (filtered.isEmpty) {
                    return EmptyStateView(
                      icon: Icons.folder_open_outlined,
                      title: _searchQuery.isEmpty ? 'No projects yet' : 'No matching projects',
                      description: _searchQuery.isEmpty
                          ? 'No software repositories have been connected to this workspace yet.'
                          : 'Try changing your filter query.',
                    );
                  }

                  return ListView.separated(
                    itemCount: filtered.length,
                    separatorBuilder: (context, index) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final project = filtered[index];
                      return _ProjectItemCard(project: project);
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProjectItemCard extends StatelessWidget {
  final Project project;

  const _ProjectItemCard({required this.project});

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      onTap: () => context.go('/projects/${project.id}'),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.slate100,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: AppColors.slate200),
            ),
            child: const Icon(Icons.code_outlined, size: 18, color: AppColors.slate700),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(project.name, style: AppTextStyles.h3),
                    const SizedBox(width: 10),
                    StatusBadge(
                      label: project.status,
                      variant: project.status == 'READY'
                          ? BadgeVariant.success
                          : BadgeVariant.neutral,
                    ),
                  ],
                ),
                if (project.description != null && project.description!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    project.description!,
                    style: AppTextStyles.bodySmall,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ] else if (project.repositoryName != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    project.repositoryName!,
                    style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 16),
          Row(
            children: [
              Text('Open', style: AppTextStyles.label.copyWith(color: AppColors.primary)),
              const SizedBox(width: 4),
              const Icon(Icons.arrow_forward, size: 14, color: AppColors.primary),
            ],
          ),
        ],
      ),
    );
  }
}
