import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../core/widgets/error_state_view.dart';
import '../../../../core/widgets/loading_state_view.dart';
import '../../domain/file_node.dart';
import '../../domain/project_file.dart';
import '../widgets/file_detail_panel.dart';
import '../widgets/file_search_bar.dart';
import '../widgets/file_tree_view.dart';
import '../workspace_controller.dart';

class FilesTab extends ConsumerStatefulWidget {
  final String projectId;
  final String projectName;
  final String? initialSelectedFilePath;
  final String? initialHighlightLines;
  final ValueChanged<ProjectFile>? onSelectFile;

  const FilesTab({
    super.key,
    required this.projectId,
    required this.projectName,
    this.initialSelectedFilePath,
    this.initialHighlightLines,
    this.onSelectFile,
  });

  @override
  ConsumerState<FilesTab> createState() => _FilesTabState();
}

class _FilesTabState extends ConsumerState<FilesTab> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  ProjectFile? _selectedFile;
  int? _highlightStartLine;
  int? _highlightEndLine;

  @override
  void initState() {
    super.initState();
    _parseHighlightLines(widget.initialHighlightLines);
  }

  @override
  void didUpdateWidget(covariant FilesTab oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialHighlightLines != widget.initialHighlightLines) {
      _parseHighlightLines(widget.initialHighlightLines);
    }
    if (oldWidget.initialSelectedFilePath != widget.initialSelectedFilePath) {
      _selectedFile = null;
    }
  }

  void _parseHighlightLines(String? lineRange) {
    if (lineRange == null || lineRange.isEmpty) {
      _highlightStartLine = null;
      _highlightEndLine = null;
      return;
    }
    final parts = lineRange.split('-');
    if (parts.length == 2) {
      _highlightStartLine = int.tryParse(parts[0]);
      _highlightEndLine = int.tryParse(parts[1]);
    } else if (parts.length == 1) {
      _highlightStartLine = int.tryParse(parts[0]);
      _highlightEndLine = _highlightStartLine;
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filesAsync = ref.watch(projectFilesProvider(widget.projectId));

    return filesAsync.when(
      loading: () => const LoadingStateView(message: 'Loading project files...'),
      error: (err, stack) => ErrorStateView(
        message: err.toString(),
        onRetry: () => ref.invalidate(projectFilesProvider(widget.projectId)),
      ),
      data: (files) {
        if (_selectedFile == null && widget.initialSelectedFilePath != null) {
          final match = files.where((f) =>
              f.path == widget.initialSelectedFilePath ||
              f.path.endsWith(widget.initialSelectedFilePath!) ||
              widget.initialSelectedFilePath!.endsWith(f.path)).firstOrNull;
          if (match != null) {
            _selectedFile = match;
          }
        }

        final treeNodes = FileNode.buildTree(files);
        final filteredNodes = FileNode.filterTree(treeNodes, _searchQuery);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Bar & Search Controls
            Row(
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Project Files',
                      style: AppTextStyles.h2.copyWith(fontSize: 16, color: AppColors.slate900),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${files.length} files tracked in current snapshot',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                    ),
                  ],
                ),
                const Spacer(),
                SizedBox(
                  width: 320,
                  child: FileSearchBar(
                    controller: _searchController,
                    onChanged: (query) {
                      setState(() {
                        _searchQuery = query;
                      });
                    },
                    onClear: () {
                      setState(() {
                        _searchQuery = '';
                      });
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Main Split Pane: Left Tree | Right Detail Inspector
            Expanded(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left Pane: File Tree
                  Expanded(
                    flex: 4,
                    child: Container(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.slate200),
                      ),
                      child: FileTreeView(
                        rootNodes: filteredNodes,
                        selectedFileId: _selectedFile?.id,
                        onSelectFile: (file) {
                          setState(() {
                            _selectedFile = file;
                          });
                          widget.onSelectFile?.call(file);
                        },
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),

                  // Right Pane: Detail Inspector or Empty Prompt
                  Expanded(
                    flex: 6,
                    child: _selectedFile != null
                        ? FileDetailPanel(
                            projectId: widget.projectId,
                            file: _selectedFile!,
                            initialHighlightStartLine: _highlightStartLine,
                            initialHighlightEndLine: _highlightEndLine,
                            onNavigateToFile: (filePath) {
                              final match = files.where((f) =>
                                  f.path == filePath ||
                                  f.path.endsWith(filePath) ||
                                  filePath.endsWith(f.path)).firstOrNull;
                              if (match != null) {
                                setState(() {
                                  _selectedFile = match;
                                  _highlightStartLine = null;
                                  _highlightEndLine = null;
                                });
                              }
                            },
                            onClose: () {
                              setState(() {
                                _selectedFile = null;
                              });
                            },
                          )
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
                                    Icons.code_outlined,
                                    size: 36,
                                    color: AppColors.slate300,
                                  ),
                                  const SizedBox(height: 12),
                                  Text(
                                    'Select a file to inspect',
                                    style: AppTextStyles.h2.copyWith(
                                      fontSize: 15,
                                      color: AppColors.slate700,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'View code structure, symbols, imports, and component callers.',
                                    style: AppTextStyles.bodySmall.copyWith(
                                      color: AppColors.slate400,
                                    ),
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
      },
    );
  }
}
