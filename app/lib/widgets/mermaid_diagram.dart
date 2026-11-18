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

  /// Cleans the raw Mermaid code to fix common syntax issues:
  ///  - Strips leading/trailing whitespace and fences
  ///  - Auto-injects flowchart TD if header is missing
  ///  - Escapes unquoted node labels containing special characters
  late String _sanitizedCode;

  /// Sanitizes Mermaid code to prevent common parse errors.
  static String sanitizeMermaid(String raw) {
    var c = raw.trim();
    if (c.startsWith('```mermaid')) {
      c = c.substring(10).trim();
    } else if (c.startsWith('```')) {
      c = c.substring(3).trim();
    }
    if (c.endsWith('```')) {
      c = c.substring(0, c.length - 3).trim();
    }
    c = c.trim();

    final lines = c.split('\n');
    final firstLine = lines.isNotEmpty ? lines.first.trim() : '';
    final hasHeader = firstLine.startsWith('flowchart') ||
        firstLine.startsWith('graph') ||
        firstLine.startsWith('sequenceDiagram') ||
        firstLine.startsWith('classDiagram') ||
        firstLine.startsWith('stateDiagram') ||
        firstLine.startsWith('erDiagram') ||
        firstLine.startsWith('gantt') ||
        firstLine.startsWith('pie');

    if (!hasHeader) {
      c = 'flowchart TD\n$c';
    }

    // Auto-quote unquoted labels containing parentheses, slashes, or hyphens e.g. A[Label (info)] -> A["Label (info)"]
    c = c.replaceAllMapped(
      RegExp(r'(\b[a-zA-Z0-9_]+)\[([^"\]\n]*[\(\)\/\s\-][^"\]\n]*)\]'),
      (match) => '${match.group(1)}["${match.group(2)}"]',
    );

    // Fix unquoted node labels with special chars on each line
    final splitLines = c.split('\n');
    final fixedLines = <String>[];
    final nodePattern = RegExp(r'^(\s*)(\w+)\[([^\]"]+)\](.*)$');

    for (final line in splitLines) {
      var fixedLine = line;
      final m = nodePattern.firstMatch(fixedLine);
      if (m != null) {
        final label = m.group(3)!;
        if (label.contains('&') ||
            label.contains('<') ||
            label.contains('>') ||
            label.contains('"') ||
            label.contains('#') ||
            label.contains(';')) {
          final clean = label
              .replaceAll('"', "'")
              .replaceAll('&', 'and')
              .replaceAll('<', '')
              .replaceAll('>', '')
              .replaceAll('#', '')
              .replaceAll(';', '');
          fixedLine = '${m.group(1)}${m.group(2)}["$clean"]${m.group(4)}';
        }
      }
      fixedLines.add(fixedLine);
    }

    return fixedLines.join('\n');
  }

  @override
  void initState() {
    super.initState();
    _isWebViewSupported = !kIsWeb && (Platform.isMacOS || Platform.isWindows || Platform.isAndroid || Platform.isIOS);
    _sanitizedCode = sanitizeMermaid(widget.code);
  }

  @override
  void didUpdateWidget(MermaidDiagram oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.code != widget.code) {
      _sanitizedCode = sanitizeMermaid(widget.code);
    }
  }

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.code));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  String _getMermaidImageUrl({String format = 'png'}) {
    final cleanCode = _sanitizedCode;
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
        code: _sanitizedCode,
        palette: widget.palette,
        imageUrl: _getMermaidImageUrl(format: 'png'),
        onDownload: _downloadImage,
      ),
    );
  }

  String _generateHtml() {
    // Use pre-sanitized code. Mermaid.js expects raw syntax inside <pre>,
    // so do NOT HTML-encode arrows (-->, -.->). The _sanitizeMermaidCode
    // already stripped dangerous characters from labels.
    final cleanCode = _sanitizedCode;
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
    #error-container {
      display: none;
      color: #FF9999;
      padding: 16px;
      text-align: center;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <pre class="mermaid">
$cleanCode
  </pre>
  <div id="error-container"></div>
  <script>
    function renderDiagram() {
      if (typeof mermaid !== 'undefined') {
        mermaid.initialize({
          startOnLoad: false,
          theme: 'dark',
          securityLevel: 'loose',
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
        mermaid.run({ suppressErrors: false }).catch(function(err) {
          var errDiv = document.getElementById('error-container');
          errDiv.style.display = 'block';
          errDiv.textContent = 'Diagram render error: ' + (err.message || err);
        });
      }
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', renderDiagram);
    } else {
      renderDiagram();
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

  Widget _buildNativeVisualFlowchart(UnoPalette p) {
    final clean = sanitizeMermaid(widget.code);
    final lines = clean.split('\n');

    // Sequence diagram check
    if (clean.toLowerCase().contains('sequencediagram')) {
      final steps = <String>[];
      for (final line in lines) {
        final trimmed = line.trim();
        if (trimmed.contains('->>') || trimmed.contains('-->>')) {
          steps.add(trimmed);
        }
      }
      return Container(
        padding: const EdgeInsets.all(16),
        color: const Color(0xFF131311),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(LucideIcons.arrowRightLeft, size: 14, color: p.accent),
                const SizedBox(width: 8),
                Text(
                  'Sequence Interaction Flow',
                  style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: p.accent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text('NATIVE VIEWER', style: UnoTypography.mono(color: p.accent, fontSize: 9)),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...steps.asMap().entries.map((entry) {
              final idx = entry.key + 1;
              final step = entry.value;
              final isReturn = step.contains('-->>');
              final arrow = isReturn ? '⇠' : '⇢';
              final parts = step.split(isReturn ? '-->>' : '->>');
              final from = parts.isNotEmpty ? parts[0].trim() : '';
              final rest = parts.length > 1 ? parts[1].trim() : '';
              final toAndMsg = rest.split(':');
              final to = toAndMsg.isNotEmpty ? toAndMsg[0].trim() : '';
              final msg = toAndMsg.length > 1 ? toAndMsg[1].replaceAll('"', '').trim() : '';

              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: p.bgSurface,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: p.div, width: 0.8),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 10,
                      backgroundColor: p.accent.withValues(alpha: 0.2),
                      child: Text(
                        '$idx',
                        style: UnoTypography.mono(color: p.accent, fontSize: 9, fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      from,
                      style: UnoTypography.mono(color: const Color(0xFF38BDF8), fontSize: 11, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      arrow,
                      style: TextStyle(color: p.textSec, fontSize: 14),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      to,
                      style: UnoTypography.mono(color: const Color(0xFFC678DD), fontSize: 11, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        msg,
                        style: UnoTypography.body(color: p.text, fontSize: 11.5),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      );
    }

    // Flowchart / Graph parser
    final subgraphs = <String, List<String>>{};
    String? currentSubgraph;
    final rootNodes = <String>[];
    final edges = <String>[];

    for (final line in lines) {
      final trimmed = line.trim();
      if (trimmed.startsWith('subgraph')) {
        final match = RegExp(r'subgraph\s+([a-zA-Z0-9_]+)\s*(?:\["?([^"\]]+)"?\])?').firstMatch(trimmed);
        currentSubgraph = match?.group(2) ?? match?.group(1) ?? 'Components';
        subgraphs[currentSubgraph] = [];
      } else if (trimmed == 'end') {
        currentSubgraph = null;
      } else if (trimmed.contains('-->') || trimmed.contains('-.->') || trimmed.contains('==>')) {
        edges.add(trimmed);
      } else if (trimmed.contains('[') && trimmed.contains(']')) {
        final nodeMatch = RegExp(r'([a-zA-Z0-9_]+)\["?([^"\]]+)"?\]').firstMatch(trimmed);
        if (nodeMatch != null) {
          final label = nodeMatch.group(2) ?? nodeMatch.group(1)!;
          if (currentSubgraph != null) {
            subgraphs[currentSubgraph]!.add(label);
          } else {
            rootNodes.add(label);
          }
        }
      }
    }

    return Container(
      padding: const EdgeInsets.all(16),
      color: const Color(0xFF131311),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(LucideIcons.boxes, size: 14, color: p.accent),
              const SizedBox(width: 8),
              Text(
                'Architecture Spec Topology',
                style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: p.accent.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text('NATIVE RENDER', style: UnoTypography.mono(color: p.accent, fontSize: 9)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Subgraphs list
          ...subgraphs.entries.map((entry) {
            final title = entry.key;
            final nodes = entry.value;
            final isPres = title.toLowerCase().contains('presentation') || title.toLowerCase().contains('client');
            final isApi = title.toLowerCase().contains('api') || title.toLowerCase().contains('gateway') || title.toLowerCase().contains('control');
            final isDomain = title.toLowerCase().contains('domain') || title.toLowerCase().contains('service') || title.toLowerCase().contains('routing') || title.toLowerCase().contains('synthesis');
            final isData = title.toLowerCase().contains('data') || title.toLowerCase().contains('storage') || title.toLowerCase().contains('database');

            final color = isPres
                ? const Color(0xFF38BDF8)
                : (isApi
                    ? const Color(0xFFA855F7)
                    : (isDomain
                        ? const Color(0xFF10B981)
                        : (isData ? const Color(0xFFF59E0B) : p.accent)));

            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: p.bgSurface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: color.withValues(alpha: 0.4), width: 1.0),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        title,
                        style: UnoTypography.mono(color: color, fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                  if (nodes.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: nodes.map((n) {
                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFF181816),
                            borderRadius: BorderRadius.circular(5),
                            border: Border.all(color: p.div),
                          ),
                          child: Text(
                            n,
                            style: UnoTypography.body(color: p.text, fontSize: 11),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ],
              ),
            );
          }),

          // Root components if any
          if (rootNodes.isNotEmpty) ...[
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: p.bgSurface,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: p.accent.withValues(alpha: 0.35), width: 1.0),
              ),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: rootNodes.map((n) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF181816),
                      borderRadius: BorderRadius.circular(5),
                      border: Border.all(color: p.div),
                    ),
                    child: Text(
                      n,
                      style: UnoTypography.body(color: p.text, fontSize: 11),
                    ),
                  );
                }).toList(),
              ),
            ),
          ],

          // Flow connections
          if (edges.isNotEmpty) ...[
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF181816),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: p.div, width: 0.7),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Direct Execution & Control Flows',
                    style: UnoTypography.mono(color: p.textSec, fontSize: 10, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: edges.take(8).map((edge) {
                      return Text(
                        edge.replaceAll('"', ''),
                        style: UnoTypography.mono(color: p.textSec, fontSize: 10),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ],
        ],
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
          _buildNativeVisualFlowchart(p),
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
    matrix.scaleByDouble(1.3, 1.3, 1.0, 1.0);
    _transController.value = matrix;
  }

  void _zoomOut() {
    final matrix = _transController.value.clone();
    matrix.scaleByDouble(0.77, 0.77, 1.0, 1.0);
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
