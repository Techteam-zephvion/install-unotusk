import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/project_repository.dart';
import 'projects_controller.dart';

class CreateProjectDialog extends ConsumerStatefulWidget {
  const CreateProjectDialog({super.key});

  @override
  ConsumerState<CreateProjectDialog> createState() => _CreateProjectDialogState();
}

class _CreateProjectDialogState extends ConsumerState<CreateProjectDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _slugController = TextEditingController();
  final _repoUrlController = TextEditingController();
  final _branchController = TextEditingController(text: 'main');
  final _descriptionController = TextEditingController();

  bool _isAutoSlug = true;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _nameController.addListener(_handleNameChanged);
    _repoUrlController.addListener(_handleRepoUrlChanged);
  }

  @override
  void dispose() {
    _nameController.removeListener(_handleNameChanged);
    _repoUrlController.removeListener(_handleRepoUrlChanged);
    _nameController.dispose();
    _slugController.dispose();
    _repoUrlController.dispose();
    _branchController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  void _handleNameChanged() {
    if (_isAutoSlug) {
      final name = _nameController.text.trim().toLowerCase();
      final slug = name
          .replaceAll(RegExp(r'[^a-z0-9\s-]'), '')
          .replaceAll(RegExp(r'\s+'), '-');
      _slugController.text = slug;
    }
  }

  void _handleRepoUrlChanged() {
    final url = _repoUrlController.text.trim();
    if (_nameController.text.isEmpty && url.isNotEmpty) {
      final parsed = _parseGitUrl(url);
      if (parsed != null && parsed.name.isNotEmpty) {
        _nameController.text = parsed.name;
      }
    }
  }

  ({String owner, String name})? _parseGitUrl(String url) {
    try {
      var clean = url.trim();
      if (clean.endsWith('.git')) {
        clean = clean.substring(0, clean.length - 4);
      }
      final uri = Uri.tryParse(clean);
      if (uri != null && uri.pathSegments.length >= 2) {
        final segments = uri.pathSegments;
        final owner = segments[segments.length - 2];
        final name = segments[segments.length - 1];
        return (owner: owner, name: name);
      }
      // Support SSH git@github.com:owner/repo
      if (clean.contains(':') && clean.contains('/')) {
        final parts = clean.split(':');
        if (parts.length == 2) {
          final subParts = parts[1].split('/');
          if (subParts.length >= 2) {
            return (owner: subParts[0], name: subParts[1]);
          }
        }
      }
    } catch (_) {}
    return null;
  }

  Future<void> _handleCreate() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final user = ref.read(authControllerProvider).user;
    final orgId = user?.organizationId;

    if (orgId == null || orgId.isEmpty) {
      setState(() {
        _errorMessage = 'No active organization found for this user session. Please re-authenticate.';
      });
      return;
    }

    final repoUrl = _repoUrlController.text.trim();
    final parsedRepo = _parseGitUrl(repoUrl);
    if (parsedRepo == null) {
      setState(() {
        _errorMessage = 'Invalid Git URL. Must be in the format: https://github.com/owner/repository';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final repo = ref.read(projectRepositoryProvider);

      // 1. Create Project
      final project = await repo.createProject(
        name: _nameController.text.trim(),
        organizationId: orgId,
        slug: _slugController.text.trim().isNotEmpty ? _slugController.text.trim() : null,
        description: _descriptionController.text.trim().isNotEmpty ? _descriptionController.text.trim() : null,
      );

      // 2. Select / Connect Repository
      final repoData = await repo.selectRepository(
        projectId: project.id,
        url: repoUrl,
        owner: parsedRepo.owner,
        name: parsedRepo.name,
        defaultBranch: _branchController.text.trim().isNotEmpty ? _branchController.text.trim() : 'main',
        description: _descriptionController.text.trim().isNotEmpty ? _descriptionController.text.trim() : null,
      );

      // 3. Trigger Ingestion
      final repoId = repoData['id']?.toString();
      if (repoId != null && repoId.isNotEmpty) {
        await repo.triggerIngestion(
          projectId: project.id,
          repositoryId: repoId,
        );
      }

      // Refresh project list
      ref.invalidate(projectsProvider);

      if (mounted) {
        Navigator.of(context).pop();
        context.go('/projects/${project.id}');
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString().replaceAll('Exception:', '').trim();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Container(
        constraints: const BoxConstraints(maxWidth: 520),
        padding: const EdgeInsets.all(28),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Connect Codebase', style: AppTextStyles.h2),
                        const SizedBox(height: 4),
                        Text(
                          'Link a software repository to start grounding project intelligence.',
                          style: AppTextStyles.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 18, color: AppColors.slate500),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Git Repository URL
              AppTextField(
                controller: _repoUrlController,
                label: 'Repository URL',
                hint: 'https://github.com/owner/repository',
                prefixIcon: const Icon(Icons.link, size: 16),
                validator: (val) {
                  if (val == null || val.trim().isEmpty) {
                    return 'Repository URL is required';
                  }
                  if (_parseGitUrl(val.trim()) == null) {
                    return 'Enter a valid Git repository URL (e.g. https://github.com/psf/requests)';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 14),

              // Project Name & Default Branch in a 2-column row
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 3,
                    child: AppTextField(
                      controller: _nameController,
                      label: 'Project Name',
                      hint: 'Requests',
                      prefixIcon: const Icon(Icons.folder_outlined, size: 16),
                      validator: (val) {
                        if (val == null || val.trim().isEmpty) {
                          return 'Project name is required';
                        }
                        return null;
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: AppTextField(
                      controller: _branchController,
                      label: 'Branch',
                      hint: 'main',
                      prefixIcon: const Icon(Icons.alt_route, size: 16),
                      validator: (val) {
                        if (val == null || val.trim().isEmpty) {
                          return 'Branch is required';
                        }
                        return null;
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Slug (Auto-generated)
              AppTextField(
                controller: _slugController,
                label: 'Project Slug',
                hint: 'requests',
                prefixIcon: const Icon(Icons.tag, size: 16),
                onChanged: (val) {
                  setState(() {
                    _isAutoSlug = false;
                  });
                },
                validator: (val) {
                  if (val != null && val.trim().isNotEmpty && val.trim().length < 2) {
                    return 'Slug must be at least 2 characters';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 14),

              // Description (Optional)
              AppTextField(
                controller: _descriptionController,
                label: 'Description (Optional)',
                hint: 'Python HTTP for humans',
                prefixIcon: const Icon(Icons.notes, size: 16),
              ),
              const SizedBox(height: 16),

              // Error Display
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.errorBg,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppColors.errorBorder),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, size: 16, color: AppColors.error),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Actions
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  AppButton(
                    text: 'Cancel',
                    variant: AppButtonVariant.secondary,
                    onPressed: _isLoading ? null : () => Navigator.of(context).pop(),
                  ),
                  const SizedBox(width: 10),
                  AppButton(
                    text: 'Connect & Ingest',
                    isLoading: _isLoading,
                    onPressed: _handleCreate,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
