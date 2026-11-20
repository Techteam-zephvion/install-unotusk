import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/markdown_text.dart';

/// Content viewer modes supported by the Files browser
enum FileContentViewMode {
  rendered,
  source,
  symbols,
  dependencies,
}

/// Files browser screen — provides a structured, modern file explorer
/// and an editorial file detail panel with compilers/converters for Markdown,
/// formatted JSON, syntax-highlighted code, and AST symbol inspection.
class FilesScreen extends StatefulWidget {
  final UnoPalette palette;
  final String? initialFilePath;
  final int? initialLine;

  const FilesScreen({
    super.key,
    required this.palette,
    this.initialFilePath,
    this.initialLine,
  });

  @override
  State<FilesScreen> createState() => _FilesScreenState();
}

class _FilesScreenState extends State<FilesScreen> {
  UnoPalette get p => widget.palette;
  bool get isDark => p.isDark;

  List<ProjectFile> _rawFiles = [];
  List<FileNode> _fileTree = [];
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _codeVerticalScrollController = ScrollController();
  bool _loading = true;
  String? _error;

  String? _selectedFileId;
  FileDetail? _fileDetail;
  bool _loadingDetail = false;
  int? _targetLine;

  FileContentViewMode _viewMode = FileContentViewMode.rendered;
  final bool _wrapLines = false;
  final bool _showLineNumbers = true;
  bool _copied = false;
  String _symbolFilter = '';

  @override
  void initState() {
    super.initState();
    _targetLine = widget.initialLine;
    _loadFiles();
  }

  @override
  void didUpdateWidget(covariant FilesScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialFilePath != oldWidget.initialFilePath ||
        widget.initialLine != oldWidget.initialLine) {
      _targetLine = widget.initialLine;
      if (widget.initialFilePath != null && _rawFiles.isNotEmpty) {
        _locateAndSelectFile(widget.initialFilePath!, targetLine: widget.initialLine);
      }
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _codeVerticalScrollController.dispose();
    super.dispose();
  }

  void _locateAndSelectFile(String targetPath, {int? targetLine}) {
    final target = targetPath.toLowerCase().replaceAll('\\', '/').trim();
    final matched = _rawFiles.where((f) {
      final p = f.path.toLowerCase().replaceAll('\\', '/');
      return p == target || p.endsWith(target) || target.endsWith(p);
    }).firstOrNull;

    if (matched != null) {
      _onFileSelected(matched, targetLine: targetLine);
    }
  }

  Future<void> _loadFiles() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final files = await ApiService.fetchProjectFiles();
      if (!mounted) return;
      setState(() {
        _rawFiles = files;
        _fileTree = FileNode.buildTree(files);
        _loading = false;
      });

      if (widget.initialFilePath != null && widget.initialFilePath!.isNotEmpty) {
        _locateAndSelectFile(widget.initialFilePath!, targetLine: widget.initialLine);
      } else if (_selectedFileId == null && files.isNotEmpty) {
        final readme = files
            .where((f) => f.filename.toLowerCase().startsWith('readme'))
            .firstOrNull;
        _onFileSelected(readme ?? files.first);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _onFileSelected(ProjectFile file, {int? targetLine}) async {
    final ext = file.extension.toLowerCase();
    final isCodeOrTarget = targetLine != null && targetLine > 0;
    final defaultMode = isCodeOrTarget
        ? FileContentViewMode.source
        : ((ext == '.md' || ext == '.markdown' || ext == '.json' || ext == '.svg')
            ? FileContentViewMode.rendered
            : FileContentViewMode.source);

    setState(() {
      _selectedFileId = file.id;
      _loadingDetail = true;
      _viewMode = defaultMode;
      _copied = false;
      _symbolFilter = '';
      _targetLine = targetLine;
    });

    try {
      final detail = await ApiService.fetchFileDetail(file.id);
      if (!mounted) return;
      setState(() {
        _fileDetail = detail;
        _loadingDetail = false;
      });

      // If targetLine is set, smoothly auto-scroll code viewer to that line
      if (targetLine != null && targetLine > 0) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_codeVerticalScrollController.hasClients) {
            final targetOffset = math.max(0.0, (targetLine - 3) * 20.0);
            _codeVerticalScrollController.animateTo(
              targetOffset,
              duration: const Duration(milliseconds: 350),
              curve: Curves.easeOutCubic,
            );
          }
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingDetail = false;
      });
    }
  }

  void _copyContent(String content) {
    Clipboard.setData(ClipboardData(text: content));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(
                color: p.accent,
                strokeWidth: 2.5,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              'Loading repository files…',
              style: TextStyle(
                color: p.textSec,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 420),
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: p.bgElevated,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: p.div),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: p.inferred.withValues(alpha: 0.15),
                ),
                child: Center(
                  child: Icon(LucideIcons.alertTriangle, size: 24, color: p.inferred),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Failed to load files',
                style: TextStyle(
                  color: p.text,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _error!,
                style: TextStyle(color: p.textSec, fontSize: 12, height: 1.4),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _loadFiles,
                icon: const Icon(LucideIcons.refreshCcw, size: 14),
                label: const Text('Try Again', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: p.accent,
                  foregroundColor: isDark ? const Color(0xFF0B1020) : Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final filteredTree = _searchQuery.isEmpty
        ? _fileTree
        : FileNode.filterTree(_fileTree, _searchQuery);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── Left File Explorer Tree Panel ──
        Container(
          width: 300,
          decoration: BoxDecoration(
            gradient: p.sidebarGradient,
            border: Border(
              right: BorderSide(color: p.div.withValues(alpha: 0.8)),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Explorer Header & Filter
              _buildExplorerHeader(),

              // Tree view
              Expanded(
                child: filteredTree.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(LucideIcons.searchX, size: 28, color: p.div),
                            const SizedBox(height: 10),
                            Text(
                              'No matching files',
                              style: TextStyle(color: p.textSec, fontSize: 12, fontWeight: FontWeight.w500),
                            ),
                          ],
                        ),
                      )
                    : ListView(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                        children: filteredTree.map((n) => _buildFileTreeNode(n, 0)).toList(),
                      ),
              ),

              // Bottom status bar
              _buildExplorerFooter(),
            ],
          ),
        ),

        // ── Right File Detail & Content Panel ──
        Expanded(
          child: Container(
            color: p.bgBase,
            child: _selectedFileId == null
                ? _buildEmptyState()
                : _loadingDetail
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(color: p.accent, strokeWidth: 2.2),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'Reading file contents…',
                              style: TextStyle(color: p.textSec, fontSize: 12),
                            ),
                          ],
                        ),
                      )
                    : _fileDetail != null
                        ? _buildFileDetailView(_fileDetail!)
                        : _buildEmptyState(),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Explorer Header & Search Field
  // ─────────────────────────────────────────────────────────
  Widget _buildExplorerHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: p.div.withValues(alpha: 0.6))),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(LucideIcons.folderGit2, size: 15, color: p.accent),
              const SizedBox(width: 8),
              Text(
                'PROJECT FILES',
                style: TextStyle(
                  color: p.accent,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E2840) : const Color(0xFFE8E3D8),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  '${_rawFiles.length}',
                  style: TextStyle(
                    color: isDark ? p.text : p.accent,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // Search input with quick clear
          Container(
            height: 34,
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF121A2C) : Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: _searchQuery.isNotEmpty ? p.accent.withValues(alpha: 0.4) : p.div,
              ),
            ),
            child: Row(
              children: [
                const SizedBox(width: 10),
                Icon(LucideIcons.search, size: 13, color: p.textSec),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    textAlignVertical: TextAlignVertical.center,
                    style: TextStyle(color: p.text, fontSize: 12.5),
                    decoration: InputDecoration(
                      isDense: true,
                      hintText: 'Filter files…',
                      hintStyle: TextStyle(color: p.textSec.withValues(alpha: 0.7), fontSize: 12),
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.zero,
                    ),
                    onChanged: (v) => setState(() => _searchQuery = v),
                  ),
                ),
                if (_searchQuery.isNotEmpty)
                  GestureDetector(
                    onTap: () {
                      _searchController.clear();
                      setState(() => _searchQuery = '');
                    },
                    child: Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: Icon(LucideIcons.x, size: 13, color: p.textSec),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExplorerFooter() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: p.div.withValues(alpha: 0.5))),
      ),
      child: Row(
        children: [
          Icon(LucideIcons.fileSpreadsheet, size: 12, color: p.textSec),
          const SizedBox(width: 6),
          Text(
            '${_rawFiles.length} tracked files',
            style: TextStyle(color: p.textSec, fontSize: 11),
          ),
          const Spacer(),
          Text(
            'Snapshot ready',
            style: TextStyle(color: p.live, fontSize: 10.5, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  File Tree Nodes
  // ─────────────────────────────────────────────────────────
  Widget _buildFileTreeNode(FileNode node, int depth) {
    if (node.isDirectory) {
      return _DirectoryNode(
        node: node,
        depth: depth,
        palette: p,
        selectedFileId: _selectedFileId,
        onFileSelected: _onFileSelected,
      );
    }

    final isSelected = node.file?.id == _selectedFileId;
    final file = node.file;
    final ext = file?.extension ?? '';

    return _FileItemTile(
      name: node.name,
      extension: ext,
      lineCount: file?.lineCount ?? 0,
      depth: depth,
      isSelected: isSelected,
      palette: p,
      onTap: () => file != null ? _onFileSelected(file) : null,
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Empty State View
  // ─────────────────────────────────────────────────────────
  Widget _buildEmptyState() {
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 380),
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: p.bgElevated.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: p.div.withValues(alpha: 0.7)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: p.accent.withValues(alpha: 0.12),
              ),
              child: Center(
                child: Icon(LucideIcons.fileCode2, size: 28, color: p.accent),
              ),
            ),
            const SizedBox(height: 18),
            Text(
              'Select a file to inspect',
              style: TextStyle(
                color: p.text,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'View compiled Markdown documentation, formatted JSON, syntax-colored code, AST symbol graphs, and dependencies.',
              style: TextStyle(
                color: p.textSec,
                fontSize: 12.5,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  // ─────────────────────────────────────────────────────────
  //  File Detail View (Minimal, Single-Row Header + Compilers)
  // ─────────────────────────────────────────────────────────
  Widget _buildFileDetailView(FileDetail detail) {
    final file = detail.file;
    final ext = file.extension.toLowerCase();
    final isMarkdown = (ext == '.md' || ext == '.markdown');
    final isJson = ext == '.json';
    final isSvg = ext == '.svg';
    final isImage = (ext == '.png' || ext == '.jpg' || ext == '.jpeg' || ext == '.gif' || ext == '.webp' || ext == '.ico');
    final isBinary = file.isBinary || isImage;
    final hasSymbols = detail.symbols.isNotEmpty;
    final totalDeps = detail.outgoingDependencies.length + detail.incomingReferences.length;
    final hasDeps = totalDeps > 0;
    final hasTextContent = !isBinary && (detail.fullContent?.isNotEmpty == true);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── Minimal Single-Row Header Bar (Height 42px) ──
        Container(
          height: 42,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            color: p.bgSurface,
            border: Border(
              bottom: BorderSide(color: p.div.withValues(alpha: 0.7)),
            ),
          ),
          child: Row(
            children: [
              // Clean File Icon
              Icon(
                _fileIcon(file.filename),
                size: 14,
                color: _fileColor(ext),
              ),
              const SizedBox(width: 8),

              // Minimal Breadcrumb Path (e.g. images / flyer / swastha-yoga-flyer.jpeg)
              Expanded(
                child: _buildCleanPath(file.path, file.filename),
              ),

              // File Metrics: only show lines if lines > 0, and clean KB size
              if (file.lineCount > 0) ...[
                Text(
                  '${file.lineCount} lines',
                  style: TextStyle(
                    color: p.textSec,
                    fontSize: 11,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
                const SizedBox(width: 8),
                Text('•', style: TextStyle(color: p.div, fontSize: 10)),
                const SizedBox(width: 8),
              ],
              Text(
                '${(file.sizeBytes / 1024).toStringAsFixed(1)} KB',
                style: TextStyle(
                  color: p.textSec,
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono',
                ),
              ),

              // Contextual actions on the right (only when relevant)
              if (!isBinary) ...[
                // Compact Segmented Mode Switcher (only if multiple views exist)
                if (isMarkdown || isJson || isSvg || hasSymbols) ...[
                  const SizedBox(width: 14),
                  Container(
                    height: 26,
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF101726) : const Color(0xFFEAE5DC),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: p.div.withValues(alpha: 0.6)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if (isMarkdown) ...[
                          _miniModeButton('Preview', FileContentViewMode.rendered),
                          _miniModeButton('Raw', FileContentViewMode.source),
                        ] else if (isJson) ...[
                          _miniModeButton('Formatted', FileContentViewMode.rendered),
                          _miniModeButton('Raw', FileContentViewMode.source),
                        ] else if (isSvg) ...[
                          _miniModeButton('Preview', FileContentViewMode.rendered),
                          _miniModeButton('XML', FileContentViewMode.source),
                        ] else ...[
                          _miniModeButton('Code', FileContentViewMode.source),
                        ],
                        if (hasSymbols)
                          _miniModeButton('Symbols (${detail.symbols.length})', FileContentViewMode.symbols),
                        if (hasDeps)
                          _miniModeButton('Deps ($totalDeps)', FileContentViewMode.dependencies),
                      ],
                    ),
                  ),
                ],

                if (hasTextContent) ...[
                  const SizedBox(width: 10),
                  // Sleek minimal copy button
                  Tooltip(
                    message: _copied ? 'Copied!' : 'Copy file content',
                    child: InkWell(
                      borderRadius: BorderRadius.circular(5),
                      onTap: () => _copyContent(detail.fullContent ?? ''),
                      child: Container(
                        width: 26,
                        height: 26,
                        decoration: BoxDecoration(
                          color: p.bgElevated,
                          borderRadius: BorderRadius.circular(5),
                          border: Border.all(color: p.div.withValues(alpha: 0.8)),
                        ),
                        child: Center(
                          child: Icon(
                            _copied ? LucideIcons.check : LucideIcons.copy,
                            size: 12.5,
                            color: _copied ? p.live : p.textSec,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ],
          ),
        ),

        // ── Active Content Viewer Engine ──
        Expanded(
          child: isBinary
              ? _buildBinaryAssetViewer(file)
              : _buildActiveContentViewer(detail, isMarkdown, isJson, isSvg),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Clean Minimal Breadcrumb Path
  // ─────────────────────────────────────────────────────────
  Widget _buildCleanPath(String path, String filename) {
    final segments = path.replaceAll('\\', '/').split('/').where((s) => s.isNotEmpty).toList();
    if (segments.isEmpty) {
      return Text(
        filename,
        style: TextStyle(
          color: p.text,
          fontSize: 12.5,
          fontWeight: FontWeight.w600,
          fontFamily: 'JetBrains Mono',
        ),
        overflow: TextOverflow.ellipsis,
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (int i = 0; i < segments.length; i++) ...[
            if (i > 0)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(
                  '/',
                  style: TextStyle(
                    color: p.textSec.withValues(alpha: 0.35),
                    fontSize: 11,
                  ),
                ),
              ),
            Text(
              segments[i],
              style: TextStyle(
                color: i == segments.length - 1 ? p.text : p.textSec,
                fontSize: 12,
                fontWeight: i == segments.length - 1 ? FontWeight.w600 : FontWeight.w400,
                fontFamily: i == segments.length - 1 ? 'JetBrains Mono' : null,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _miniModeButton(String label, FileContentViewMode mode) {
    final active = _viewMode == mode;
    return GestureDetector(
      onTap: () => setState(() => _viewMode = mode),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: active
              ? (isDark ? const Color(0xFF222C44) : Colors.white)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          boxShadow: active
              ? [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.04),
                    blurRadius: 3,
                    offset: const Offset(0, 1),
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? p.text : p.textSec,
            fontSize: 11,
            fontWeight: active ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }

  Widget _buildBinaryAssetViewer(ProjectFile file) {
    final ext = file.extension.toLowerCase();
    final isImage = (ext == '.png' || ext == '.jpg' || ext == '.jpeg' || ext == '.gif' || ext == '.webp' || ext == '.ico');

    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 320),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
        decoration: BoxDecoration(
          color: p.bgSurface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: p.div.withValues(alpha: 0.7)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _fileColor(ext).withValues(alpha: 0.12),
              ),
              child: Center(
                child: Icon(_fileIcon(file.filename), size: 20, color: _fileColor(ext)),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              file.filename,
              style: TextStyle(
                color: p.text,
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
                fontFamily: 'JetBrains Mono',
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 6),
            Text(
              isImage
                  ? 'Binary Image Asset • ${(file.sizeBytes / 1024).toStringAsFixed(1)} KB'
                  : 'Binary Asset • ${(file.sizeBytes / 1024).toStringAsFixed(1)} KB',
              style: TextStyle(color: p.textSec, fontSize: 11),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: p.bgBase,
                borderRadius: BorderRadius.circular(5),
                border: Border.all(color: p.div.withValues(alpha: 0.6)),
              ),
              child: Text(
                'Stored in repository snapshot',
                style: TextStyle(
                  color: p.textSec.withValues(alpha: 0.65),
                  fontSize: 10,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Active Content Viewer Switcher
  // ─────────────────────────────────────────────────────────
  Widget _buildActiveContentViewer(
    FileDetail detail,
    bool isMarkdown,
    bool isJson,
    bool isSvg,
  ) {
    final content = detail.fullContent ?? '';

    switch (_viewMode) {
      case FileContentViewMode.rendered:
        if (isMarkdown) {
          return _buildMarkdownCompiler(content);
        } else if (isJson) {
          return _buildFormattedJsonViewer(content);
        } else if (isSvg) {
          return _buildSvgViewer(content);
        }
        return _buildCodeViewer(content);

      case FileContentViewMode.source:
        return _buildCodeViewer(content);

      case FileContentViewMode.symbols:
        return _buildSymbolsInspector(detail);

      case FileContentViewMode.dependencies:
        return _buildDependenciesInspector(detail);
    }
  }

  // ─────────────────────────────────────────────────────────
  //  Compiler 1: Editorial Markdown Compiler
  // ─────────────────────────────────────────────────────────
  Widget _buildMarkdownCompiler(String markdownContent) {
    return Container(
      color: p.bgBase,
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 880),
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              color: p.bgSurface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: p.div.withValues(alpha: 0.8)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.04),
                  blurRadius: 10,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: MarkdownText(
              text: markdownContent.isEmpty ? '*Empty document*' : markdownContent,
              palette: p,
              selectable: true,
            ),
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Compiler 2: Formatted & Syntax-Colored JSON Viewer
  // ─────────────────────────────────────────────────────────
  Widget _buildFormattedJsonViewer(String rawJson) {
    String prettyJson = rawJson;
    bool isValidJson = false;

    try {
      final decoded = jsonDecode(rawJson);
      prettyJson = const JsonEncoder.withIndent('  ').convert(decoded);
      isValidJson = true;
    } catch (_) {
      prettyJson = rawJson;
      isValidJson = false;
    }

    final lines = prettyJson.split('\n');

    return Container(
      color: isDark ? const Color(0xFF0D1220) : const Color(0xFFFAF7F2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // JSON Status banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF131B2C) : const Color(0xFFF0ECE3),
              border: Border(bottom: BorderSide(color: p.div.withValues(alpha: 0.5))),
            ),
            child: Row(
              children: [
                Icon(
                  isValidJson ? LucideIcons.checkCircle2 : LucideIcons.alertCircle,
                  size: 13,
                  color: isValidJson ? p.live : p.inferred,
                ),
                const SizedBox(width: 6),
                Text(
                  isValidJson ? 'Valid JSON Document' : 'Raw JSON Format',
                  style: TextStyle(
                    color: isValidJson ? p.live : p.textSec,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                Text(
                  '${lines.length} lines',
                  style: TextStyle(color: p.textSec, fontSize: 11),
                ),
              ],
            ),
          ),
          // Code list
          Expanded(
            child: _buildLineNumberedCodeView(lines, isJson: true),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Compiler 3: Live Vector SVG Previewer
  // ─────────────────────────────────────────────────────────
  Widget _buildSvgViewer(String svgString) {
    return Container(
      color: p.bgBase,
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                constraints: const BoxConstraints(maxWidth: 600, maxHeight: 500),
                padding: const EdgeInsets.all(32),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF121A2C) : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: p.div),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.05),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Center(
                  child: SvgPicture.string(
                    svgString,
                    placeholderBuilder: (ctx) => Center(
                      child: CircularProgressIndicator(color: p.accent, strokeWidth: 2),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Vector SVG graphic compiled natively',
                style: TextStyle(color: p.textSec, fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Compiler 4: Code Viewer with Line Gutter & Syntax Tokens
  // ─────────────────────────────────────────────────────────
  Widget _buildCodeViewer(String codeContent) {
    final lines = codeContent.isEmpty ? [''] : codeContent.split('\n');

    return Container(
      color: isDark ? const Color(0xFF0C111E) : const Color(0xFFFAF7F2),
      child: _buildLineNumberedCodeView(lines, isJson: false),
    );
  }

  Widget _buildLineNumberedCodeView(List<String> lines, {required bool isJson}) {
    final gutterWidth = (lines.length > 999) ? 56.0 : 44.0;

    return SingleChildScrollView(
      controller: _codeVerticalScrollController,
      scrollDirection: Axis.vertical,
      child: SingleChildScrollView(
        scrollDirection: _wrapLines ? Axis.vertical : Axis.horizontal,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Line numbers gutter
            if (_showLineNumbers)
              Container(
                width: gutterWidth,
                padding: const EdgeInsets.symmetric(vertical: 14),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF090D18) : const Color(0xFFF2ECE1),
                  border: Border(
                    right: BorderSide(color: p.div.withValues(alpha: 0.6)),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: List.generate(lines.length, (idx) {
                    final isTarget = _targetLine != null && (idx + 1) == _targetLine;
                    return Container(
                      height: 20.0,
                      color: isTarget ? p.accent.withValues(alpha: 0.22) : Colors.transparent,
                      alignment: Alignment.centerRight,
                      child: Padding(
                        padding: const EdgeInsets.only(right: 10),
                        child: Text(
                          '${idx + 1}',
                          style: TextStyle(
                            fontFamily: 'JetBrains Mono',
                            fontSize: 11,
                            fontWeight: isTarget ? FontWeight.w700 : FontWeight.w400,
                            color: isTarget ? p.accent : p.textSec.withValues(alpha: 0.5),
                          ),
                        ),
                      ),
                    );
                  }),
                ),
              ),

            // Code lines content
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: List.generate(lines.length, (idx) {
                  final line = lines[idx];
                  final isTarget = _targetLine != null && (idx + 1) == _targetLine;
                  return Container(
                    height: 20.0,
                    decoration: isTarget
                        ? BoxDecoration(
                            color: p.accent.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(2),
                            border: Border(
                              left: BorderSide(color: p.accent, width: 2.5),
                            ),
                          )
                        : null,
                    padding: isTarget ? const EdgeInsets.only(left: 4) : EdgeInsets.zero,
                    child: SelectableText.rich(
                      TextSpan(
                        children: isJson
                            ? _highlightJsonTokens(line)
                            : _highlightCodeTokens(line),
                      ),
                    ),
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Syntax Token Highlighting Engines
  // ─────────────────────────────────────────────────────────
  List<TextSpan> _highlightJsonTokens(String line) {
    final spans = <TextSpan>[];
    // Check for keys, string values, numbers, booleans
    final keyMatch = RegExp(r'^(\s*)"([^"]+)"(\s*:)(.*)$').firstMatch(line);
    if (keyMatch != null) {
      spans.add(TextSpan(text: keyMatch.group(1), style: const TextStyle(fontFamily: 'JetBrains Mono')));
      // Key in vibrant sky blue
      spans.add(TextSpan(
        text: '"${keyMatch.group(2)}"',
        style: TextStyle(
          color: isDark ? const Color(0xFF7DD3FC) : const Color(0xFF0369A1),
          fontFamily: 'JetBrains Mono',
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ));
      // Colon
      spans.add(TextSpan(
        text: keyMatch.group(3),
        style: TextStyle(color: p.textSec, fontFamily: 'JetBrains Mono', fontSize: 12),
      ));
      // Value part
      final valuePart = keyMatch.group(4) ?? '';
      spans.addAll(_tokenizeJsonValue(valuePart));
    } else {
      spans.addAll(_tokenizeJsonValue(line));
    }
    return spans;
  }

  List<TextSpan> _tokenizeJsonValue(String raw) {
    final spans = <TextSpan>[];
    final tokenRegex = RegExp(r'("(?:[^"\\]|\\.)*")|(-?\b\d+(?:\.\d+)?\b)|(\btrue\b|\bfalse\b|\bnull\b)|([\{\}\[\]:,])|([^\s"0-9a-zA-Z\{\}\[\]:,]+)');

    int lastEnd = 0;
    for (final m in tokenRegex.allMatches(raw)) {
      if (m.start > lastEnd) {
        spans.add(TextSpan(
          text: raw.substring(lastEnd, m.start),
          style: TextStyle(color: p.text, fontFamily: 'JetBrains Mono', fontSize: 12),
        ));
      }
      final str = m.group(1);
      final num = m.group(2);
      final boolOrNull = m.group(3);
      final punct = m.group(4);

      if (str != null) {
        spans.add(TextSpan(
          text: str,
          style: TextStyle(
            color: isDark ? const Color(0xFF86EFAC) : const Color(0xFF15803D),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
          ),
        ));
      } else if (num != null) {
        spans.add(TextSpan(
          text: num,
          style: TextStyle(
            color: isDark ? const Color(0xFFFDBA74) : const Color(0xFFC2410C),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
          ),
        ));
      } else if (boolOrNull != null) {
        spans.add(TextSpan(
          text: boolOrNull,
          style: TextStyle(
            color: isDark ? const Color(0xFFC084FC) : const Color(0xFF7E22CE),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ));
      } else if (punct != null) {
        spans.add(TextSpan(
          text: punct,
          style: TextStyle(color: p.textSec, fontFamily: 'JetBrains Mono', fontSize: 12),
        ));
      } else {
        spans.add(TextSpan(
          text: m.group(0)!,
          style: TextStyle(color: p.text, fontFamily: 'JetBrains Mono', fontSize: 12),
        ));
      }
      lastEnd = m.end;
    }

    if (lastEnd < raw.length) {
      spans.add(TextSpan(
        text: raw.substring(lastEnd),
        style: TextStyle(color: p.text, fontFamily: 'JetBrains Mono', fontSize: 12),
      ));
    }

    return spans;
  }

  List<TextSpan> _highlightCodeTokens(String line) {
    final spans = <TextSpan>[];
    final trimmed = line.trimLeft();

    // Check for comment line
    if (trimmed.startsWith('//') || trimmed.startsWith('#') || trimmed.startsWith('/*')) {
      return [
        TextSpan(
          text: line,
          style: TextStyle(
            color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
            fontStyle: FontStyle.italic,
          ),
        )
      ];
    }

    // Tokenize line with keywords, strings, numbers
    final tokenRegex = RegExp(
      r'("(?:[^"\\]|\\.)*"|\x27(?:[^\x27\\]|\\.)*\x27|`(?:[^`\\]|\\.)*`)|(\b(?:import|export|from|as|default|const|let|var|function|class|interface|type|enum|struct|package|def|return|if|else|elif|for|while|do|switch|case|break|continue|yield|try|catch|finally|throw|async|await|public|private|protected|static|final|override|new|this|self|super|extends|implements|with|in|is|not|and|or|true|false|null|None|undefined|void)\b)|(\b\d+(?:\.\d+)?\b)|(@\w+)',
    );

    int lastEnd = 0;
    for (final m in tokenRegex.allMatches(line)) {
      if (m.start > lastEnd) {
        spans.add(TextSpan(
          text: line.substring(lastEnd, m.start),
          style: TextStyle(color: p.text, fontFamily: 'JetBrains Mono', fontSize: 12),
        ));
      }
      final str = m.group(1);
      final keyword = m.group(2);
      final num = m.group(3);
      final decorator = m.group(4);

      if (str != null) {
        spans.add(TextSpan(
          text: str,
          style: TextStyle(
            color: isDark ? const Color(0xFF86EFAC) : const Color(0xFF15803D),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
          ),
        ));
      } else if (keyword != null) {
        spans.add(TextSpan(
          text: keyword,
          style: TextStyle(
            color: isDark ? const Color(0xFFC084FC) : const Color(0xFF7E22CE),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ));
      } else if (num != null) {
        spans.add(TextSpan(
          text: num,
          style: TextStyle(
            color: isDark ? const Color(0xFFFDBA74) : const Color(0xFFC2410C),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
          ),
        ));
      } else if (decorator != null) {
        spans.add(TextSpan(
          text: decorator,
          style: TextStyle(
            color: isDark ? const Color(0xFF38BDF8) : const Color(0xFF0284C7),
            fontFamily: 'JetBrains Mono',
            fontSize: 12,
          ),
        ));
      }
      lastEnd = m.end;
    }

    if (lastEnd < line.length) {
      spans.add(TextSpan(
        text: line.substring(lastEnd),
        style: TextStyle(color: p.text, fontFamily: 'JetBrains Mono', fontSize: 12),
      ));
    }

    return spans;
  }

  // ─────────────────────────────────────────────────────────
  //  Compiler 5: AST Symbols Inspector
  // ─────────────────────────────────────────────────────────
  Widget _buildSymbolsInspector(FileDetail detail) {
    final filteredSymbols = _symbolFilter.isEmpty
        ? detail.symbols
        : detail.symbols
            .where((s) => s.name.toLowerCase().contains(_symbolFilter.toLowerCase()))
            .toList();

    return Container(
      color: p.bgBase,
      child: Column(
        children: [
          // Filter search bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: Container(
                    height: 36,
                    decoration: BoxDecoration(
                      color: p.bgSurface,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: p.div),
                    ),
                    child: TextField(
                      style: TextStyle(color: p.text, fontSize: 12.5),
                      decoration: InputDecoration(
                        isDense: true,
                        hintText: 'Filter symbols…',
                        hintStyle: TextStyle(color: p.textSec, fontSize: 12),
                        prefixIcon: Icon(LucideIcons.search, size: 14, color: p.textSec),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(vertical: 9),
                      ),
                      onChanged: (v) => setState(() => _symbolFilter = v),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  '${filteredSymbols.length} of ${detail.symbols.length} symbols',
                  style: TextStyle(color: p.textSec, fontSize: 12),
                ),
              ],
            ),
          ),

          // Symbol list
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              itemCount: filteredSymbols.length,
              separatorBuilder: (context, index) => const SizedBox(height: 6),
              itemBuilder: (context, idx) {
                final s = filteredSymbols[idx];
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: p.bgSurface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: p.div.withValues(alpha: 0.7)),
                  ),
                  child: Row(
                    children: [
                      _chip(s.symbolType, _symbolColor(s.symbolType)),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              s.name,
                              style: TextStyle(
                                color: p.text,
                                fontSize: 13,
                                fontFamily: 'JetBrains Mono',
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            if (s.qualifiedName.isNotEmpty && s.qualifiedName != s.name)
                              Text(
                                s.qualifiedName,
                                style: TextStyle(color: p.textSec, fontSize: 11),
                              ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: p.bgBase,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: p.div),
                        ),
                        child: Text(
                          'L${s.startLine}–L${s.endLine}',
                          style: TextStyle(
                            fontFamily: 'JetBrains Mono',
                            color: p.textSec,
                            fontSize: 10.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  Compiler 6: Dependencies & Graph References
  // ─────────────────────────────────────────────────────────
  Widget _buildDependenciesInspector(FileDetail detail) {
    return Container(
      color: p.bgBase,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Outgoing dependencies
          Text(
            'Outgoing Dependencies (${detail.outgoingDependencies.length})',
            style: TextStyle(color: p.text, fontSize: 13.5, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(
            'Modules and files imported by this file',
            style: TextStyle(color: p.textSec, fontSize: 11.5),
          ),
          const SizedBox(height: 10),
          if (detail.outgoingDependencies.isEmpty)
            _emptyDependencyCard('No outgoing imports tracked')
          else
            ...detail.outgoingDependencies.map((dep) => _dependencyCard(dep, isOutgoing: true)),

          const SizedBox(height: 24),

          // Incoming references
          Text(
            'Incoming References (${detail.incomingReferences.length})',
            style: TextStyle(color: p.text, fontSize: 13.5, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(
            'Other files that depend on or import this file',
            style: TextStyle(color: p.textSec, fontSize: 11.5),
          ),
          const SizedBox(height: 10),
          if (detail.incomingReferences.isEmpty)
            _emptyDependencyCard('No incoming references tracked')
          else
            ...detail.incomingReferences.map((dep) => _dependencyCard(dep, isOutgoing: false)),
        ],
      ),
    );
  }

  Widget _emptyDependencyCard(String message) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: p.bgSurface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: p.div),
      ),
      child: Text(message, style: TextStyle(color: p.textSec, fontSize: 12)),
    );
  }

  Widget _dependencyCard(ProjectDependency dep, {required bool isOutgoing}) {
    final rawTarget = isOutgoing ? (dep.targetPath ?? dep.externalPackage) : dep.sourcePath;
    final targetPath = rawTarget ?? 'unknown';
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: p.bgSurface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: p.div),
      ),
      child: Row(
        children: [
          Icon(
            isOutgoing ? LucideIcons.arrowUpRight : LucideIcons.arrowDownLeft,
            size: 14,
            color: isOutgoing ? p.accent : p.live,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              targetPath,
              style: TextStyle(
                color: p.text,
                fontSize: 12.5,
                fontFamily: 'JetBrains Mono',
              ),
            ),
          ),
          _chip(dep.dependencyType, p.neutral),
          if (dep.lineNumber > 0) ...[
            const SizedBox(width: 8),
            Text('L${dep.lineNumber}', style: TextStyle(color: p.textSec, fontSize: 11)),
          ],
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────
  //  UI Helper Components (Pills, Chips, Badges, Icons)
  // ─────────────────────────────────────────────────────────


  Widget _chip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }

  IconData _fileIcon(String name) {
    final lower = name.toLowerCase();
    if (lower.endsWith('.md') || lower.endsWith('.markdown')) return LucideIcons.fileText;
    if (lower.endsWith('.dart') || lower.endsWith('.py') || lower.endsWith('.ts') || lower.endsWith('.tsx') || lower.endsWith('.js') || lower.endsWith('.jsx')) return LucideIcons.fileCode;
    if (lower.endsWith('.json')) return LucideIcons.fileJson;
    if (lower.endsWith('.yaml') || lower.endsWith('.yml') || lower.endsWith('.toml')) return LucideIcons.fileCog;
    if (lower.endsWith('.svg') || lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.ico')) return LucideIcons.image;
    if (lower.endsWith('.css') || lower.endsWith('.scss')) return LucideIcons.palette;
    if (lower.endsWith('.sql')) return LucideIcons.database;
    if (lower.endsWith('.sh') || lower.endsWith('.bash')) return LucideIcons.terminal;
    return LucideIcons.file;
  }

  Color _fileColor(String ext) {
    switch (ext.toLowerCase()) {
      case '.md':
      case '.markdown':
        return const Color(0xFF38BDF8); // Sky blue
      case '.ts':
      case '.tsx':
        return const Color(0xFF3B82F6); // Blue
      case '.js':
      case '.jsx':
      case '.mjs':
        return const Color(0xFFFBBF24); // Amber
      case '.py':
        return const Color(0xFF34D399); // Emerald
      case '.dart':
        return const Color(0xFF2DD4BF); // Teal
      case '.json':
        return const Color(0xFFFB923C); // Orange
      case '.yaml':
      case '.yml':
        return const Color(0xFFA855F7); // Purple
      case '.svg':
      case '.png':
      case '.jpg':
        return const Color(0xFF4ADE80); // Green
      case '.css':
      case '.scss':
        return const Color(0xFFF472B6); // Pink
      default:
        return p.accent;
    }
  }

  Color _symbolColor(String type) {
    switch (type.toUpperCase()) {
      case 'CLASS':
        return const Color(0xFF38BDF8);
      case 'METHOD':
      case 'FUNCTION':
        return const Color(0xFF86EFAC);
      case 'INTERFACE':
      case 'TYPE':
        return const Color(0xFFC084FC);
      default:
        return p.neutral;
    }
  }
}

// ─────────────────────────────────────────────────────────
//  Folder Directory Node Widget
// ─────────────────────────────────────────────────────────
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
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Folder Row
        InkWell(
          borderRadius: BorderRadius.circular(5),
          onTap: () => setState(() => _expanded = !_expanded),
          child: Padding(
            padding: EdgeInsets.only(
              left: 10.0 + widget.depth * 14.0,
              right: 8,
              top: 5,
              bottom: 5,
            ),
            child: Row(
              children: [
                Icon(
                  _expanded ? LucideIcons.chevronDown : LucideIcons.chevronRight,
                  size: 12,
                  color: p.textSec.withValues(alpha: 0.7),
                ),
                const SizedBox(width: 5),
                Icon(
                  _expanded ? LucideIcons.folderOpen : LucideIcons.folder,
                  size: 14.5,
                  color: const Color(0xFFE5A93C),
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    widget.node.name,
                    style: TextStyle(
                      color: p.text,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w500,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Text(
                  '${widget.node.children.length}',
                  style: TextStyle(
                    color: p.textSec.withValues(alpha: 0.6),
                    fontSize: 10,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
              ],
            ),
          ),
        ),

        // Expanded children
        if (_expanded)
          Container(
            decoration: BoxDecoration(
              border: Border(
                left: BorderSide(
                  color: p.div.withValues(alpha: 0.35),
                  width: 1.0,
                ),
              ),
            ),
            margin: EdgeInsets.only(left: 16.0 + widget.depth * 14.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: widget.node.children.map((child) {
                if (child.isDirectory) {
                  return _DirectoryNode(
                    node: child,
                    depth: 0,
                    palette: p,
                    selectedFileId: widget.selectedFileId,
                    onFileSelected: widget.onFileSelected,
                  );
                }
                final isSelected = child.file?.id == widget.selectedFileId;
                return _FileItemTile(
                  name: child.name,
                  extension: child.file?.extension ?? '',
                  lineCount: child.file?.lineCount ?? 0,
                  depth: 0,
                  isSelected: isSelected,
                  palette: p,
                  onTap: () => child.file != null ? widget.onFileSelected(child.file!) : null,
                );
              }).toList(),
            ),
          ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────
//  File Item Tile Widget (Color-coded semantic icon & pills)
// ─────────────────────────────────────────────────────────
class _FileItemTile extends StatefulWidget {
  final String name;
  final String extension;
  final int lineCount;
  final int depth;
  final bool isSelected;
  final UnoPalette palette;
  final VoidCallback? onTap;

  const _FileItemTile({
    required this.name,
    required this.extension,
    required this.lineCount,
    required this.depth,
    required this.isSelected,
    required this.palette,
    required this.onTap,
  });

  @override
  State<_FileItemTile> createState() => _FileItemTileState();
}

class _FileItemTileState extends State<_FileItemTile> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isDark = p.isDark;
    final isSelected = widget.isSelected;
    final extColor = _fileColor(widget.extension);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          margin: const EdgeInsets.symmetric(vertical: 1.5),
          padding: EdgeInsets.only(
            left: 10.0 + widget.depth * 14.0,
            right: 8,
            top: 5,
            bottom: 5,
          ),
          decoration: BoxDecoration(
            color: isSelected
                ? (isDark
                    ? p.accent.withValues(alpha: 0.14)
                    : const Color(0xFFE8E2D6))
                : (_hovered
                    ? (isDark
                        ? Colors.white.withValues(alpha: 0.04)
                        : Colors.black.withValues(alpha: 0.03))
                    : Colors.transparent),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: isSelected
                  ? p.accent.withValues(alpha: 0.28)
                  : Colors.transparent,
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(_fileIcon(widget.name), size: 14, color: isSelected ? extColor : extColor.withValues(alpha: 0.85)),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  widget.name,
                  style: TextStyle(
                    color: isSelected ? (isDark ? p.text : p.accent) : p.text,
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (widget.lineCount > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? (isDark ? const Color(0xFF1E2840) : Colors.white)
                        : (isDark
                            ? Colors.black.withValues(alpha: 0.2)
                            : Colors.black.withValues(alpha: 0.04)),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${widget.lineCount}L',
                    style: TextStyle(
                      color: isSelected ? p.accent : p.textSec.withValues(alpha: 0.7),
                      fontSize: 9.5,
                      fontFamily: 'JetBrains Mono',
                      fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _fileIcon(String name) {
    final lower = name.toLowerCase();
    if (lower.endsWith('.md') || lower.endsWith('.markdown')) return LucideIcons.fileText;
    if (lower.endsWith('.dart') || lower.endsWith('.py') || lower.endsWith('.ts') || lower.endsWith('.tsx') || lower.endsWith('.js') || lower.endsWith('.jsx')) return LucideIcons.fileCode;
    if (lower.endsWith('.json')) return LucideIcons.fileJson;
    if (lower.endsWith('.yaml') || lower.endsWith('.yml') || lower.endsWith('.toml')) return LucideIcons.fileCog;
    if (lower.endsWith('.svg') || lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.ico')) return LucideIcons.image;
    if (lower.endsWith('.css') || lower.endsWith('.scss')) return LucideIcons.palette;
    if (lower.endsWith('.sql')) return LucideIcons.database;
    if (lower.endsWith('.sh') || lower.endsWith('.bash')) return LucideIcons.terminal;
    return LucideIcons.file;
  }

  Color _fileColor(String ext) {
    switch (ext.toLowerCase()) {
      case '.md':
      case '.markdown':
        return const Color(0xFF38BDF8); // Sky blue
      case '.ts':
      case '.tsx':
        return const Color(0xFF3B82F6); // Blue
      case '.js':
      case '.jsx':
      case '.mjs':
        return const Color(0xFFFBBF24); // Amber
      case '.py':
        return const Color(0xFF34D399); // Emerald
      case '.dart':
        return const Color(0xFF2DD4BF); // Teal
      case '.json':
        return const Color(0xFFFB923C); // Orange
      case '.yaml':
      case '.yml':
        return const Color(0xFFA855F7); // Purple
      case '.svg':
      case '.png':
      case '.jpg':
        return const Color(0xFF4ADE80); // Green
      case '.css':
      case '.scss':
        return const Color(0xFFF472B6); // Pink
      default:
        return const Color(0xFF94A3B8); // Slate
    }
  }
}
