import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class ChatGPTSettingsModal extends StatefulWidget {
  final VoidCallback onClose;
  final String defaultTab;

  const ChatGPTSettingsModal({
    super.key,
    required this.onClose,
    this.defaultTab = 'profile',
  });

  @override
  State<ChatGPTSettingsModal> createState() => _ChatGPTSettingsModalState();
}

class _ChatGPTSettingsModalState extends State<ChatGPTSettingsModal> {
  late String _activeTab;
  String _selectedReasoningTier = 'warm';
  String _selectedSpecFormat = 'bdd';
  String _selectedTheme = 'Dark';

  @override
  void initState() {
    super.initState();
    if (widget.defaultTab == 'general' || widget.defaultTab == 'settings') {
      _activeTab = 'general';
    } else if (widget.defaultTab == 'personalization' || widget.defaultTab == 'intelligence') {
      _activeTab = 'personalization';
    } else {
      _activeTab = 'profile';
    }
  }

  static const List<Map<String, dynamic>> _tabs = [
    {'id': 'profile', 'label': 'Profile', 'icon': Icons.person_outline},
    {'id': 'general', 'label': 'Appearance', 'icon': Icons.palette_outlined},
    {'id': 'personalization', 'label': 'Intelligence', 'icon': Icons.auto_awesome_outlined},
  ];

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(24),
      child: Center(
        child: Container(
          width: 760,
          height: 560,
          decoration: BoxDecoration(
            color: AppColors.bgElevated,
            border: Border.all(color: AppColors.divider),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.5),
                blurRadius: 48,
                offset: const Offset(0, 20),
              ),
            ],
          ),
          clipBehavior: Clip.antiAlias,
          child: Column(
            children: [
              // Header
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
                decoration: const BoxDecoration(
                  border: Border(bottom: BorderSide(color: AppColors.divider)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Settings',
                          style: AppTextStyles.inter(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Manage your profile, preferences, and workspace experience',
                          style: AppTextStyles.caption,
                        ),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 18),
                      color: AppColors.textSecondary,
                      onPressed: widget.onClose,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
              ),

              // Body: Left Tabs + Right Content
              Expanded(
                child: Row(
                  children: [
                    // Left Navigation
                    Container(
                      width: 200,
                      decoration: const BoxDecoration(
                        color: AppColors.bgSurface,
                        border: Border(right: BorderSide(color: AppColors.divider)),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
                      child: Column(
                        children: _tabs.map((tab) {
                          final bool isActive = _activeTab == tab['id'];
                          return InkWell(
                            onTap: () => setState(() => _activeTab = tab['id'] as String),
                            borderRadius: BorderRadius.circular(10),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              margin: const EdgeInsets.only(bottom: 4),
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                              decoration: BoxDecoration(
                                color: isActive
                                    ? AppColors.accent.withValues(alpha: 0.12)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                                border: isActive
                                    ? Border.all(color: AppColors.accent.withValues(alpha: 0.35))
                                    : Border.all(color: Colors.transparent),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    tab['icon'] as IconData,
                                    size: 16,
                                    color: isActive ? AppColors.accent : AppColors.textSecondary,
                                  ),
                                  const SizedBox(width: 10),
                                  Text(
                                    tab['label'] as String,
                                    style: AppTextStyles.inter(
                                      fontSize: 13,
                                      fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                                      color: isActive ? AppColors.textPrimary : AppColors.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),

                    // Right Content Pane
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(28),
                        child: SingleChildScrollView(
                          physics: const BouncingScrollPhysics(),
                          child: _buildTabContent(),
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

  Widget _buildTabContent() {
    switch (_activeTab) {
      case 'profile':
        return _buildProfileTab();
      case 'general':
        return _buildGeneralTab();
      case 'personalization':
      default:
        return _buildPersonalizationTab();
    }
  }

  Widget _buildProfileTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.person, size: 18, color: AppColors.accent),
            const SizedBox(width: 8),
            Text('User Profile', style: _tabHeadingStyle),
          ],
        ),
        const SizedBox(height: 16),

        // Hero Profile Card
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.bgSurface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.divider),
          ),
          child: Row(
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  color: AppColors.accent,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.accent.withValues(alpha: 0.25),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Center(
                  child: Text(
                    'DL',
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF0A0F20),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text('Dev Lead', style: AppTextStyles.inter(fontSize: 17, fontWeight: FontWeight.w700)),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                          decoration: BoxDecoration(
                            color: AppColors.live.withValues(alpha: 0.14),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppColors.live.withValues(alpha: 0.35)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 5,
                                height: 5,
                                decoration: const BoxDecoration(shape: BoxShape.circle, color: AppColors.live),
                              ),
                              const SizedBox(width: 4),
                              Text(
                                'Active',
                                style: AppTextStyles.inter(
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.live,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text('lead@acme.com', style: AppTextStyles.caption),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                      decoration: BoxDecoration(
                        color: AppColors.accent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppColors.accent.withValues(alpha: 0.28)),
                      ),
                      child: Text(
                        'LEAD ADMIN',
                        style: AppTextStyles.mono(fontSize: 10, color: AppColors.accent, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 24),

        Text(
          'WORKSPACE ACCOUNT DETAILS',
          style: AppTextStyles.mono(fontSize: 10.5, color: AppColors.textSecondary, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),

        Container(
          decoration: BoxDecoration(
            color: AppColors.bgSurface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.divider),
          ),
          child: Column(
            children: [
              _buildInfoRow('Full Name', 'Dev Lead', Icons.person_outline),
              const Divider(color: AppColors.divider, height: 1),
              _buildInfoRow('Email Address', 'lead@acme.com', Icons.mail_outline, badge: 'Verified'),
              const Divider(color: AppColors.divider, height: 1),
              _buildInfoRow('Workspace Role', 'Workspace Administrator', Icons.shield_outlined),
              const Divider(color: AppColors.divider, height: 1),
              _buildInfoRow('Organization', 'Acme Corporation', Icons.business_outlined),
            ],
          ),
        ),

        const SizedBox(height: 20),

        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.bgSurface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.divider),
          ),
          child: Row(
            children: [
              const Icon(Icons.lock_outline, size: 16, color: AppColors.accent),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Local Cryptographic Authentication', style: AppTextStyles.inter(fontSize: 12.5, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 2),
                    Text(
                      'Signed via secure local HS256 JWT tokens. Codebase intelligence and credentials remain private on your server.',
                      style: AppTextStyles.caption.copyWith(height: 1.35),
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

  Widget _buildGeneralTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.palette_outlined, size: 18, color: AppColors.accent),
            const SizedBox(width: 8),
            Text('Appearance & Interface', style: _tabHeadingStyle),
          ],
        ),
        const SizedBox(height: 6),
        Text('Select your visual workspace theme and ambiance', style: AppTextStyles.caption),
        const SizedBox(height: 20),

        Text(
          'THEME SELECTION',
          style: AppTextStyles.mono(fontSize: 10.5, color: AppColors.textSecondary, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 10),

        Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: () => setState(() => _selectedTheme = 'Dark'),
                borderRadius: BorderRadius.circular(14),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: _selectedTheme == 'Dark' ? const Color(0xFF161E32) : AppColors.bgSurface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: _selectedTheme == 'Dark' ? AppColors.accent : AppColors.divider,
                      width: _selectedTheme == 'Dark' ? 1.8 : 1.0,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.dark_mode_outlined, size: 18, color: AppColors.accent),
                      const SizedBox(height: 12),
                      Text('Warm Dark', style: AppTextStyles.inter(fontSize: 14, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 3),
                      Text('Obsidian Navy with Warm Ivory accents.', style: AppTextStyles.caption),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: InkWell(
                onTap: () => setState(() => _selectedTheme = 'Light'),
                borderRadius: BorderRadius.circular(14),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: _selectedTheme == 'Light' ? const Color(0xFFFAF7F2) : AppColors.bgSurface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: _selectedTheme == 'Light' ? AppColors.accent : AppColors.divider,
                      width: _selectedTheme == 'Light' ? 1.8 : 1.0,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.light_mode_outlined, size: 18, color: Color(0xFF181816)),
                      const SizedBox(height: 12),
                      Text('Warm Light', style: AppTextStyles.inter(fontSize: 14, fontWeight: FontWeight.w700, color: _selectedTheme == 'Light' ? const Color(0xFF181816) : null)),
                      const SizedBox(height: 3),
                      Text('Natural ivory tones with high contrast.', style: AppTextStyles.caption.copyWith(color: _selectedTheme == 'Light' ? const Color(0xFF666368) : null)),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPersonalizationTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.auto_awesome_outlined, size: 18, color: AppColors.accent),
            const SizedBox(width: 8),
            Text('Intelligence & Reasoning', style: _tabHeadingStyle),
          ],
        ),
        const SizedBox(height: 6),
        Text('Configure AI reasoning depth and output formats', style: AppTextStyles.caption),
        const SizedBox(height: 20),

        Text(
          'DEFAULT REASONING DEPTH',
          style: AppTextStyles.mono(fontSize: 10.5, color: AppColors.textSecondary, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 10),

        _buildTierRow('warm', 'Warm Tier · Multi-Signal AST (Recommended)', 'Balanced synthesis combining AST symbol hierarchy and call-graph edges.', Icons.local_fire_department_outlined, AppColors.live),
        const SizedBox(height: 8),
        _buildTierRow('cold', 'Cold Tier · Deep Proof Verification', 'Exhaustive multi-hop traversal with deterministic contract verification.', Icons.ac_unit_outlined, const Color(0xFF38BDF8)),
        const SizedBox(height: 8),
        _buildTierRow('hot', 'Hot Tier · Direct Symbol Retrieval', 'Low-latency search targeting exact symbols and interfaces.', Icons.bolt_outlined, AppColors.warning),

        const SizedBox(height: 24),

        Text(
          'SPECIFICATION OUTPUT FORMAT',
          style: AppTextStyles.mono(fontSize: 10.5, color: AppColors.textSecondary, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 10),

        Row(
          children: [
            _buildSpecChip('bdd', 'Gherkin BDD Contracts'),
            const SizedBox(width: 8),
            _buildSpecChip('adr', 'Markdown ADR Records'),
            const SizedBox(width: 8),
            _buildSpecChip('ts', 'TypeScript Interfaces'),
          ],
        ),
      ],
    );
  }

  Widget _buildTierRow(String id, String title, String desc, IconData icon, Color color) {
    final isSelected = _selectedReasoningTier == id;
    return InkWell(
      onTap: () => setState(() => _selectedReasoningTier = id),
      borderRadius: BorderRadius.circular(12),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.10) : AppColors.bgSurface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: isSelected ? color : AppColors.divider, width: isSelected ? 1.5 : 1.0),
        ),
        child: Row(
          children: [
            Icon(icon, size: 18, color: color),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: AppTextStyles.inter(fontSize: 13, fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text(desc, style: AppTextStyles.caption),
                ],
              ),
            ),
            if (isSelected) Icon(Icons.check_circle, size: 16, color: color),
          ],
        ),
      ),
    );
  }

  Widget _buildSpecChip(String id, String label) {
    final isSelected = _selectedSpecFormat == id;
    return InkWell(
      onTap: () => setState(() => _selectedSpecFormat = id),
      borderRadius: BorderRadius.circular(20),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.accent.withValues(alpha: 0.16) : AppColors.bgSurface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: isSelected ? AppColors.accent : AppColors.divider, width: isSelected ? 1.4 : 1.0),
        ),
        child: Text(
          label,
          style: AppTextStyles.inter(fontSize: 12, fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400, color: isSelected ? AppColors.textPrimary : AppColors.textSecondary),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, IconData icon, {String? badge}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Icon(icon, size: 15, color: AppColors.textSecondary),
          const SizedBox(width: 10),
          Text(label, style: AppTextStyles.inter(fontSize: 13, color: AppColors.textSecondary)),
          const Spacer(),
          if (badge != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.live.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(badge, style: AppTextStyles.mono(fontSize: 10, color: AppColors.live, fontWeight: FontWeight.w600)),
            ),
            const SizedBox(width: 8),
          ],
          Text(value, style: AppTextStyles.inter(fontSize: 13, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  TextStyle get _tabHeadingStyle => AppTextStyles.inter(
        fontSize: 16,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
      );
}
