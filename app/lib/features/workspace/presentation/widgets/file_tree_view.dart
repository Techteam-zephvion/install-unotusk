import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/file_node.dart';
import '../../domain/project_file.dart';

class FileTreeView extends StatefulWidget {
  final List<FileNode> rootNodes;
  final String? selectedFileId;
  final ValueChanged<ProjectFile> onSelectFile;

  const FileTreeView({
    super.key,
    required this.rootNodes,
    this.selectedFileId,
    required this.onSelectFile,
  });

  @override
  State<FileTreeView> createState() => _FileTreeViewState();
}

class _FileTreeViewState extends State<FileTreeView> {
  final Set<String> _collapsedPaths = {};

  void _toggleDirectory(String path) {
    setState(() {
      if (_collapsedPaths.contains(path)) {
        _collapsedPaths.remove(path);
      } else {
        _collapsedPaths.add(path);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (widget.rootNodes.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(32),
        alignment: Alignment.center,
        child: Text(
          'No files found matching criteria.',
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate500),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      children: widget.rootNodes
          .map((node) => _buildNode(node, depth: 0))
          .toList(),
    );
  }

  Widget _buildNode(FileNode node, {required int depth}) {
    if (node.isDirectory) {
      final isCollapsed = _collapsedPaths.contains(node.path);

      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Directory Row
          InkWell(
            onTap: () => _toggleDirectory(node.path),
            borderRadius: BorderRadius.circular(4),
            child: Padding(
              padding: EdgeInsets.only(
                left: 12.0 + (depth * 18.0),
                right: 12.0,
                top: 6.0,
                bottom: 6.0,
              ),
              child: Row(
                children: [
                  Icon(
                    isCollapsed ? Icons.chevron_right : Icons.expand_more,
                    size: 16,
                    color: AppColors.slate500,
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    isCollapsed ? Icons.folder_outlined : Icons.folder_open_outlined,
                    size: 16,
                    color: AppColors.slate700,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    node.name,
                    style: AppTextStyles.bodyMedium.copyWith(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppColors.slate900,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '(${node.children.length})',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontSize: 11,
                      color: AppColors.slate400,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Children
          if (!isCollapsed)
            ...node.children.map((child) => _buildNode(child, depth: depth + 1)),
        ],
      );
    } else {
      final file = node.file!;
      final isSelected = widget.selectedFileId == file.id;

      return Container(
        margin: const EdgeInsets.symmetric(vertical: 1, horizontal: 4),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.accentMuted : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: isSelected ? Border.all(color: AppColors.accent.withOpacity(0.4)) : null,
        ),
        child: InkWell(
          onTap: () => widget.onSelectFile(file),
          borderRadius: BorderRadius.circular(6),
          child: Padding(
            padding: EdgeInsets.only(
              left: 12.0 + (depth * 18.0) + 20.0, // align with folder contents
              right: 12.0,
              top: 6.0,
              bottom: 6.0,
            ),
            child: Row(
              children: [
                Icon(
                  Icons.insert_drive_file_outlined,
                  size: 14,
                  color: isSelected ? AppColors.accent : AppColors.textSecondary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    node.name,
                    style: AppTextStyles.bodyMedium.copyWith(
                      fontSize: 13,
                      color: isSelected ? AppColors.textPrimary : AppColors.textSecondary,
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (file.isTest) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    margin: const EdgeInsets.only(right: 6),
                    decoration: BoxDecoration(
                      color: AppColors.slate200,
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      'TEST',
                      style: AppTextStyles.bodySmall.copyWith(
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        color: AppColors.slate700,
                      ),
                    ),
                  ),
                ],
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: AppColors.slate100,
                    borderRadius: BorderRadius.circular(3),
                  ),
                  child: Text(
                    file.extension.isNotEmpty ? file.extension : file.language,
                    style: AppTextStyles.code.copyWith(
                      fontSize: 10,
                      color: AppColors.slate600,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  '${file.lineCount} lines',
                  style: AppTextStyles.bodySmall.copyWith(
                    fontSize: 11,
                    color: AppColors.slate400,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }
  }
}
