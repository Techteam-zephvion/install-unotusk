import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class CodeViewer extends StatefulWidget {
  final String code;
  final int? highlightStartLine;
  final int? highlightEndLine;

  const CodeViewer({
    super.key,
    required this.code,
    this.highlightStartLine,
    this.highlightEndLine,
  });

  @override
  State<CodeViewer> createState() => _CodeViewerState();
}

class _CodeViewerState extends State<CodeViewer> {
  final ScrollController _verticalScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToHighlight());
  }

  @override
  void didUpdateWidget(covariant CodeViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.highlightStartLine != widget.highlightStartLine) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToHighlight());
    }
  }

  void _scrollToHighlight() {
    if (widget.highlightStartLine != null && widget.highlightStartLine! > 1) {
      if (_verticalScrollController.hasClients) {
        // Approximate 20px per line
        final targetOffset = ((widget.highlightStartLine! - 1) * 20.0).clamp(
          0.0,
          _verticalScrollController.position.maxScrollExtent,
        );
        _verticalScrollController.animateTo(
          targetOffset,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    }
  }

  @override
  void dispose() {
    _verticalScrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lines = widget.code.split('\n');

    return Container(
      decoration: BoxDecoration(
        color: AppColors.slate950,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.slate800),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(6),
        child: SingleChildScrollView(
          controller: _verticalScrollController,
          scrollDirection: Axis.vertical,
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: List.generate(lines.length, (index) {
                  final lineNumber = index + 1;
                  final isHighlighted = widget.highlightStartLine != null &&
                      widget.highlightEndLine != null &&
                      lineNumber >= widget.highlightStartLine! &&
                      lineNumber <= widget.highlightEndLine!;

                  return Container(
                    color: isHighlighted
                        ? AppColors.primary.withValues(alpha: 0.25)
                        : Colors.transparent,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Line number
                        SizedBox(
                          width: 40,
                          child: Text(
                            '$lineNumber',
                            style: AppTextStyles.code.copyWith(
                              fontSize: 12,
                              color: isHighlighted ? AppColors.primaryMuted : AppColors.slate600,
                            ),
                            textAlign: TextAlign.right,
                          ),
                        ),
                        const SizedBox(width: 16),
                        // Code line
                        Text(
                          lines[index],
                          style: AppTextStyles.code.copyWith(
                            fontSize: 12.5,
                            color: isHighlighted ? Colors.white : AppColors.slate200,
                            height: 1.3,
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
