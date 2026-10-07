import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../core/widgets/error_state_view.dart';
import '../../../../core/widgets/loading_state_view.dart';
import '../../domain/component_node.dart';
import '../widgets/file_search_bar.dart';
import '../workspace_controller.dart';

class ArchitectureTab extends ConsumerStatefulWidget {
  final String projectId;
  final String projectName;
  final void Function(int tabIndex)? onNavigateToTab;
  final ValueChanged<String>? onNavigateToFile;

  const ArchitectureTab({
    super.key,
    required this.projectId,
    required this.projectName,
    this.onNavigateToTab,
    this.onNavigateToFile,
  });

  @override
  ConsumerState<ArchitectureTab> createState() => _ArchitectureTabState();
}

class _ArchitectureTabState extends ConsumerState<ArchitectureTab> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  ComponentNode? _selectedComponent;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final depsAsync = ref.watch(projectDependenciesProvider(widget.projectId));
    final filesAsync = ref.watch(projectFilesProvider(widget.projectId));

    if (depsAsync.isLoading || filesAsync.isLoading) {
      return const LoadingStateView(message: 'Mapping component relationships...');
    }

    if (depsAsync.hasError) {
      return ErrorStateView(
        message: depsAsync.error.toString(),
        onRetry: () {
          ref.invalidate(projectDependenciesProvider(widget.projectId));
          ref.invalidate(projectFilesProvider(widget.projectId));
        },
      );
    }

    final deps = depsAsync.value ?? [];
    final files = filesAsync.value ?? [];
    final allComponents = ComponentNode.aggregateComponents(
      dependencies: deps,
      files: files,
    );

    final filteredComponents = _searchQuery.trim().isEmpty
        ? allComponents
        : allComponents.where((c) {
            final q = _searchQuery.toLowerCase().trim();
            return c.name.toLowerCase().contains(q) || c.path.toLowerCase().contains(q);
          }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header & Search
        Row(
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Component Relationships',
                  style: AppTextStyles.h2.copyWith(fontSize: 16, color: AppColors.slate900),
                ),
                const SizedBox(height: 2),
                Text(
                  '${allComponents.length} components • ${deps.length} dependency edges',
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                ),
              ],
            ),
            const Spacer(),
            SizedBox(
              width: 320,
              child: FileSearchBar(
                controller: _searchController,
                hintText: 'Filter components by name...',
                onChanged: (q) => setState(() => _searchQuery = q),
                onClear: () => setState(() => _searchQuery = ''),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Split Pane
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Left List of Components
              Expanded(
                flex: 4,
                child: Material(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.slate200),
                    ),
                    child: filteredComponents.isEmpty
                        ? Center(
                            child: Text(
                              'No components found.',
                              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate500),
                            ),
                          )
                        : ListView.separated(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            itemCount: filteredComponents.length,
                            separatorBuilder: (c, i) => const Divider(height: 1, color: AppColors.slate100),
                            itemBuilder: (context, index) {
                              final comp = filteredComponents[index];
                              final isSelected = _selectedComponent?.path == comp.path;

                              return InkWell(
                                onTap: () {
                                  setState(() {
                                    _selectedComponent = comp;
                                  });
                                },
                                child: Container(
                                  color: isSelected ? AppColors.slate100 : Colors.transparent,
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                                  child: Row(
                                    children: [
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              comp.name,
                                              style: AppTextStyles.bodyMedium.copyWith(
                                                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                                                color: AppColors.slate900,
                                              ),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              comp.path,
                                              style: AppTextStyles.code.copyWith(
                                                fontSize: 11,
                                                color: AppColors.slate500,
                                              ),
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ],
                                        ),
                                      ),
                                      if (comp.callerCount > 0) ...[
                                        const SizedBox(width: 8),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: AppColors.slate200,
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            '${comp.callerCount} callers',
                                            style: AppTextStyles.bodySmall.copyWith(
                                              fontSize: 10,
                                              fontWeight: FontWeight.w600,
                                              color: AppColors.slate700,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                  ),
                ),
              ),
              const SizedBox(width: 16),

              // Right Relationship Inspector
              Expanded(
                flex: 6,
                child: _selectedComponent != null
                    ? _buildRelationshipInspector(_selectedComponent!)
                    : Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.slate200),
                        ),
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.account_tree_outlined,
                                size: 36,
                                color: AppColors.slate300,
                              ),
                              const SizedBox(height: 12),
                              Text(
                                'Select a component to inspect relationships',
                                style: AppTextStyles.h2.copyWith(fontSize: 15, color: AppColors.slate700),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Examine caller references and downstream dependencies.',
                                style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                              ),
                            ],
                          ),
                        ),
                      ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRelationshipInspector(ComponentNode comp) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.slate200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.slate200)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          comp.name,
                          style: AppTextStyles.h2.copyWith(fontSize: 16, color: AppColors.slate900),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          comp.path,
                          style: AppTextStyles.code.copyWith(
                            fontSize: 12,
                            color: AppColors.slate500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: () {
                      if (widget.onNavigateToFile != null) {
                        widget.onNavigateToFile!(comp.path);
                      } else {
                        widget.onNavigateToTab?.call(3);
                      }
                    },
                    icon: const Icon(Icons.folder_open, size: 14),
                    label: const Text('Open in Files'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.slate900,
                      side: const BorderSide(color: AppColors.slate300),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                  ),
                ],
              ),
            ),

            // Content: Used by & Depends on
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  // Used by
                  Row(
                    children: [
                      Text(
                        'Used by',
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.slate900,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.slate100,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '${comp.incomingCallers.length} files',
                          style: AppTextStyles.bodySmall.copyWith(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.slate700,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  if (comp.incomingCallers.isEmpty)
                    Text(
                      'No other components directly depend on this module.',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                    )
                  else
                    ...comp.incomingCallers.map((dep) {
                      final callerPath = dep.sourcePath ?? 'Unknown file';
                      return InkWell(
                        onTap: dep.sourcePath != null && widget.onNavigateToFile != null
                            ? () => widget.onNavigateToFile!(dep.sourcePath!)
                            : null,
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 6),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppColors.slate50,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: AppColors.slate200),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.subdirectory_arrow_right, size: 14, color: AppColors.slate500),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  callerPath,
                                  style: AppTextStyles.code.copyWith(
                                    fontSize: 12,
                                    color: widget.onNavigateToFile != null ? AppColors.primary : AppColors.slate800,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              Text(
                                'line ${dep.lineNumber}',
                                style: AppTextStyles.bodySmall.copyWith(
                                  fontSize: 11,
                                  color: AppColors.slate400,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }),

                  const Divider(height: 32, color: AppColors.slate200),

                  // Depends on
                  Row(
                    children: [
                      Text(
                        'Depends on',
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.slate900,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.slate100,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '${comp.outgoingDependencies.length} imports',
                          style: AppTextStyles.bodySmall.copyWith(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.slate700,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  if (comp.outgoingDependencies.isEmpty)
                    Text(
                      'No internal or external dependencies.',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                    )
                  else
                    ...comp.outgoingDependencies.map((dep) {
                      final target = dep.targetPath ?? dep.externalPackage ?? 'Unknown target';
                      final isExternal = dep.externalPackage != null;

                      return InkWell(
                        onTap: !isExternal && dep.targetPath != null && widget.onNavigateToFile != null
                            ? () => widget.onNavigateToFile!(dep.targetPath!)
                            : null,
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 6),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppColors.slate50,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: AppColors.slate200),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                isExternal ? Icons.public : Icons.arrow_forward,
                                size: 14,
                                color: AppColors.slate500,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  target,
                                  style: AppTextStyles.code.copyWith(
                                    fontSize: 12,
                                    color: !isExternal && widget.onNavigateToFile != null ? AppColors.primary : AppColors.slate800,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              if (isExternal) ...[
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                                  margin: const EdgeInsets.only(right: 8),
                                  decoration: BoxDecoration(
                                    color: AppColors.slate200,
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  child: Text(
                                    'EXTERNAL',
                                    style: AppTextStyles.bodySmall.copyWith(fontSize: 9, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              ],
                              Text(
                                'line ${dep.lineNumber}',
                                style: AppTextStyles.bodySmall.copyWith(
                                  fontSize: 11,
                                  color: AppColors.slate400,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
