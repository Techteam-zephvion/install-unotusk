import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

  Future<void> _openInBrowser() async {
    final cleanCode = widget.code.trim();
    final jsonStr = jsonEncode({
      'code': cleanCode,
      'mermaid': {'theme': 'dark'},
    });
    final b64 = base64Url.encode(utf8.encode(jsonStr));
    final url = 'https://mermaid.ink/img/$b64';

    if (!kIsWeb) {
      try {
        if (Platform.isLinux) {
          await Process.run('xdg-open', [url]);
        } else if (Platform.isMacOS) {
          await Process.run('open', [url]);
        } else if (Platform.isWindows) {
          await Process.run('cmd', ['/c', 'start', '', url]);
        }
      } catch (_) {}
    }
  }

  String _getMermaidImageUrl() {
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
    return 'https://mermaid.ink/img/$b64';
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
              _getMermaidImageUrl(),
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
                    color: p.surface,
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
                const SizedBox(width: 8),
                // Copy Code Button
                InkWell(
                  onTap: _copy,
                  borderRadius: BorderRadius.circular(4),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _copied ? LucideIcons.check : LucideIcons.copy,
                          size: 13,
                          color: _copied ? p.confirmed : p.textSec,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          _copied ? 'Copied!' : 'Copy',
                          style: UnoTypography.mono(
                            color: _copied ? p.confirmed : p.textSec,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                // Open in System Browser
                InkWell(
                  onTap: _openInBrowser,
                  borderRadius: BorderRadius.circular(4),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(LucideIcons.externalLink, size: 12, color: p.textSec),
                        const SizedBox(width: 4),
                        Text(
                          'Open',
                          style: UnoTypography.mono(
                            color: p.textSec,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
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
