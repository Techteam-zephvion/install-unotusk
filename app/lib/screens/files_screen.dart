import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Files browser screen — shows file tree and file detail.
/// Ported feature from install-unotusk repo, using local UnoPalette UI.
class FilesScreen extends StatefulWidget {
  final UnoPalette palette;
  const FilesScreen({super.key, required this.palette});

  @override
  State<FilesScreen> createState() => _FilesScreenState();
}

class _FilesScreenState extends State<FilesScreen> {
  UnoPalette get p => widget.palette;
  List<FileNode> _fileTree = [];
  String _searchQuery = '';
  bool _loading = true;
  String? _error;
  String? _selectedFileId;
  FileDetail? _fileDetail;
  bool _loadingDetail = false;

  @override
  void initState() {
    super.initState();
    _loadFiles();
  }

  Future<void> _loadFiles() async {
    setState(() { _loading = true; _error = null; });
    try {
      final files = await ApiService.fetchProjectFiles();
      setState(() {
        _fileTree = FileNode.buildTree(files);
        _loading = false;
      });
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _onFileSelected(ProjectFile file) async {
    setState(() { _selectedFileId = file.id; _loadingDetail = true; });
    try {
      final detail = await ApiService.fetchFileDetail(file.id);
      setState(() { _fileDetail = detail; _loadingDetail = false; });
    } catch (e) {
      setState(() { _loadingDetail = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Center(child: CircularProgressIndicator(color: p.accent));
    }
    if (_error != null) {
      return Center(child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(LucideIcons.alertTriangle, size: 32, color: p.inferred),
          const SizedBox(height: 12),
          Text('Failed to load files', style: TextStyle(color: p.text, fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text(_error!, style: TextStyle(color: p.textSec, fontSize: 12), textAlign: TextAlign.center),
          const SizedBox(height: 16),
          TextButton.icon(
            onPressed: _loadFiles,
            icon: Icon(LucideIcons.refreshCcw, size: 14, color: p.accent),
            label: Text('Retry', style: TextStyle(color: p.accent, fontSize: 12)),
          ),
        ],
      ));
    }

    final filteredTree = _searchQuery.isEmpty
        ? _fileTree
        : FileNode.filterTree(_fileTree, _searchQuery);

    return Row(
      children: [
        // File tree panel
        Container(
          width: 280,
          decoration: BoxDecoration(
            color: p.bgSurface,
            border: Border(right: BorderSide(color: p.div)),
          ),
          child: Column(
            children: [
              // Search bar
              Padding(
                padding: const EdgeInsets.all(10),
                child: Container(
                  height: 32,
                  decoration: BoxDecoration(
                    color: p.bgElevated,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: p.div),
                  ),
                  child: TextField(
                    textAlignVertical: TextAlignVertical.center,
                    style: TextStyle(color: p.text, fontSize: 12),
                    decoration: InputDecoration(
                      isDense: true,
                      hintText: 'Search files…',
                      hintStyle: TextStyle(color: p.textSec, fontSize: 12),
                      prefixIcon: Icon(LucideIcons.search, size: 14, color: p.textSec),
                      prefixIconConstraints: const BoxConstraints(minWidth: 30, minHeight: 32),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.only(right: 8),
                    ),
                    onChanged: (v) => setState(() => _searchQuery = v),
                  ),
                ),
              ),
              // Tree
              Expanded(
                child: filteredTree.isEmpty
                    ? Center(child: Text('No files found', style: TextStyle(color: p.textSec, fontSize: 12)))
                    : ListView(
                        padding: const EdgeInsets.symmetric(horizontal: 6),
                        children: filteredTree.map((n) => _buildFileTreeNode(n, 0)).toList(),
                      ),
              ),
            ],
          ),
        ),
        // File detail panel
        Expanded(
          child: _selectedFileId == null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(LucideIcons.fileSearch, size: 40, color: p.div),
                      const SizedBox(height: 12),
                      Text('Select a file to view details', style: TextStyle(color: p.textSec, fontSize: 13)),
                    ],
                  ),
                )
              : _loadingDetail
                  ? Center(child: CircularProgressIndicator(color: p.accent, strokeWidth: 2))
                  : _fileDetail != null
                      ? _buildFileDetail(_fileDetail!)
                      : Center(child: Text('No details', style: TextStyle(color: p.textSec))),
        ),
      ],
    );
  }

  Widget _buildFileTreeNode(FileNode node, int depth) {
    final isSelected = !node.isDirectory && node.file?.id == _selectedFileId;
    if (node.isDirectory) {
      return _DirectoryNode(
        node: node,
        depth: depth,
        palette: p,
        selectedFileId: _selectedFileId,
        onFileSelected: _onFileSelected,
      );
    }

    return InkWell(
      onTap: () => node.file != null ? _onFileSelected(node.file!) : null,
      child: Container(
        padding: EdgeInsets.only(left: 12.0 + depth * 16, right: 8, top: 4, bottom: 4),
        decoration: BoxDecoration(
          color: isSelected ? p.accent.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          children: [
            Icon(_fileIcon(node.name), size: 14, color: isSelected ? p.accent : p.textSec),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                node.name,
                style: TextStyle(
                  color: isSelected ? p.accent : p.text,
                  fontSize: 12,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (node.file != null)
              Text(
                '${node.file!.lineCount}L',
                style: TextStyle(color: p.textSec, fontSize: 10),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildFileDetail(FileDetail detail) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // File header
          Row(
            children: [
              Icon(_fileIcon(detail.file.filename), size: 18, color: p.accent),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(detail.file.filename, style: TextStyle(color: p.text, fontSize: 15, fontWeight: FontWeight.w600)),
                    Text(detail.file.path, style: TextStyle(color: p.textSec, fontSize: 11)),
                  ],
                ),
              ),
              _chip(detail.file.language, p.accent),
            ],
          ),
          const SizedBox(height: 16),

          // Metrics row
          Wrap(
            spacing: 12,
            children: [
              _metricBadge('Lines', '${detail.file.lineCount}'),
              _metricBadge('Size', '${(detail.file.sizeBytes / 1024).toStringAsFixed(1)} KB'),
              _metricBadge('Symbols', '${detail.symbols.length}'),
              _metricBadge('Deps Out', '${detail.outgoingDependencies.length}'),
              _metricBadge('Refs In', '${detail.incomingReferences.length}'),
              if (detail.file.isTest) _metricBadge('Test', '✓', color: p.live),
            ],
          ),
          const SizedBox(height: 20),

          // Symbols section
          if (detail.symbols.isNotEmpty) ...[
            Text('Symbols', style: TextStyle(color: p.text, fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            ...detail.symbols.map((s) => Container(
              margin: const EdgeInsets.only(bottom: 4),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: p.bgElevated,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: p.div),
              ),
              child: Row(
                children: [
                  _chip(s.symbolType, p.neutral),
                  const SizedBox(width: 8),
                  Expanded(child: Text(s.name, style: TextStyle(color: p.text, fontSize: 12, fontFamily: 'JetBrains Mono'))),
                  Text('L${s.startLine}–${s.endLine}', style: TextStyle(color: p.textSec, fontSize: 10)),
                ],
              ),
            )),
            const SizedBox(height: 20),
          ],

          // Code content
          if (detail.fullContent != null) ...[
            Text('Source Code', style: TextStyle(color: p.text, fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: p.bgBase,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: p.div),
              ),
              child: SelectableText(
                detail.fullContent!,
                style: TextStyle(color: p.text, fontSize: 11, fontFamily: 'JetBrains Mono', height: 1.5),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _metricBadge(String label, String value, {Color? color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: p.bgElevated,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: p.div),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: TextStyle(color: p.textSec, fontSize: 10)),
          const SizedBox(width: 4),
          Text(value, style: TextStyle(color: color ?? p.text, fontSize: 11, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  Widget _chip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(3),
      ),
      child: Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600)),
    );
  }

  IconData _fileIcon(String name) {
    if (name.endsWith('.dart')) return LucideIcons.fileCode;
    if (name.endsWith('.py')) return LucideIcons.fileCode;
    if (name.endsWith('.js') || name.endsWith('.ts')) return LucideIcons.fileCode;
    if (name.endsWith('.json')) return LucideIcons.fileJson;
    if (name.endsWith('.yaml') || name.endsWith('.yml')) return LucideIcons.fileText;
    if (name.endsWith('.md')) return LucideIcons.fileText;
    return LucideIcons.file;
  }
}

class _DirectoryNode extends StatefulWidget {
  final FileNode node;
  final int depth;
  final UnoPalette palette;
  final String? selectedFileId;
  final Function(ProjectFile) onFileSelected;

  const _DirectoryNode({
    required this.node,
    required this.depth,
    required this.palette,
    required this.selectedFileId,
    required this.onFileSelected,
  });

  @override
  State<_DirectoryNode> createState() => _DirectoryNodeState();
}

class _DirectoryNodeState extends State<_DirectoryNode> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InkWell(
          onTap: () => setState(() => _expanded = !_expanded),
          child: Container(
            padding: EdgeInsets.only(left: 12.0 + widget.depth * 16, right: 8, top: 4, bottom: 4),
            child: Row(
              children: [
                Icon(_expanded ? LucideIcons.chevronDown : LucideIcons.chevronRight, size: 12, color: p.textSec),
                const SizedBox(width: 4),
                Icon(LucideIcons.folder, size: 14, color: p.accent.withValues(alpha: 0.7)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(widget.node.name, style: TextStyle(color: p.text, fontSize: 12, fontWeight: FontWeight.w500)),
                ),
                Text('${widget.node.children.length}', style: TextStyle(color: p.textSec, fontSize: 10)),
              ],
            ),
          ),
        ),
        if (_expanded)
          ...widget.node.children.map((child) {
            if (child.isDirectory) {
              return _DirectoryNode(
                node: child,
                depth: widget.depth + 1,
                palette: p,
                selectedFileId: widget.selectedFileId,
                onFileSelected: widget.onFileSelected,
              );
            }
            final isSelected = child.file?.id == widget.selectedFileId;
            return InkWell(
              onTap: () => child.file != null ? widget.onFileSelected(child.file!) : null,
              child: Container(
                padding: EdgeInsets.only(left: 12.0 + (widget.depth + 1) * 16, right: 8, top: 4, bottom: 4),
                decoration: BoxDecoration(
                  color: isSelected ? p.accent.withValues(alpha: 0.12) : Colors.transparent,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  children: [
                    Icon(LucideIcons.file, size: 14, color: isSelected ? p.accent : p.textSec),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(child.name,
                          style: TextStyle(color: isSelected ? p.accent : p.text, fontSize: 12,
                              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400),
                          overflow: TextOverflow.ellipsis),
                    ),
                  ],
                ),
              ),
            );
          }),
      ],
    );
  }
}
