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

  String _generateHtml() {
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      background-color: transparent;
      margin: 0;
      padding: 16px;
      display: flex;
      justify-content: center;
      align-items: center;
    }
  </style>
</head>
<body>
  <pre class="mermaid">
\${widget.code.replaceAll('`', '\\\\`').replaceAll('\\\$', '\\\\\\\$')}
  </pre>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({ 
      startOnLoad: true, 
      theme: 'dark',
      themeVariables: {
        primaryColor: '#2B2822',
        primaryTextColor: '#E2E0D9',
        primaryBorderColor: '#454035',
        lineColor: '#888478',
        secondaryColor: '#4A463B',
        tertiaryColor: '#181816'
      }
    });
  </script>
</body>
</html>
''';
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
                          _copied ? 'Copied code!' : 'Copy code',
                          style: UnoTypography.mono(
                            color: _copied ? p.confirmed : p.textSec,
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
          if (_isWebViewSupported)
            SizedBox(
              height: 350,
              child: InAppWebView(
                initialData: InAppWebViewInitialData(
                  data: _generateHtml(),
                ),
                initialSettings: InAppWebViewSettings(
                  transparentBackground: true,
                  disableVerticalScroll: false,
                  disableHorizontalScroll: false,
                ),
              ),
            )
          else
            Container(
              padding: const EdgeInsets.all(24),
              alignment: Alignment.center,
              child: Column(
                children: [
                  Icon(LucideIcons.imageOff, size: 32, color: p.textSec.withOpacity(0.5)),
                  const SizedBox(height: 16),
                  Text(
                    'Inline webview not supported on this platform (Linux).',
                    style: UnoTypography.body(color: p.textSec, fontSize: 13),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Copy the code to view it in Mermaid Live Editor.',
                    style: UnoTypography.body(color: p.textSec, fontSize: 13),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
