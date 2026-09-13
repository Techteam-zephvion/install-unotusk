import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../core/widgets/error_state_view.dart';
import '../../../../core/widgets/loading_state_view.dart';
import '../../data/workspace_repository.dart';
import '../../domain/project_knowledge.dart';
import '../widgets/knowledge_card.dart';
import '../widgets/knowledge_form_dialog.dart';
import '../workspace_controller.dart';

class KnowledgeTab extends ConsumerStatefulWidget {
  final String projectId;
  final String projectName;
  final void Function(int tabIndex)? onNavigateToTab;
  final void Function(String filePath)? onNavigateToFile;

  const KnowledgeTab({
    super.key,
    required this.projectId,
    required this.projectName,
    this.onNavigateToTab,
    this.onNavigateToFile,
  });

  @override
  ConsumerState<KnowledgeTab> createState() => _KnowledgeTabState();
}

class _KnowledgeTabState extends ConsumerState<KnowledgeTab> {
  String? _selectedCategory;
  String? _selectedStatus = 'ACTIVE';
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _openCreateDialog() async {
    await showDialog(
      context: context,
      builder: (ctx) => KnowledgeFormDialog(
        onSave: ({
          required String category,
          required String title,
          required String content,
          String? relatedFilePath,
          String? relatedSymbol,
        }) async {
          await ref.read(workspaceRepositoryProvider).createKnowledge(
                widget.projectId,
                category: category,
                title: title,
                content: content,
                relatedFilePath: relatedFilePath,
                relatedSymbol: relatedSymbol,
              );
          ref.invalidate(projectKnowledgeListProvider);
        },
      ),
    );
  }

  Future<void> _openEditDialog(ProjectKnowledge item) async {
    await showDialog(
      context: context,
      builder: (ctx) => KnowledgeFormDialog(
        initialItem: item,
        onSave: ({
          required String category,
          required String title,
          required String content,
          String? relatedFilePath,
          String? relatedSymbol,
        }) async {
          await ref.read(workspaceRepositoryProvider).updateKnowledge(
                widget.projectId,
                item.id,
                category: category,
                title: title,
                content: content,
              );
          ref.invalidate(projectKnowledgeListProvider);
        },
      ),
    );
  }

  Future<void> _toggleArchive(ProjectKnowledge item) async {
    try {
      if (item.status == 'ARCHIVED') {
        await ref.read(workspaceRepositoryProvider).restoreKnowledge(widget.projectId, item.id);
      } else {
        await ref.read(workspaceRepositoryProvider).archiveKnowledge(widget.projectId, item.id);
      }
      ref.invalidate(projectKnowledgeListProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Operation failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final knowledgeAsync = ref.watch(
      projectKnowledgeListProvider((
        projectId: widget.projectId,
        category: _selectedCategory,
        status: _selectedStatus,
      )),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Controls Row: Search + Category Filter + Status Filter + Add Button
        Row(
          children: [
            // Search Input
            Expanded(
              flex: 3,
              child: SizedBox(
                height: 38,
                child: TextField(
                  controller: _searchController,
                  style: AppTextStyles.bodySmall,
                  decoration: InputDecoration(
                    hintText: 'Search knowledge context...',
                    hintStyle: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                    prefixIcon: const Icon(Icons.search, size: 16, color: AppColors.slate400),
                    suffixIcon: _searchQuery.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 14, color: AppColors.slate500),
                            onPressed: () {
                              _searchController.clear();
                              setState(() {
                                _searchQuery = '';
                              });
                            },
                          )
                        : null,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 0),
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate200)),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate200)),
                  ),
                  onChanged: (val) {
                    setState(() {
                      _searchQuery = val.trim().toLowerCase();
                    });
                  },
                ),
              ),
            ),
            const SizedBox(width: 10),

            // Category Filter Dropdown
            Container(
              height: 38,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.slate200),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String?>(
                  value: _selectedCategory,
                  hint: Text('All Categories', style: AppTextStyles.bodySmall),
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate800),
                  items: const [
                    DropdownMenuItem(value: null, child: Text('All Categories')),
                    DropdownMenuItem(value: 'ARCHITECTURE_DECISION', child: Text('Architecture Decision')),
                    DropdownMenuItem(value: 'BUSINESS_RULE', child: Text('Business Rule')),
                    DropdownMenuItem(value: 'INTENT', child: Text('Intent')),
                    DropdownMenuItem(value: 'CONSTRAINT', child: Text('Constraint')),
                    DropdownMenuItem(value: 'EXCEPTION', child: Text('Exception')),
                    DropdownMenuItem(value: 'CRITICAL_COMPONENT', child: Text('Critical Component')),
                  ],
                  onChanged: (val) {
                    setState(() {
                      _selectedCategory = val;
                    });
                  },
                ),
              ),
            ),
            const SizedBox(width: 10),

            // Status Filter Dropdown
            Container(
              height: 38,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.slate200),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String?>(
                  value: _selectedStatus,
                  hint: Text('All Status', style: AppTextStyles.bodySmall),
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate800),
                  items: const [
                    DropdownMenuItem(value: null, child: Text('All Status')),
                    DropdownMenuItem(value: 'ACTIVE', child: Text('Active Only')),
                    DropdownMenuItem(value: 'ARCHIVED', child: Text('Archived Only')),
                  ],
                  onChanged: (val) {
                    setState(() {
                      _selectedStatus = val;
                    });
                  },
                ),
              ),
            ),
            const SizedBox(width: 10),

            // Add Knowledge Button
            ElevatedButton.icon(
              onPressed: _openCreateDialog,
              icon: const Icon(Icons.add, size: 14),
              label: const Text('Add Knowledge'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.slate900,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Knowledge Feed
        Expanded(
          child: knowledgeAsync.when(
            loading: () => const LoadingStateView(message: 'Loading knowledge items...'),
            error: (err, stack) => ErrorStateView(
              message: err.toString(),
              onRetry: () => ref.invalidate(projectKnowledgeListProvider),
            ),
            data: (items) {
              final filtered = items.where((item) {
                if (_searchQuery.isEmpty) return true;
                return item.title.toLowerCase().contains(_searchQuery) ||
                    item.content.toLowerCase().contains(_searchQuery) ||
                    (item.relatedFilePath?.toLowerCase().contains(_searchQuery) ?? false);
              }).toList();

              if (filtered.isEmpty) {
                return Container(
                  padding: const EdgeInsets.all(32),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.slate200),
                  ),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.lightbulb_outline, size: 36, color: AppColors.slate300),
                        const SizedBox(height: 12),
                        Text(
                          'No project knowledge items found',
                          style: AppTextStyles.h2.copyWith(fontSize: 15, color: AppColors.slate700),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Document architecture choices, constraints, or business rules to ground the engine.',
                          style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                        ),
                      ],
                    ),
                  ),
                );
              }

              return ListView.builder(
                itemCount: filtered.length,
                itemBuilder: (context, index) {
                  final item = filtered[index];
                  return KnowledgeCard(
                    item: item,
                    onEdit: () => _openEditDialog(item),
                    onArchiveOrRestore: () => _toggleArchive(item),
                    onNavigateToFile: (filePath) {
                      if (widget.onNavigateToFile != null) {
                        widget.onNavigateToFile!(filePath);
                      } else {
                        widget.onNavigateToTab?.call(3);
                      }
                    },
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }
}
