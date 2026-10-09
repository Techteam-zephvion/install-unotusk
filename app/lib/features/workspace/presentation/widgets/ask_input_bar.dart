import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

enum ThinkingTier { hot, warm, cold }

class AskInputBar extends StatefulWidget {
  final TextEditingController controller;
  final ValueChanged<String>? onSubmitted;
  final void Function(String text, ThinkingTier tier)? onSubmittedWithTier;
  final ValueChanged<ThinkingTier>? onTierChanged;
  final ThinkingTier initialTier;
  final bool isGenerating;
  final String? placeholder;
  final ValueChanged<String>? onSuggestionSelect;
  final List<String> suggestions;

  const AskInputBar({
    super.key,
    required this.controller,
    this.onSubmitted,
    this.onSubmittedWithTier,
    this.onTierChanged,
    this.initialTier = ThinkingTier.warm,
    this.isGenerating = false,
    this.placeholder,
    this.onSuggestionSelect,
    this.suggestions = const [],
  });

  @override
  State<AskInputBar> createState() => _AskInputBarState();
}

class _AskInputBarState extends State<AskInputBar> {
  bool _plusOpen = false;
  bool _thinkingOpen = false;
  bool _thinkingEnabled = true;
  late ThinkingTier _thinkingTier;
  String? _activeSearchMode; // 'research' | 'web' | null
  bool _piEnabled = false;
  bool _showSuggestions = false;
  final List<String> _attachedFileNames = [];

  Future<void> _handlePickFiles() async {
    try {
      final result = await FilePicker.pickFiles(
        type: FileType.any,
      );
      if (result.isNotEmpty) {
        setState(() {
          for (final f in result) {
            if (f.name.isNotEmpty && !_attachedFileNames.contains(f.name)) {
              _attachedFileNames.add(f.name);
            }
          }
        });
      }
    } catch (e) {
      debugPrint('File picker error: $e');
    }
  }

  @override
  void initState() {
    super.initState();
    _thinkingTier = widget.initialTier;
  }

  @override
  void didUpdateWidget(AskInputBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialTier != oldWidget.initialTier) {
      _thinkingTier = widget.initialTier;
    }
  }

  Color get _thinkingColor {
    switch (_thinkingTier) {
      case ThinkingTier.hot:
        return AppColors.modeHot;
      case ThinkingTier.warm:
        return AppColors.modeWarm;
      case ThinkingTier.cold:
        return AppColors.modeCold;
    }
  }

  String get _thinkingLabel {
    switch (_thinkingTier) {
      case ThinkingTier.hot:
        return 'Hot';
      case ThinkingTier.warm:
        return 'Warm';
      case ThinkingTier.cold:
        return 'Cold';
    }
  }

  void _submit(String text) {
    if (widget.controller.text.trim().isEmpty || widget.isGenerating) return;
    setState(() {
      _showSuggestions = false;
      _attachedFileNames.clear();
    });
    final effectiveTier = _thinkingEnabled ? _thinkingTier : ThinkingTier.warm;
    if (widget.onSubmittedWithTier != null) {
      widget.onSubmittedWithTier!(text, effectiveTier);
    } else if (widget.onSubmitted != null) {
      widget.onSubmitted!(text);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool canSubmit = widget.controller.text.trim().isNotEmpty && !widget.isGenerating;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Active search mode pill
        if (_activeSearchMode != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: (_activeSearchMode == 'research' ? AppColors.neutral : AppColors.accent)
                        .withValues(alpha: 0.15),
                    border: Border.all(
                      color: (_activeSearchMode == 'research' ? AppColors.neutral : AppColors.accent)
                          .withValues(alpha: 0.4),
                    ),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        _activeSearchMode == 'research' ? Icons.menu_book : Icons.public,
                        size: 12,
                        color: _activeSearchMode == 'research' ? AppColors.neutral : AppColors.accent,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _activeSearchMode == 'research' ? 'Research' : 'Web Search',
                        style: AppTextStyles.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: _activeSearchMode == 'research' ? AppColors.neutral : AppColors.accent,
                        ),
                      ),
                      const SizedBox(width: 4),
                      InkWell(
                        onTap: () => setState(() => _activeSearchMode = null),
                        child: Icon(
                          Icons.close,
                          size: 12,
                          color: _activeSearchMode == 'research' ? AppColors.neutral : AppColors.accent,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

        if (_plusOpen)
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: _buildPlusDropdown(),
            ),
          ),
        if (_thinkingOpen)
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: const EdgeInsets.only(left: 80, bottom: 8),
              child: _buildThinkingDropdown(),
            ),
          ),
        if (_showSuggestions)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _buildSuggestionsMenu(),
          ),

        // Signature Enclosed Input Container
        Container(
              decoration: BoxDecoration(
                color: AppColors.bgElevated,
                border: Border.all(color: AppColors.divider),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.08),
                    blurRadius: 24,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              padding: const EdgeInsets.fromLTRB(16, 12, 14, 10),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Text input field with Enter submission and Shift+Enter for newline
                  Focus(
                    onKeyEvent: (node, event) {
                      if (event is KeyDownEvent) {
                        final isEnter = event.logicalKey == LogicalKeyboardKey.enter ||
                            event.logicalKey == LogicalKeyboardKey.numpadEnter;
                        if (isEnter) {
                          if (HardwareKeyboard.instance.isShiftPressed) {
                            return KeyEventResult.ignored;
                          } else {
                            if (canSubmit) {
                              _submit(widget.controller.text);
                            }
                            return KeyEventResult.handled;
                          }
                        }
                      }
                      return KeyEventResult.ignored;
                    },
                    child: TextField(
                      controller: widget.controller,
                      onChanged: (text) {
                        setState(() {
                          _showSuggestions = text.trim().isNotEmpty && widget.suggestions.isNotEmpty;
                        });
                      },
                      onSubmitted: (text) {
                        if (canSubmit) _submit(text);
                      },
                      textInputAction: TextInputAction.send,
                      style: AppTextStyles.inter(
                        fontSize: 15,
                        color: AppColors.textPrimary,
                        height: 1.5,
                      ),
                      maxLines: null,
                      decoration: InputDecoration(
                        hintText: widget.placeholder ??
                            'Ask about a merge, a ticket, or a decision on your project…',
                        hintStyle: AppTextStyles.inter(
                          fontSize: 14,
                          color: AppColors.textSecondary.withValues(alpha: 0.8),
                        ),
                        isDense: true,
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.only(bottom: 12),
                      ),
                    ),
                  ),

                  // Attached files chips
                  if (_attachedFileNames.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: _attachedFileNames.map((name) {
                          return Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: AppColors.accentMuted,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(color: AppColors.accent.withValues(alpha: 0.3)),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.attach_file, size: 12, color: AppColors.accent),
                                const SizedBox(width: 4),
                                ConstrainedBox(
                                  constraints: const BoxConstraints(maxWidth: 160),
                                  child: Text(
                                    name,
                                    style: AppTextStyles.mono(fontSize: 11, color: AppColors.textPrimary),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                InkWell(
                                  onTap: () => setState(() => _attachedFileNames.remove(name)),
                                  child: const Icon(Icons.close, size: 12, color: AppColors.textSecondary),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    ),

                  // Bottom Toolbar inside container
                  Container(
                    padding: const EdgeInsets.only(top: 6),
                    decoration: const BoxDecoration(
                      border: Border(top: BorderSide(color: Color(0x3333332E))),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Left Toolbar: + button, Paperclip, Thinking Tier
                        Row(
                          children: [
                            // Plus button
                            _buildIconBtn(
                              icon: Icons.add,
                              isActive: _plusOpen,
                              onTap: () {
                                setState(() {
                                  _plusOpen = !_plusOpen;
                                  _thinkingOpen = false;
                                });
                              },
                            ),
                            const SizedBox(width: 6),

                            // Paperclip
                            _buildIconBtn(
                              icon: Icons.attach_file,
                              onTap: _handlePickFiles,
                              tooltip: 'Attach context file or ticket',
                            ),
                            const SizedBox(width: 8),

                            // Thinking Mode pill
                            InkWell(
                              key: const Key('thinking_tier_button'),
                              onTap: () {
                                setState(() {
                                  _thinkingOpen = !_thinkingOpen;
                                  _plusOpen = false;
                                });
                              },
                              borderRadius: BorderRadius.circular(20),
                              child: Container(
                                height: 30,
                                padding: const EdgeInsets.symmetric(horizontal: 11),
                                decoration: BoxDecoration(
                                  color: _thinkingOpen
                                      ? AppColors.accent.withValues(alpha: 0.12)
                                      : Colors.transparent,
                                  border: Border.all(
                                    color: _thinkingEnabled
                                        ? _thinkingColor.withValues(alpha: 0.6)
                                        : AppColors.divider,
                                  ),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.bolt,
                                      size: 13,
                                      color: _thinkingEnabled ? _thinkingColor : AppColors.textSecondary,
                                    ),
                                    const SizedBox(width: 5),
                                    Text(
                                      _thinkingEnabled ? '$_thinkingLabel tier' : 'Thinking',
                                      style: AppTextStyles.inter(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w500,
                                        color: _thinkingEnabled ? _thinkingColor : AppColors.textSecondary,
                                      ),
                                    ),
                                    const SizedBox(width: 4),
                                    Icon(
                                      Icons.keyboard_arrow_down,
                                      size: 13,
                                      color: _thinkingEnabled ? _thinkingColor : AppColors.textSecondary,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),

                        // Right Toolbar: Mic & Terracotta Round Send Button
                        Row(
                          children: [
                            _buildIconBtn(
                              icon: Icons.mic_none,
                              onTap: () {},
                            ),
                            const SizedBox(width: 8),

                            // Round Send Button
                            InkWell(
                              key: const Key('ask_submit_button'),
                              onTap: canSubmit ? () => _submit(widget.controller.text) : null,
                              borderRadius: BorderRadius.circular(16),
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 150),
                                width: 32,
                                height: 32,
                                decoration: BoxDecoration(
                                  color: canSubmit ? AppColors.accent : AppColors.divider,
                                  shape: BoxShape.circle,
                                ),
                                child: Center(
                                  child: Icon(
                                    Icons.arrow_upward,
                                    size: 16,
                                    color: canSubmit ? Colors.white : AppColors.textSecondary,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
      ],
    );
  }

  Widget _buildIconBtn({
    required IconData icon,
    required VoidCallback onTap,
    bool isActive = false,
    String? tooltip,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 30,
        height: 30,
        decoration: BoxDecoration(
          border: Border.all(color: isActive ? AppColors.accent : AppColors.divider),
          borderRadius: BorderRadius.circular(8),
          color: isActive ? AppColors.accent.withValues(alpha: 0.12) : Colors.transparent,
        ),
        child: Center(
          child: Icon(
            icon,
            size: 15,
            color: isActive ? AppColors.accent : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildPlusDropdown() {
    return Container(
      width: 220,
      decoration: BoxDecoration(
        color: AppColors.bgElevated,
        border: Border.all(color: AppColors.divider),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 28,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildDropdownItem(
            icon: Icons.create_new_folder_outlined,
            title: 'Add to project',
            hasChevron: true,
            onTap: () {},
          ),
          _buildDropdownItem(
            icon: Icons.extension_outlined,
            title: 'Connectors',
            hasChevron: true,
            onTap: () {},
          ),
          const Divider(color: AppColors.divider, height: 8),
          _buildDropdownItem(
            icon: Icons.menu_book_outlined,
            title: 'Research mode',
            onTap: () {
              setState(() {
                _activeSearchMode = 'research';
                _plusOpen = false;
              });
            },
          ),
          _buildDropdownItem(
            icon: Icons.public,
            title: 'Web Search',
            onTap: () {
              setState(() {
                _activeSearchMode = 'web';
                _plusOpen = false;
              });
            },
          ),
          const Divider(color: AppColors.divider, height: 8),
          // Personal Intelligence toggle
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Row(
              children: [
                Icon(
                  Icons.electric_bolt,
                  size: 14,
                  color: _piEnabled ? AppColors.accent : AppColors.textSecondary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Personal Intelligence',
                    style: AppTextStyles.inter(
                      fontSize: 12,
                      color: _piEnabled ? AppColors.textPrimary : AppColors.textSecondary,
                    ),
                  ),
                ),
                Switch(
                  value: _piEnabled,
                  onChanged: (v) => setState(() => _piEnabled = v),
                  activeThumbColor: AppColors.accent,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildThinkingDropdown() {
    return Container(
      width: 210,
      decoration: BoxDecoration(
        color: AppColors.bgElevated,
        border: Border.all(color: AppColors.divider),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.35),
            blurRadius: 28,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Thinking Toggle
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppColors.divider)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Thinking',
                  style: AppTextStyles.inter(fontSize: 13, fontWeight: FontWeight.w500),
                ),
                Switch(
                  key: const Key('thinking_toggle_switch'),
                  value: _thinkingEnabled,
                  onChanged: (v) {
                    setState(() => _thinkingEnabled = v);
                    widget.onTierChanged?.call(v ? _thinkingTier : ThinkingTier.warm);
                  },
                  activeThumbColor: AppColors.accent,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ],
            ),
          ),

          // Temperature tiers
          _buildTierOption(ThinkingTier.hot, 'Hot', 'Quick answers', AppColors.modeHot),
          _buildTierOption(ThinkingTier.warm, 'Warm', 'Balanced', AppColors.modeWarm),
          _buildTierOption(ThinkingTier.cold, 'Cold', 'Deep reasoning', AppColors.modeCold),
        ],
      ),
    );
  }

  Widget _buildTierOption(ThinkingTier tier, String title, String desc, Color color) {
    final bool isSelected = _thinkingTier == tier && _thinkingEnabled;

    return InkWell(
      key: Key('thinking_tier_${tier.name}'),
      onTap: () {
        setState(() {
          _thinkingTier = tier;
          _thinkingEnabled = true;
          _thinkingOpen = false;
        });
        widget.onTierChanged?.call(tier);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.12) : Colors.transparent,
          border: Border(
            left: BorderSide(
              color: isSelected ? color : Colors.transparent,
              width: 3,
            ),
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(shape: BoxShape.circle, color: color),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTextStyles.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: isSelected ? color : AppColors.textPrimary,
                  ),
                ),
                Text(
                  desc,
                  style: AppTextStyles.inter(fontSize: 11, color: AppColors.textSecondary),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDropdownItem({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
    bool hasChevron = false,
  }) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        child: Row(
          children: [
            Icon(icon, size: 14, color: AppColors.textSecondary),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                title,
                style: AppTextStyles.inter(fontSize: 13, color: AppColors.textSecondary),
              ),
            ),
            if (hasChevron)
              const Icon(Icons.chevron_right, size: 13, color: AppColors.textSecondary),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionsMenu() {
    final query = widget.controller.text.toLowerCase();
    final matching = widget.suggestions
        .where((s) => s.toLowerCase().contains(query))
        .take(4)
        .toList();

    if (matching.isEmpty) return const SizedBox.shrink();

    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgElevated,
        border: Border.all(color: AppColors.divider),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.25),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: matching.map((s) {
          return InkWell(
            onTap: () {
              widget.controller.text = s;
              setState(() => _showSuggestions = false);
              widget.onSuggestionSelect?.call(s);
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                children: [
                  const Icon(Icons.search, size: 14, color: AppColors.textSecondary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      s,
                      style: AppTextStyles.inter(fontSize: 13, color: AppColors.textPrimary),
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
