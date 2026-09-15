import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/desktop_scaffold.dart';
import '../../../core/widgets/error_state_view.dart';
import '../../../core/widgets/loading_state_view.dart';
import '../../../core/widgets/status_badge.dart';
import '../../projects/presentation/projects_controller.dart';
import 'tabs/architecture_tab.dart';
import 'tabs/ask_tab.dart';
import 'tabs/discoveries_tab.dart';
import 'tabs/files_tab.dart';
import 'tabs/knowledge_tab.dart';
import 'tabs/overview_tab.dart';
import 'widgets/ingestion_progress_view.dart';
import 'workspace_controller.dart';

class WorkspaceScreen extends ConsumerStatefulWidget {
  final String projectId;

  const WorkspaceScreen({
    super.key,
    required this.projectId,
  });

  @override
  ConsumerState<WorkspaceScreen> createState() => _WorkspaceScreenState();
}

class _WorkspaceScreenState extends ConsumerState<WorkspaceScreen> {
  int _selectedTabIndex = 0;
  String? _targetFilePath;
  String? _targetHighlightLines;
  String? _targetAskQuery;

  final List<String> _tabs = [
    'Overview',
    'Discoveries',
    'Architecture',
    'Files',
    'Knowledge',
    'Ask',
  ];

  void _navigateToFiles({String? filePath, String? highlightLines}) {
    setState(() {
      _targetFilePath = filePath;
      _targetHighlightLines = highlightLines;
      _selectedTabIndex = 3; // Files tab
    });
  }

  void _navigateToAsk({String? query}) {
    setState(() {
      _targetAskQuery = query;
      _selectedTabIndex = 5; // Ask tab
    });
  }

  @override
  Widget build(BuildContext context) {
    final projectAsync = ref.watch(selectedProjectProvider(widget.projectId));
    final contextAsync = ref.watch(projectContextProvider(widget.projectId));
    final criticalFindingsAsync = ref.watch(projectCriticalFindingsProvider(widget.projectId));
    final criticalCount = criticalFindingsAsync.valueOrNull?.length ?? 0;

    return DesktopScaffold(
      currentRoute: '/projects/${widget.projectId}',
      body: projectAsync.when(
        loading: () => const LoadingStateView(message: 'Loading workspace...'),
        error: (err, stack) => ErrorStateView(
          message: err.toString(),
          onRetry: () => ref.refresh(selectedProjectProvider(widget.projectId)),
        ),
        data: (project) {
          final repoContext = contextAsync.valueOrNull;
          final snapshot = repoContext?.activeSnapshot;
          final repoInfo = repoContext?.repository;

          return CallbackShortcuts(
            bindings: <ShortcutActivator, VoidCallback>{
              const SingleActivator(LogicalKeyboardKey.digit1, control: true): () => setState(() => _selectedTabIndex = 0),
              const SingleActivator(LogicalKeyboardKey.digit2, control: true): () => setState(() => _selectedTabIndex = 1),
              const SingleActivator(LogicalKeyboardKey.digit3, control: true): () => setState(() => _selectedTabIndex = 2),
              const SingleActivator(LogicalKeyboardKey.digit4, control: true): () => setState(() => _selectedTabIndex = 3),
              const SingleActivator(LogicalKeyboardKey.digit5, control: true): () => setState(() => _selectedTabIndex = 4),
              const SingleActivator(LogicalKeyboardKey.digit6, control: true): () => setState(() => _selectedTabIndex = 5),
              const SingleActivator(LogicalKeyboardKey.keyK, control: true): () => setState(() => _selectedTabIndex = 5),
            },
            child: Focus(
              autofocus: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Workspace Header
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  border: Border(
                    bottom: BorderSide(color: AppColors.slate200),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Back link
                    InkWell(
                      onTap: () => context.go('/projects'),
                      borderRadius: BorderRadius.circular(4),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.arrow_back, size: 14, color: AppColors.slate600),
                            const SizedBox(width: 6),
                            Text('Projects', style: AppTextStyles.bodySmall),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),

                    // Title, Status & Repository Context
                    Row(
                      children: [
                        Text(project.name, style: AppTextStyles.h1),
                        const SizedBox(width: 12),
                        StatusBadge(
                          label: project.status,
                          variant: project.status == 'READY'
                              ? BadgeVariant.success
                              : BadgeVariant.neutral,
                        ),
                        if (repoInfo?.fullName != null || project.repositoryName != null) ...[
                          const SizedBox(width: 12),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppColors.slate100,
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: AppColors.slate200),
                            ),
                            child: Text(
                              repoInfo?.fullName ?? project.repositoryName!,
                              style: AppTextStyles.code.copyWith(
                                color: AppColors.slate700,
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ],
                        if (snapshot != null) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppColors.slate100,
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: AppColors.slate200),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.commit, size: 12, color: AppColors.slate500),
                                const SizedBox(width: 4),
                                Text(
                                  '${snapshot.branch} @ ${snapshot.commitHash.length > 7 ? snapshot.commitHash.substring(0, 7) : snapshot.commitHash}',
                                  style: AppTextStyles.code.copyWith(
                                    color: AppColors.slate600,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Tab Navigation
                    Row(
                      children: List.generate(_tabs.length, (index) {
                        final tabName = _tabs[index];
                        final isSelected = _selectedTabIndex == index;
                        final showCount = tabName == 'Discoveries' && criticalCount > 0;

                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: InkWell(
                            onTap: () {
                              setState(() {
                                _selectedTabIndex = index;
                              });
                            },
                            borderRadius: BorderRadius.circular(4),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                              decoration: BoxDecoration(
                                color: isSelected ? AppColors.slate900 : Colors.transparent,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    tabName,
                                    style: AppTextStyles.bodyMedium.copyWith(
                                      color: isSelected ? Colors.white : AppColors.slate700,
                                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                                    ),
                                  ),
                                  if (showCount) ...[
                                    const SizedBox(width: 6),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                      decoration: BoxDecoration(
                                        color: isSelected ? Colors.white : AppColors.errorBg,
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: Text(
                                        '$criticalCount',
                                        style: AppTextStyles.bodySmall.copyWith(
                                          color: isSelected ? AppColors.slate900 : AppColors.error,
                                          fontWeight: FontWeight.w600,
                                          fontSize: 10,
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                        );
                      }),
                    ),
                  ],
                ),
              ),

              // Tab Content Area or Ingestion Progress
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(32),
                  child: (project.status != 'READY' ||
                          (snapshot != null &&
                              snapshot.status != 'COMPLETED' &&
                              snapshot.status != 'READY'))
                      ? IngestionProgressView(
                          project: project,
                          snapshot: snapshot,
                          repository: repoInfo,
                        )
                      : _buildActiveTab(project.name),
                ),
              ),
            ],
          ),
        ),
      );
    },
  ),
);
  }

  Widget _buildActiveTab(String projectName) {
    switch (_selectedTabIndex) {
      case 0:
        return OverviewTab(
          projectId: widget.projectId,
          projectName: projectName,
          onNavigateToTab: (index) {
            setState(() {
              _selectedTabIndex = index;
            });
          },
        );
      case 1:
        return DiscoveriesTab(
          projectId: widget.projectId,
          projectName: projectName,
          onNavigateToTab: (index) {
            setState(() {
              _selectedTabIndex = index;
            });
          },
          onAskAboutFinding: (query) {
            _navigateToAsk(query: query);
          },
          onNavigateToEntity: (entity) {
            _navigateToFiles(filePath: entity);
          },
        );
      case 2:
        return ArchitectureTab(
          projectId: widget.projectId,
          projectName: projectName,
          onNavigateToTab: (index) {
            setState(() {
              _selectedTabIndex = index;
            });
          },
          onNavigateToFile: (filePath) {
            _navigateToFiles(filePath: filePath);
          },
        );
      case 3:
        return FilesTab(
          projectId: widget.projectId,
          projectName: projectName,
          initialSelectedFilePath: _targetFilePath,
          initialHighlightLines: _targetHighlightLines,
        );
      case 4:
        return KnowledgeTab(
          projectId: widget.projectId,
          projectName: projectName,
          onNavigateToTab: (index) {
            setState(() {
              _selectedTabIndex = index;
            });
          },
          onNavigateToFile: (filePath) {
            _navigateToFiles(filePath: filePath);
          },
        );
      case 5:
        return AskTab(
          projectId: widget.projectId,
          projectName: projectName,
          initialQuery: _targetAskQuery,
          onNavigateToTab: (index) {
            setState(() {
              _selectedTabIndex = index;
            });
          },
          onNavigateToFileWithLines: (file, lines) {
            _navigateToFiles(filePath: file, highlightLines: lines);
          },
        );
      default:
        return OverviewTab(
          projectId: widget.projectId,
          projectName: projectName,
          onNavigateToTab: (index) {
            setState(() {
              _selectedTabIndex = index;
            });
          },
        );
    }
  }
}
