import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/app_card.dart';
import '../../../projects/data/project_repository.dart';
import '../../../projects/domain/project.dart';
import '../../../projects/presentation/projects_controller.dart';
import '../../domain/repository_context.dart';
import '../workspace_controller.dart';

class IngestionProgressView extends ConsumerStatefulWidget {
  final Project project;
  final ActiveSnapshot? snapshot;
  final RepositoryInfo? repository;

  const IngestionProgressView({
    super.key,
    required this.project,
    this.snapshot,
    this.repository,
  });

  @override
  ConsumerState<IngestionProgressView> createState() => _IngestionProgressViewState();
}

class _IngestionProgressViewState extends ConsumerState<IngestionProgressView> {
  Timer? _pollTimer;
  bool _isRetrying = false;
  String? _retryError;

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (timer) {
      if (!mounted) return;
      ref.invalidate(selectedProjectProvider(widget.project.id));
      ref.invalidate(projectContextProvider(widget.project.id));
    });
  }

  Future<void> _handleRetry() async {
    final repoId = widget.repository?.id ?? widget.snapshot?.repositoryId;
    if (repoId == null || repoId.isEmpty) return;

    setState(() {
      _isRetrying = true;
      _retryError = null;
    });

    try {
      final repo = ref.read(projectRepositoryProvider);
      await repo.triggerIngestion(
        projectId: widget.project.id,
        repositoryId: repoId,
      );
      ref.invalidate(selectedProjectProvider(widget.project.id));
      ref.invalidate(projectContextProvider(widget.project.id));
    } catch (e) {
      setState(() {
        _retryError = e.toString().replaceAll('Exception:', '').trim();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isRetrying = false;
        });
      }
    }
  }

  int _getPhaseIndex(String status) {
    switch (status.toUpperCase()) {
      case 'QUEUED':
        return 0;
      case 'CLONING':
        return 1;
      case 'SCANNING':
        return 2;
      case 'PARSING':
        return 3;
      case 'INDEXING':
        return 4;
      case 'COMPLETED':
      case 'READY':
        return 5;
      default:
        return 0;
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentStatus = widget.snapshot?.status.toUpperCase() ??
        (widget.project.status.toUpperCase() == 'READY' ? 'READY' : 'CLONING');
    final isFailed = currentStatus == 'FAILED' || widget.project.status.toUpperCase() == 'ERROR';
    final activePhase = _getPhaseIndex(currentStatus);

    final phases = [
      {'key': 'CLONING', 'title': 'Cloning Codebase', 'desc': 'Fetching Git tree and verifying commit references'},
      {'key': 'SCANNING', 'title': 'Scanning File Tree', 'desc': 'Enumerating directories and filtering source files'},
      {'key': 'PARSING', 'title': 'Parsing AST Symbols', 'desc': 'Extracting functions, classes, interfaces, and imports'},
      {'key': 'INDEXING', 'title': 'Indexing & Dependency Mapping', 'desc': 'Generating vector embeddings and building graph edges'},
      {'key': 'READY', 'title': 'Intelligence Engine Online', 'desc': 'Architectural context and grounded Q&A active'},
    ];

    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 580),
        padding: const EdgeInsets.all(24),
        child: AppCard(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: isFailed ? AppColors.errorBg : AppColors.slate100,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: isFailed ? AppColors.errorBorder : AppColors.slate200,
                      ),
                    ),
                    child: Icon(
                      isFailed ? Icons.error_outline : Icons.sync,
                      size: 20,
                      color: isFailed ? AppColors.error : AppColors.primary,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          isFailed ? 'Ingestion Encountered an Issue' : 'Analyzing Codebase',
                          style: AppTextStyles.h2,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          widget.repository?.fullName ?? widget.project.name,
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.slate600,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Description
              Text(
                isFailed
                    ? 'The background ingestion worker was unable to complete analyzing this repository. You can trigger a clean re-run below.'
                    : 'Unotusk is building an AST symbol hierarchy and dependency graph. Evidentiary intelligence will unlock as soon as indexing completes.',
                style: AppTextStyles.bodySmall,
              ),
              const SizedBox(height: 24),

              // Phase List
              Column(
                children: List.generate(phases.length, (index) {
                  final phase = phases[index];
                  final isDone = !isFailed && activePhase > index;
                  final isCurrent = !isFailed && activePhase == index;
                  final isPhaseFailed = isFailed && activePhase == index;

                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Phase Step Icon
                        Container(
                          width: 24,
                          height: 24,
                          margin: const EdgeInsets.only(top: 2),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isDone
                                ? AppColors.successBg
                                : isCurrent
                                    ? AppColors.primaryMuted
                                    : isPhaseFailed
                                        ? AppColors.errorBg
                                        : AppColors.slate100,
                            border: Border.all(
                              color: isDone
                                  ? AppColors.successBorder
                                  : isCurrent
                                      ? AppColors.primary
                                      : isPhaseFailed
                                          ? AppColors.errorBorder
                                          : AppColors.slate200,
                            ),
                          ),
                          child: Center(
                            child: isDone
                                ? const Icon(Icons.check, size: 14, color: AppColors.success)
                                : isCurrent
                                    ? const SizedBox(
                                        width: 10,
                                        height: 10,
                                        child: CircularProgressIndicator(strokeWidth: 2),
                                      )
                                    : isPhaseFailed
                                        ? const Icon(Icons.close, size: 14, color: AppColors.error)
                                        : Text(
                                            '${index + 1}',
                                            style: const TextStyle(
                                              fontSize: 11,
                                              color: AppColors.slate500,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                phase['title']!,
                                style: AppTextStyles.bodyMedium.copyWith(
                                  fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w500,
                                  color: isCurrent
                                      ? AppColors.slate900
                                      : isDone
                                          ? AppColors.slate800
                                          : AppColors.slate500,
                                ),
                              ),
                              Text(
                                phase['desc']!,
                                style: AppTextStyles.bodySmall.copyWith(
                                  fontSize: 11,
                                  color: AppColors.slate500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ),

              if (isFailed) ...[
                const SizedBox(height: 16),
                if (_retryError != null) ...[
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.errorBg,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppColors.errorBorder),
                    ),
                    child: Text(
                      _retryError!,
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
                AppButton(
                  text: 'Retry Ingestion',
                  icon: Icons.refresh,
                  isLoading: _isRetrying,
                  onPressed: _handleRetry,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
