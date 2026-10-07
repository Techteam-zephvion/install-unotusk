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
  bool _memoryEnabled = true;
  bool _shareData = false;
  bool _mfaEnabled = false;
  String _selectedTheme = 'Dark';
  String _selectedVoice = 'Ember (Warm & Natural)';

  @override
  void initState() {
    super.initState();
    _activeTab = widget.defaultTab;
  }

  static const List<Map<String, dynamic>> _tabs = [
    {'id': 'profile', 'label': 'Profile', 'icon': Icons.person_outline},
    {'id': 'general', 'label': 'General', 'icon': Icons.settings_outlined},
    {'id': 'personalization', 'label': 'Personalization', 'icon': Icons.tune},
    {'id': 'data', 'label': 'Data controls', 'icon': Icons.folder_open_outlined},
    {'id': 'apps', 'label': 'Connected apps', 'icon': Icons.extension_outlined},
    {'id': 'security', 'label': 'Security', 'icon': Icons.shield_outlined},
  ];

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(24),
      child: Center(
        child: Container(
          width: 740,
          height: 540,
          decoration: BoxDecoration(
            color: AppColors.bgElevated,
            border: Border.all(color: AppColors.divider),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.5),
                blurRadius: 40,
                offset: const Offset(0, 16),
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
                    Text(
                      'Settings',
                      style: AppTextStyles.inter(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
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
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
                      child: Column(
                        children: _tabs.map((tab) {
                          final bool isActive = _activeTab == tab['id'];
                          return InkWell(
                            onTap: () => setState(() => _activeTab = tab['id'] as String),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 4),
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                              decoration: BoxDecoration(
                                color: isActive ? AppColors.bgElevated : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
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

                    // Right Content Panel
                    Expanded(
                      child: Container(
                        color: AppColors.bgElevated,
                        padding: const EdgeInsets.all(28),
                        child: SingleChildScrollView(
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
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('User Profile', style: _tabHeadingStyle),
            const SizedBox(height: 16),
            // Avatar row
            Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: const BoxDecoration(
                    color: AppColors.accent,
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      'ND',
                      style: AppTextStyles.inter(
                        fontSize: 20,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Naren D', style: AppTextStyles.inter(fontSize: 15, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text('naren@unotusk.com', style: AppTextStyles.caption),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 24),
            _buildInputField('Full Name', 'Naren D'),
            const SizedBox(height: 14),
            _buildInputField('Email Address', 'naren@unotusk.com'),
            const SizedBox(height: 14),
            _buildInputField('Role / Title', 'Lead AI Architect'),
          ],
        );

      case 'general':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('General Settings', style: _tabHeadingStyle),
            const SizedBox(height: 20),
            _buildSettingRow(
              label: 'Theme',
              child: PopupMenuButton<String>(
                color: AppColors.bgElevated,
                initialValue: _selectedTheme,
                onSelected: (val) => setState(() => _selectedTheme = val),
                itemBuilder: (context) => [
                  const PopupMenuItem(value: 'Dark', child: Text('Dark (Warm Slate)')),
                  const PopupMenuItem(value: 'Light', child: Text('Light')),
                  const PopupMenuItem(value: 'System', child: Text('System')),
                ],
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    border: Border.all(color: AppColors.divider),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Text(_selectedTheme, style: AppTextStyles.inter(fontSize: 13)),
                      const SizedBox(width: 6),
                      const Icon(Icons.keyboard_arrow_down, size: 14, color: AppColors.textSecondary),
                    ],
                  ),
                ),
              ),
            ),
            const Divider(color: AppColors.divider, height: 24),
            _buildSettingRow(
              label: 'Default Language',
              child: Text('English (US)', style: AppTextStyles.inter(fontSize: 13, color: AppColors.textSecondary)),
            ),
            const Divider(color: AppColors.divider, height: 24),
            _buildSettingRow(
              label: 'Voice Model',
              child: PopupMenuButton<String>(
                color: AppColors.bgElevated,
                initialValue: _selectedVoice,
                onSelected: (val) => setState(() => _selectedVoice = val),
                itemBuilder: (context) => [
                  const PopupMenuItem(value: 'Ember (Warm & Natural)', child: Text('Ember (Warm & Natural)')),
                  const PopupMenuItem(value: 'Cove (Direct & Authoritative)', child: Text('Cove (Direct & Authoritative)')),
                  const PopupMenuItem(value: 'Breeze (Crisp)', child: Text('Breeze (Crisp)')),
                ],
                child: Row(
                  children: [
                    Text(_selectedVoice, style: AppTextStyles.inter(fontSize: 13, color: AppColors.textSecondary)),
                    const SizedBox(width: 6),
                    const Icon(Icons.keyboard_arrow_down, size: 14, color: AppColors.textSecondary),
                  ],
                ),
              ),
            ),
          ],
        );

      case 'personalization':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Personalization', style: _tabHeadingStyle),
            const SizedBox(height: 20),
            _buildToggleRow(
              label: 'Memory',
              desc: 'Allow Unotusk to recall past architecture decisions and context.',
              value: _memoryEnabled,
              onChanged: (v) => setState(() => _memoryEnabled = v),
            ),
            const Divider(color: AppColors.divider, height: 24),
            _buildToggleRow(
              label: 'Deep Reasoning Default',
              desc: 'Always invoke deep ontology search for architectural queries.',
              value: true,
              onChanged: (_) {},
            ),
          ],
        );

      case 'data':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Data Controls', style: _tabHeadingStyle),
            const SizedBox(height: 20),
            _buildToggleRow(
              label: 'Telemetry & Ingestion Metrics',
              desc: 'Share anonymous usage metrics to improve graph precision.',
              value: _shareData,
              onChanged: (v) => setState(() => _shareData = v),
            ),
            const SizedBox(height: 20),
            OutlinedButton(
              onPressed: () {},
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.error,
                side: const BorderSide(color: AppColors.error),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
              child: const Text('Export Workspace Data'),
            ),
          ],
        );

      case 'security':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Security & Authentication', style: _tabHeadingStyle),
            const SizedBox(height: 20),
            _buildToggleRow(
              label: 'Two-Factor Authentication (MFA)',
              desc: 'Require TOTP authenticator app verification on login.',
              value: _mfaEnabled,
              onChanged: (v) => setState(() => _mfaEnabled = v),
            ),
            const Divider(color: AppColors.divider, height: 24),
            _buildSettingRow(
              label: 'mTLS Client Certificate',
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.live.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'ACTIVE (US-PKI)',
                  style: AppTextStyles.mono(fontSize: 10, color: AppColors.live),
                ),
              ),
            ),
          ],
        );

      default:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Connected Apps', style: _tabHeadingStyle),
            const SizedBox(height: 16),
            _buildConnectedAppItem('GitHub Enterprise', 'Connected (4 repos indexed)', Icons.code),
            const SizedBox(height: 10),
            _buildConnectedAppItem('Jira Software', 'Connected (Sync every 15m)', Icons.task_alt),
            const SizedBox(height: 10),
            _buildConnectedAppItem('Slack Workspace', 'Connected (#eng-arch)', Icons.chat_bubble_outline),
          ],
        );
    }
  }

  Widget _buildConnectedAppItem(String name, String status, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgSurface,
        border: Border.all(color: AppColors.divider),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppColors.accent),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: AppTextStyles.inter(fontSize: 13, fontWeight: FontWeight.w600)),
                Text(status, style: AppTextStyles.caption),
              ],
            ),
          ),
          Text('Manage →', style: AppTextStyles.mono(fontSize: 11, color: AppColors.accent)),
        ],
      ),
    );
  }

  Widget _buildInputField(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.caption),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: AppColors.bgSurface,
            border: Border.all(color: AppColors.divider),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(value, style: AppTextStyles.inter(fontSize: 13, color: AppColors.textPrimary)),
        ),
      ],
    );
  }

  Widget _buildSettingRow({required String label, required Widget child}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTextStyles.inter(fontSize: 14, color: AppColors.textPrimary)),
        child,
      ],
    );
  }

  Widget _buildToggleRow({
    required String label,
    required String desc,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: AppTextStyles.inter(fontSize: 14, fontWeight: FontWeight.w500)),
              const SizedBox(height: 3),
              Text(desc, style: AppTextStyles.caption),
            ],
          ),
        ),
        const SizedBox(width: 16),
        Switch(
          value: value,
          onChanged: onChanged,
          activeThumbColor: AppColors.accent,
        ),
      ],
    );
  }

  TextStyle get _tabHeadingStyle => AppTextStyles.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
      );
}
