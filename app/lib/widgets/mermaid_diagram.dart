import 'dart:convert';
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import '../theme/app_theme.dart';

class MermaidDiagram extends StatefulWidget {
  final String code;
  final UnoPalette palette;

  const MermaidDiagram({
    super.key,
    required this.code,
    required this.palette,
  });

  @override
  State<MermaidDiagram> createState() => _MermaidDiagramState();
}

class _MermaidDiagramState extends State<MermaidDiagram> {
  bool _copied = false;
  bool _showCode = false;
  bool _imageError = false;
  bool _isDownloading = false;
  late final bool _isWebViewSupported;

  @override
  void initState() {
    super.initState();
    _isWebViewSupported = !kIsWeb && (Platform.isMacOS || Platform.isWindows || Platform.isAndroid || Platform.isIOS);
  }

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.code));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  String _getMermaidImageUrl({String format = 'png'}) {
    final cleanCode = widget.code.trim();
    final payload = jsonEncode({
      'code': cleanCode,
      'mermaid': {
        'theme': 'dark',
        'themeVariables': {
          'background': '#131311',
          'primaryColor': '#2B2822',
          'primaryTextColor': '#E2E0D9',
          'primaryBorderColor': '#454035',
          'lineColor': '#888478',
          'secondaryColor': '#4A463B',
          'tertiaryColor': '#181816',
          'mainBkg': '#1D1C19',
        }
      }
    });
    final b64 = base64Url.encode(utf8.encode(payload));
    return 'https://mermaid.ink/img/$b64?type=$format';
  }

  Future<void> _downloadImage(String format) async {
    if (_isDownloading) return;
    setState(() => _isDownloading = true);

    try {
      final url = _getMermaidImageUrl(format: format);
      final response = await http.get(Uri.parse(url));

      if (response.statusCode == 200 && response.bodyBytes.isNotEmpty) {
        final timestamp = DateTime.now().millisecondsSinceEpoch;
        final fileName = 'mermaid_diagram_$timestamp.$format';
        final mimeType = format == 'png' ? 'image/png' : 'image/jpeg';

        final result = await FilePicker.saveFile(
          fileName: fileName,
          bytes: response.bodyBytes,
          mimeType: mimeType,
          dialogTitle: 'Save Diagram as ${format.toUpperCase()}',
        );

        if (result != null && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              backgroundColor: const Color(0xFF282824),
              content: Text(
                'Diagram saved as $fileName',
                style: const TextStyle(color: Color(0xFFEDEDEB)),
              ),
              duration: const Duration(seconds: 3),
            ),
          );
        }
      } else {
        throw Exception('HTTP error ${response.statusCode}');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: const Color(0xFF421D1D),
            content: Text(
              'Could not download image: $e',
              style: const TextStyle(color: Color(0xFFEDEDEB)),
            ),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isDownloading = false);
      }
    }
  }

  void _openFullscreen() {
    showDialog(
      context: context,
      useSafeArea: false,
      builder: (ctx) => _MermaidFullscreenDialog(
        code: widget.code,
        palette: widget.palette,
        imageUrl: _getMermaidImageUrl(format: 'png'),
        onDownload: _downloadImage,
      ),
    );
  }

  String _generateHtml() {
    final cleanCode = widget.code.replaceAll('`', '\\`').replaceAll('\$', '\\\$');
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    body {
      background-color: transparent;
      margin: 0;
      padding: 16px;
      display: flex;
      justify-content: center;
      align-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
      color: #E2E0D9;
      overflow-x: auto;
    }
    .mermaid {
      width: 100%;
      display: flex;
      justify-content: center;
    }
    svg {
      max-width: 100% !important;
      height: auto !important;
    }
  </style>
</head>
<body>
  <div class="mermaid">
$cleanCode
  </div>
  <script>
    function renderDiagram() {
      if (typeof mermaid !== 'undefined') {
        try {
          mermaid.initialize({ 
            startOnLoad: true, 
            theme: 'dark',
            themeVariables: {
              primaryColor: '#2B2822',
              primaryTextColor: '#E2E0D9',
              primaryBorderColor: '#454035',
              lineColor: '#888478',
              secondaryColor: '#4A463B',
              tertiaryColor: '#181816',
              background: '#131311',
              mainBkg: '#1D1C19'
            }
          });
          mermaid.run();
        } catch (e) {
          console.error('Mermaid render error:', e);
        }
      }
    }
    if (typeof mermaid !== 'undefined') {
      renderDiagram();
    } else {
      window.addEventListener('DOMContentLoaded', renderDiagram);
      window.addEventListener('load', renderDiagram);
    }
  </script>
</body>
</html>
''';
  }

  Widget _buildCodeView(UnoPalette p) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      color: const Color(0xFF131311),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: SelectableText(
          widget.code.trim(),
          style: UnoTypography.mono(
            color: p.textSec,
            fontSize: 12,
            height: 1.5,
          ),
        ),
      ),
    );
  }

  Widget _buildDiagramView(UnoPalette p) {
    if (_isWebViewSupported) {
      return SizedBox(
        height: 350,
        child: InAppWebView(
          initialData: InAppWebViewInitialData(
            data: _generateHtml(),
            baseUrl: WebUri('https://cdn.jsdelivr.net'),
          ),
          initialSettings: InAppWebViewSettings(
            transparentBackground: true,
            disableVerticalScroll: false,
            disableHorizontalScroll: false,
          ),
        ),
      );
    }

    if (_imageError) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            color: p.warn.withValues(alpha: 0.1),
            child: Row(
              children: [
                Icon(LucideIcons.info, size: 13, color: p.warn),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Remote render unavailable offline. Showing Mermaid source.',
                    style: UnoTypography.mono(color: p.warn, fontSize: 11),
                  ),
                ),
              ],
            ),
          ),
          _buildCodeView(p),
        ],
      );
    }

    return Container(
      constraints: const BoxConstraints(minHeight: 180, maxHeight: 420),
      color: const Color(0xFF131311),
      child: InteractiveViewer(
        minScale: 0.5,
        maxScale: 3.5,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Image.network(
              _getMermaidImageUrl(format: 'png'),
              fit: BoxFit.contain,
              loadingBuilder: (context, child, loadingProgress) {
                if (loadingProgress == null) return child;
                return Container(
                  height: 200,
                  alignment: Alignment.center,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: p.accent,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Rendering Mermaid diagram...',
                        style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                      ),
                    ],
                  ),
                );
              },
              errorBuilder: (context, error, stackTrace) {
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  if (mounted && !_imageError) {
                    setState(() => _imageError = true);
                  }
                });
                return const SizedBox.shrink();
              },
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildToggleButton({
    required String label,
    required IconData icon,
    required bool active,
    required VoidCallback onTap,
    required UnoPalette p,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(3),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: active ? p.accent.withValues(alpha: 0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(3),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 11,
              color: active ? p.accent : p.textSec,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: UnoTypography.mono(
                color: active ? p.accent : p.textSec,
                fontSize: 11,
                fontWeight: active ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDownloadButton(UnoPalette p) {
    return PopupMenuButton<String>(
      tooltip: 'Download diagram',
      color: const Color(0xFF20201D),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(6),
        side: BorderSide(color: p.div, width: 0.8),
      ),
      offset: const Offset(0, 26),
      onSelected: (format) => _downloadImage(format),
      itemBuilder: (context) => [
        PopupMenuItem<String>(
          value: 'png',
          height: 32,
          child: Row(
            children: [
              Icon(LucideIcons.image, size: 13, color: p.accent),
              const SizedBox(width: 8),
              Text(
                'PNG Image (.png)',
                style: UnoTypography.mono(color: p.text, fontSize: 11),
              ),
            ],
          ),
        ),
        PopupMenuItem<String>(
          value: 'jpeg',
          height: 32,
          child: Row(
            children: [
              Icon(LucideIcons.fileImage, size: 13, color: p.accent),
              const SizedBox(width: 8),
              Text(
                'JPEG Image (.jpeg)',
                style: UnoTypography.mono(color: p.text, fontSize: 11),
              ),
            ],
          ),
        ),
      ],
      child: Container(
        padding: const EdgeInsets.all(5),
        decoration: BoxDecoration(
          color: p.bgSurface,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: p.div, width: 0.6),
        ),
        child: _isDownloading
            ? SizedBox(
                width: 13,
                height: 13,
                child: CircularProgressIndicator(
                  strokeWidth: 1.5,
                  color: p.accent,
                ),
              )
            : Icon(
                LucideIcons.download,
                size: 13,
                color: p.textSec,
              ),
      ),
    );
  }

  Widget _buildFullscreenButton(UnoPalette p) {
    return Tooltip(
      message: 'Fullscreen',
      waitDuration: const Duration(milliseconds: 300),
      child: InkWell(
        onTap: _openFullscreen,
        borderRadius: BorderRadius.circular(4),
        child: Container(
          padding: const EdgeInsets.all(5),
          decoration: BoxDecoration(
            color: p.bgSurface,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: p.div, width: 0.6),
          ),
          child: Icon(
            LucideIcons.maximize2,
            size: 13,
            color: p.textSec,
          ),
        ),
      ),
    );
  }

  Widget _buildCopyButton(UnoPalette p) {
    return Tooltip(
      message: _copied ? 'Copied!' : 'Copy code',
      waitDuration: const Duration(milliseconds: 300),
      child: InkWell(
        onTap: _copy,
        borderRadius: BorderRadius.circular(4),
        child: Container(
          padding: const EdgeInsets.all(5),
          decoration: BoxDecoration(
            color: p.bgSurface,
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: p.div, width: 0.6),
          ),
          child: Icon(
            _copied ? LucideIcons.check : LucideIcons.copy,
            size: 13,
            color: _copied ? p.confirmed : p.textSec,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF131311),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: p.div, width: 1),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF1D1C19),
              border: Border(bottom: BorderSide(color: p.div, width: 0.8)),
            ),
            child: Row(
              children: [
                Icon(LucideIcons.gitMerge, size: 14, color: p.accent),
                const SizedBox(width: 8),
                Text(
                  'Mermaid Diagram',
                  style: UnoTypography.mono(
                    color: p.text,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                // Segmented Toggle: Diagram | Code
                Container(
                  decoration: BoxDecoration(
                    color: p.bgSurface,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: p.div, width: 0.6),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _buildToggleButton(
                        label: 'Diagram',
                        icon: LucideIcons.eye,
                        active: !_showCode,
                        onTap: () => setState(() => _showCode = false),
                        p: p,
                      ),
                      _buildToggleButton(
                        label: 'Code',
                        icon: LucideIcons.code,
                        active: _showCode,
                        onTap: () => setState(() => _showCode = true),
                        p: p,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 6),
                // Icon-only Download Button
                _buildDownloadButton(p),
                const SizedBox(width: 6),
                // Icon-only Fullscreen Button
                _buildFullscreenButton(p),
                const SizedBox(width: 6),
                // Icon-only Copy Code Button
                _buildCopyButton(p),
              ],
            ),
          ),

          // Content body
          _showCode ? _buildCodeView(p) : _buildDiagramView(p),
        ],
      ),
    );
  }
}

class _MermaidFullscreenDialog extends StatefulWidget {
  final String code;
  final UnoPalette palette;
  final String imageUrl;
  final Future<void> Function(String format) onDownload;

  const _MermaidFullscreenDialog({
    required this.code,
    required this.palette,
    required this.imageUrl,
    required this.onDownload,
  });

  @override
  State<_MermaidFullscreenDialog> createState() => _MermaidFullscreenDialogState();
}

class _MermaidFullscreenDialogState extends State<_MermaidFullscreenDialog> {
  final TransformationController _transController = TransformationController();
  bool _showCode = false;
  bool _copied = false;
  bool _isDownloading = false;

  @override
  void dispose() {
    _transController.dispose();
    super.dispose();
  }

  void _zoomIn() {
    final matrix = _transController.value.clone();
    matrix.scale(1.3, 1.3);
    _transController.value = matrix;
  }

  void _zoomOut() {
    final matrix = _transController.value.clone();
    matrix.scale(0.77, 0.77);
    _transController.value = matrix;
  }

  void _resetZoom() {
    _transController.value = Matrix4.identity();
  }

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.code));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  Future<void> _handleDownload(String format) async {
    if (_isDownloading) return;
    setState(() => _isDownloading = true);
    try {
      await widget.onDownload(format);
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;

    return Dialog.fullscreen(
      backgroundColor: const Color(0xFF131311),
      child: Scaffold(
        backgroundColor: const Color(0xFF131311),
        body: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Top Bar
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  color: const Color(0xFF1D1C19),
                  border: Border(bottom: BorderSide(color: p.div, width: 0.8)),
                ),
                child: Row(
                  children: [
                    Icon(LucideIcons.gitMerge, size: 16, color: p.accent),
                    const SizedBox(width: 8),
                    Text(
                      'Mermaid Diagram — Fullscreen',
                      style: UnoTypography.mono(
                        color: p.text,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const Spacer(),
                    // Segmented Toggle: Diagram | Code
                    Container(
                      decoration: BoxDecoration(
                        color: p.bgSurface,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: p.div, width: 0.6),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _buildTabButton(
                            label: 'Diagram',
                            icon: LucideIcons.eye,
                            active: !_showCode,
                            onTap: () => setState(() => _showCode = false),
                            p: p,
                          ),
                          _buildTabButton(
                            label: 'Code',
                            icon: LucideIcons.code,
                            active: _showCode,
                            onTap: () => setState(() => _showCode = true),
                            p: p,
                          ),
                        ],
                      ),
                    ),
                    if (!_showCode) ...[
                      const SizedBox(width: 10),
                      // Zoom Controls
                      Container(
                        decoration: BoxDecoration(
                          color: p.bgSurface,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: p.div, width: 0.6),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              tooltip: 'Zoom In',
                              icon: Icon(LucideIcons.zoomIn, size: 13, color: p.textSec),
                              visualDensity: VisualDensity.compact,
                              padding: const EdgeInsets.all(6),
                              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                              onPressed: _zoomIn,
                            ),
                            Container(width: 0.6, height: 16, color: p.div),
                            InkWell(
                              onTap: _resetZoom,
                              child: Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 5),
                                child: Text(
                                  '100%',
                                  style: UnoTypography.mono(color: p.textSec, fontSize: 10),
                                ),
                              ),
                            ),
                            Container(width: 0.6, height: 16, color: p.div),
                            IconButton(
                              tooltip: 'Zoom Out',
                              icon: Icon(LucideIcons.zoomOut, size: 13, color: p.textSec),
                              visualDensity: VisualDensity.compact,
                              padding: const EdgeInsets.all(6),
                              constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
                              onPressed: _zoomOut,
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(width: 8),
                    // Icon-only Download Menu
                    PopupMenuButton<String>(
                      tooltip: 'Download diagram',
                      color: const Color(0xFF20201D),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                        side: BorderSide(color: p.div, width: 0.8),
                      ),
                      offset: const Offset(0, 32),
                      onSelected: _handleDownload,
                      itemBuilder: (context) => [
                        PopupMenuItem<String>(
                          value: 'png',
                          height: 34,
                          child: Row(
                            children: [
                              Icon(LucideIcons.image, size: 14, color: p.accent),
                              const SizedBox(width: 8),
                              Text(
                                'PNG Image (.png)',
                                style: UnoTypography.mono(color: p.text, fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                        PopupMenuItem<String>(
                          value: 'jpeg',
                          height: 34,
                          child: Row(
                            children: [
                              Icon(LucideIcons.fileImage, size: 14, color: p.accent),
                              const SizedBox(width: 8),
                              Text(
                                'JPEG Image (.jpeg)',
                                style: UnoTypography.mono(color: p.text, fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                      ],
                      child: Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: p.bgSurface,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: p.div, width: 0.6),
                        ),
                        child: _isDownloading
                            ? SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 1.5, color: p.accent),
                              )
                            : Icon(LucideIcons.download, size: 14, color: p.textSec),
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Icon-only Copy Code Button
                    Tooltip(
                      message: _copied ? 'Copied!' : 'Copy code',
                      waitDuration: const Duration(milliseconds: 300),
                      child: InkWell(
                        onTap: _copy,
                        borderRadius: BorderRadius.circular(4),
                        child: Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: p.bgSurface,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: p.div, width: 0.6),
                          ),
                          child: Icon(
                            _copied ? LucideIcons.check : LucideIcons.copy,
                            size: 14,
                            color: _copied ? p.confirmed : p.textSec,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Close Fullscreen Button
                    IconButton(
                      tooltip: 'Exit Fullscreen (ESC)',
                      icon: Icon(LucideIcons.x, size: 18, color: p.text),
                      padding: const EdgeInsets.all(6),
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),

              // View Area
              Expanded(
                child: _showCode
                    ? Container(
                        color: const Color(0xFF131311),
                        padding: const EdgeInsets.all(24),
                        child: SingleChildScrollView(
                          child: SelectableText(
                            widget.code.trim(),
                            style: UnoTypography.mono(
                              color: p.text,
                              fontSize: 13,
                              height: 1.6,
                            ),
                          ),
                        ),
                      )
                    : Stack(
                        children: [
                          Positioned.fill(
                            child: InteractiveViewer(
                              transformationController: _transController,
                              minScale: 0.1,
                              maxScale: 8.0,
                              boundaryMargin: const EdgeInsets.all(1200),
                              child: Center(
                                child: Padding(
                                  padding: const EdgeInsets.all(32),
                                  child: Image.network(
                                    widget.imageUrl,
                                    fit: BoxFit.contain,
                                    loadingBuilder: (context, child, loadingProgress) {
                                      if (loadingProgress == null) return child;
                                      return Center(
                                        child: Column(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: p.accent,
                                            ),
                                            const SizedBox(height: 12),
                                            Text(
                                              'Loading full resolution diagram...',
                                              style: UnoTypography.mono(color: p.textSec, fontSize: 12),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                    errorBuilder: (context, error, stackTrace) => Center(
                                      child: Column(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(LucideIcons.alertCircle, size: 28, color: p.warn),
                                          const SizedBox(height: 10),
                                          Text(
                                            'Failed to load diagram in fullscreen.',
                                            style: UnoTypography.mono(color: p.warn, fontSize: 13),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          // Bottom helper pill
                          Positioned(
                            bottom: 16,
                            left: 0,
                            right: 0,
                            child: Center(
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                                decoration: BoxDecoration(
                                  color: const Color(0xDD1D1C19),
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(color: p.div, width: 0.6),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(LucideIcons.zoomIn, size: 12, color: p.textSec),
                                    const SizedBox(width: 6),
                                    Text(
                                      'Scroll / Pinch to zoom • Drag to pan • ESC to exit',
                                      style: UnoTypography.mono(color: p.textSec, fontSize: 11),
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
          ),
        ),
      ),
    );
  }

  Widget _buildTabButton({
    required String label,
    required IconData icon,
    required bool active,
    required VoidCallback onTap,
    required UnoPalette p,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(3),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: active ? p.accent.withValues(alpha: 0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(3),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 12,
              color: active ? p.accent : p.textSec,
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: UnoTypography.mono(
                color: active ? p.accent : p.textSec,
                fontSize: 11,
                fontWeight: active ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
