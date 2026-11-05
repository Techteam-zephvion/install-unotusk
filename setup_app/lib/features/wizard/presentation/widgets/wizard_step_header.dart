import 'package:flutter/material.dart';
import '../../../../core/theme/uno_palette.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../domain/wizard_step.dart';

class WizardStepHeader extends StatelessWidget {
  final WizardStep currentStep;
  final VoidCallback? onBack;
  final ValueChanged<WizardStep>? onStepTapped;

  const WizardStepHeader({
    super.key,
    required this.currentStep,
    this.onBack,
    this.onStepTapped,
  });

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);

    return Container(
      width: double.infinity,
      height: 48,
      decoration: BoxDecoration(
        color: palette.bgSurface,
        border: Border(
          bottom: BorderSide(color: palette.div),
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Centered steps pipeline across the page
          Center(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 60),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: WizardStep.values.map((step) {
                  final isCurrent = step == currentStep;
                  final isCompleted = step.index < currentStep.index;
                  final stepNum = step.index + 1;

                  Color badgeBg;
                  Color badgeText;
                  Color textColor;
                  Border? badgeBorder;

                  if (isCompleted) {
                    badgeBg = palette.live.withValues(alpha: 0.16);
                    badgeText = palette.live;
                    textColor = palette.text;
                    badgeBorder = Border.all(color: palette.live.withValues(alpha: 0.4));
                  } else if (isCurrent) {
                    badgeBg = palette.accent;
                    badgeText = Colors.white;
                    textColor = palette.text;
                  } else {
                    badgeBg = palette.bgElevated;
                    badgeText = palette.textSec;
                    textColor = palette.textSec;
                    badgeBorder = Border.all(color: palette.div);
                  }

                  final stepWidget = Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          color: badgeBg,
                          shape: BoxShape.circle,
                          border: badgeBorder,
                        ),
                        child: Center(
                          child: isCompleted
                              ? Icon(Icons.check, size: 13, color: palette.live)
                              : Text(
                                  '$stepNum',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: badgeText,
                                  ),
                                ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        step.label,
                        style: AppTextStyles.labelOf(context).copyWith(
                          color: textColor,
                          fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w500,
                          fontSize: 12.5,
                        ),
                      ),
                      if (step.index < WizardStep.values.length - 1) ...[
                        const SizedBox(width: 10),
                        Container(
                          width: 16,
                          height: 1,
                          color: isCompleted
                              ? palette.accent.withValues(alpha: 0.5)
                              : palette.div,
                        ),
                        const SizedBox(width: 10),
                      ],
                    ],
                  );

                  if (isCompleted && onStepTapped != null) {
                    return MouseRegion(
                      cursor: SystemMouseCursors.click,
                      child: GestureDetector(
                        onTap: () => onStepTapped!(step),
                        child: stepWidget,
                      ),
                    );
                  }

                  return stepWidget;
                }).toList(),
              ),
            ),
          ),

          // Complete left back button (symbol only)
          if (onBack != null)
            Positioned(
              left: 20,
              child: _StepBackBtn(
                onTap: onBack,
                palette: palette,
              ),
            ),
        ],
      ),
    );
  }
}

/// Sleek icon-only back button placed at the complete left of the page
class _StepBackBtn extends StatefulWidget {
  final VoidCallback? onTap;
  final UnoPalette palette;

  const _StepBackBtn({
    required this.onTap,
    required this.palette,
  });

  @override
  State<_StepBackBtn> createState() => _StepBackBtnState();
}

class _StepBackBtnState extends State<_StepBackBtn> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final isEnabled = widget.onTap != null;

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      cursor: isEnabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: Tooltip(
        message: 'Back',
        child: GestureDetector(
          onTap: widget.onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: _isHovered ? p.accent.withValues(alpha: 0.15) : p.bgElevated,
              border: Border.all(
                color: _isHovered ? p.accent.withValues(alpha: 0.5) : p.div,
              ),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Center(
              child: Icon(
                Icons.arrow_back_rounded,
                size: 16,
                color: _isHovered ? p.accent : p.text,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
