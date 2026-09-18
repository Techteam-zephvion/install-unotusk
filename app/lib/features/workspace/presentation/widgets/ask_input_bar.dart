import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

enum ThinkingTier { hot, warm, cold }

class AskInputBar extends StatefulWidget {
  final TextEditingController controller;
  final ValueChanged<String> onSubmitted;
  final bool isGenerating;
  final String? placeholder;
  final ValueChanged<String>? onSuggestionSelect;
  final List<String> suggestions;

  const AskInputBar({
    super.key,
    required this.controller,
    required this.onSubmitted,
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
  bool _thinkingEnabled = false;
  ThinkingTier _thinkingTier = ThinkingTier.warm;
  String? _activeSearchMode; // 'research' | 'web' | null
  bool _piEnabled = false;
  bool _showSuggestions = false;

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

        // Signature Enclosed Input Container
        Stack(
          clipBehavior: Clip.none,
          children: [
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
                  // Text input field
                  TextField(
                    controller: widget.controller,
                    onChanged: (text) {
                      setState(() {
                        _showSuggestions = text.trim().isNotEmpty && widget.suggestions.isNotEmpty;
                      });
                    },
                    onSubmitted: (text) {
                      setState(() => _showSuggestions = false);
                      if (canSubmit) widget.onSubmitted(text);
                    },
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
                              onTap: () {},
                              tooltip: 'Attach context file or ticket',
                            ),
                            const SizedBox(width: 8),

                            // Thinking Mode pill
                            InkWell(
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
                              onTap: canSubmit ? () => widget.onSubmitted(widget.controller.text) : null,
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

            // Plus Dropdown Popup Menu (anchored above)
            if (_plusOpen)
              Positioned(
                bottom: 60,
                left: 0,
                child: _buildPlusDropdown(),
              ),

            // Thinking Dropdown Popup Menu (anchored above)
            if (_thinkingOpen)
              Positioned(
                bottom: 60,
                left: 80,
                child: _buildThinkingDropdown(),
              ),

            // Auto-suggestions dropdown
            if (_showSuggestions)
              Positioned(
                bottom: 60,
                left: 0,
                right: 0,
                child: _buildSuggestionsMenu(),
              ),
          ],
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
            icon: Icons.attach_file,
            title: 'Upload files',
            onTap: () => setState(() => _plusOpen = false),
          ),
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
                  value: _thinkingEnabled,
                  onChanged: (v) => setState(() => _thinkingEnabled = v),
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
      onTap: () {
        setState(() {
          _thinkingTier = tier;
          _thinkingEnabled = true;
          _thinkingOpen = false;
        });
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
