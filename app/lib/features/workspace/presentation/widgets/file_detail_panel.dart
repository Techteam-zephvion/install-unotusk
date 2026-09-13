import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../core/widgets/error_state_view.dart';
import '../../../../core/widgets/loading_state_view.dart';
import '../../domain/project_file.dart';
import '../../domain/project_symbol.dart';
import '../workspace_controller.dart';
import 'code_viewer.dart';

class FileDetailPanel extends ConsumerStatefulWidget {
  final String projectId;
  final ProjectFile file;
  final VoidCallback onClose;
  final ValueChanged<String>? onNavigateToFile;
  final int? initialHighlightStartLine;
  final int? initialHighlightEndLine;

  const FileDetailPanel({
    super.key,
    required this.projectId,
    required this.file,
    required this.onClose,
    this.onNavigateToFile,
    this.initialHighlightStartLine,
    this.initialHighlightEndLine,
  });

  @override
  ConsumerState<FileDetailPanel> createState() => _FileDetailPanelState();
}

class _FileDetailPanelState extends ConsumerState<FileDetailPanel> {
  int _activeSegmentIndex = 0; // 0: Code, 1: Symbols, 2: Dependencies
  int? _highlightStartLine;
  int? _highlightEndLine;

  @override
  void initState() {
    super.initState();
    _highlightStartLine = widget.initialHighlightStartLine;
    _highlightEndLine = widget.initialHighlightEndLine;
  }

  @override
  void didUpdateWidget(covariant FileDetailPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.file.id != widget.file.id ||
        oldWidget.initialHighlightStartLine != widget.initialHighlightStartLine ||
        oldWidget.initialHighlightEndLine != widget.initialHighlightEndLine) {
      _highlightStartLine = widget.initialHighlightStartLine;
      _highlightEndLine = widget.initialHighlightEndLine;
    }
  }

  void _jumpToSymbol(ProjectSymbol symbol) {
    setState(() {
      _highlightStartLine = symbol.startLine;
      _highlightEndLine = symbol.endLine;
      _activeSegmentIndex = 0; // Switch to Code view to see the highlighted symbol
    });
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(
      projectFileDetailProvider((projectId: widget.projectId, fileId: widget.file.id)),
    );

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
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppColors.slate200)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            widget.file.filename,
                            style: AppTextStyles.bodyMedium.copyWith(
                              fontWeight: FontWeight.w600,
                              color: AppColors.slate900,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: AppColors.slate100,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              widget.file.language,
                              style: AppTextStyles.bodySmall.copyWith(
                                fontSize: 10,
                                fontWeight: FontWeight.w500,
                                color: AppColors.slate600,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        widget.file.path,
                        style: AppTextStyles.code.copyWith(
                          fontSize: 11,
                          color: AppColors.slate500,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close, size: 16, color: AppColors.slate500),
                  onPressed: widget.onClose,
                  tooltip: 'Close Inspector',
                ),
              ],
            ),
          ),

          // Segment Selector Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: const BoxDecoration(
              color: AppColors.slate50,
              border: Border(bottom: BorderSide(color: AppColors.slate200)),
            ),
            child: Row(
              children: [
                _buildSegmentButton('Code', 0),
                const SizedBox(width: 8),
                _buildSegmentButton('Symbols', 1),
                const SizedBox(width: 8),
                _buildSegmentButton('Dependencies', 2),
              ],
            ),
          ),

          // Content Area
          Expanded(
            child: detailAsync.when(
              loading: () => const LoadingStateView(message: 'Loading structure and code...'),
              error: (err, stack) => ErrorStateView(
                message: err.toString(),
                onRetry: () => ref.invalidate(
                  projectFileDetailProvider((projectId: widget.projectId, fileId: widget.file.id)),
                ),
              ),
              data: (detail) {
                if (_activeSegmentIndex == 0) {
                  // Code View
                  final codeText = detail.fullContent ??
                      (detail.chunks.isNotEmpty
                          ? detail.chunks.map((c) => c.content).join('\n\n')
                          : '# Source code content not cached in local snapshot');

                  return Padding(
                    padding: const EdgeInsets.all(12),
                    child: CodeViewer(
                      code: codeText,
                      highlightStartLine: _highlightStartLine,
                      highlightEndLine: _highlightEndLine,
                    ),
                  );
                } else if (_activeSegmentIndex == 1) {
                  // Symbols View
                  if (detail.symbols.isEmpty) {
                    return Center(
                      child: Text(
                        'No symbols parsed in this file.',
                        style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate500),
                      ),
                    );
                  }

                  return ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: detail.symbols.length,
                    separatorBuilder: (c, i) => const Divider(height: 1, color: AppColors.slate100),
                    itemBuilder: (context, index) {
                      final sym = detail.symbols[index];
                      return ListTile(
                        dense: true,
                        title: Text(
                          sym.name,
                          style: AppTextStyles.bodyMedium.copyWith(
                            fontWeight: FontWeight.w600,
                            color: AppColors.slate900,
                          ),
                        ),
                        subtitle: Text(
                          sym.qualifiedName,
                          style: AppTextStyles.code.copyWith(
                            fontSize: 11,
                            color: AppColors.slate600,
                          ),
                        ),
                        trailing: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.slate100,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'L${sym.startLine}-${sym.endLine}',
                            style: AppTextStyles.bodySmall.copyWith(
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                              color: AppColors.slate700,
                            ),
                          ),
                        ),
                        onTap: () => _jumpToSymbol(sym),
                      );
                    },
                  );
                } else {
                  // Dependencies View
                  return ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      // Outgoing Dependencies
                      Text(
                        'Depends on (${detail.outgoingDependencies.length})',
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.slate900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      if (detail.outgoingDependencies.isEmpty)
                        Text('No outgoing dependencies', style: AppTextStyles.bodySmall)
                      else
                        ...detail.outgoingDependencies.map((dep) {
                          final label = dep.targetPath ?? dep.externalPackage ?? 'Unknown target';
                          final isInternalFile = dep.targetPath != null;

                          return InkWell(
                            onTap: isInternalFile && widget.onNavigateToFile != null
                                ? () => widget.onNavigateToFile!(dep.targetPath!)
                                : null,
                            borderRadius: BorderRadius.circular(4),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
                              child: Row(
                                children: [
                                  const Icon(Icons.arrow_forward, size: 14, color: AppColors.slate400),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      label,
                                      style: AppTextStyles.code.copyWith(
                                        fontSize: 12,
                                        color: isInternalFile ? AppColors.primary : AppColors.slate800,
                                        decoration: isInternalFile ? TextDecoration.underline : TextDecoration.none,
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
                      const Divider(height: 28, color: AppColors.slate200),

                      // Incoming References (Used By)
                      Text(
                        'Used by (${detail.incomingReferences.length} files)',
                        style: AppTextStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.slate900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      if (detail.incomingReferences.isEmpty)
                        Text('No incoming references recorded', style: AppTextStyles.bodySmall)
                      else
                        ...detail.incomingReferences.map((ref) {
                          final sourcePath = ref.sourcePath ?? 'Unknown file';
                          return InkWell(
                            onTap: ref.sourcePath != null && widget.onNavigateToFile != null
                                ? () => widget.onNavigateToFile!(ref.sourcePath!)
                                : null,
                            borderRadius: BorderRadius.circular(4),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
                              child: Row(
                                children: [
                                  const Icon(Icons.subdirectory_arrow_right, size: 14, color: AppColors.slate400),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      sourcePath,
                                      style: AppTextStyles.code.copyWith(
                                        fontSize: 12,
                                        color: AppColors.primary,
                                        decoration: TextDecoration.underline,
                                      ),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  Text(
                                    'line ${ref.lineNumber}',
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
                  );
                }
              },
            ),
          ),
        ],
      ),
    ),
    );
  }

  Widget _buildSegmentButton(String title, int index) {
    final isSelected = _activeSegmentIndex == index;
    return InkWell(
      onTap: () {
        setState(() {
          _activeSegmentIndex = index;
        });
      },
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.slate900 : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          title,
          style: AppTextStyles.bodySmall.copyWith(
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
            color: isSelected ? Colors.white : AppColors.slate700,
          ),
        ),
      ),
    );
  }
}
