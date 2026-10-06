import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';

class SettingsModal extends StatefulWidget {
  final UnoPalette palette;
  final bool isDark;
  final Function(bool) onThemeChange;
  final VoidCallback onClose;
  final String defaultTab;
  final UserModel user;

  const SettingsModal({
    super.key,
    required this.palette,
    required this.isDark,
    required this.onThemeChange,
    required this.onClose,
    this.defaultTab = 'general',
    required this.user,
  });

  @override
  State<SettingsModal> createState() => _SettingsModalState();
}

class _SettingsModalState extends State<SettingsModal> {
  late String _activeTab;
  bool _shareUsageData = true;
  bool _includeMetadata = true;
  bool _allowSpecMatching = true;

  final List<Map<String, dynamic>> _tabs = const [
    {'id': 'profile', 'label': 'Profile', 'icon': LucideIcons.user},
    {'id': 'general', 'label': 'General', 'icon': LucideIcons.settings},
    {'id': 'personalization', 'label': 'Personalization', 'icon': LucideIcons.sliders},
    {'id': 'data', 'label': 'Data controls', 'icon': LucideIcons.database},
    {'id': 'apps', 'label': 'Connected apps', 'icon': LucideIcons.layers},
    {'id': 'security', 'label': 'Security', 'icon': LucideIcons.shield},
  ];

  final List<Map<String, String>> _connectedApps = const [
    {'name': 'GitHub', 'status': 'Connected', 'icon': 'GH'},
    {'name': 'Jira', 'status': 'Connected', 'icon': 'JR'},
    {'name': 'Confluence', 'status': 'Connected', 'icon': 'CF'},
    {'name': 'Linear', 'status': 'Not connected', 'icon': 'LN'},
    {'name': 'Slack', 'status': 'Connected', 'icon': 'SL'},
    {'name': 'GitLab', 'status': 'Not connected', 'icon': 'GL'},
    {'name': 'PagerDuty', 'status': 'Connected', 'icon': 'PD'},
  ];

  @override
  void initState() {
    super.initState();
    _activeTab = widget.defaultTab == 'settings' ? 'general' : widget.defaultTab;
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.black.withValues(alpha: 0.55),
      child: Center(
        child: Container(
          width: 740,
          height: 540,
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: widget.palette.bgSurface,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.36),
                blurRadius: 60,
                offset: const Offset(0, 24),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 18, 20, 18),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Settings',
                      style: UnoTypography.body(
                        color: widget.palette.text,
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    IconButton(
                      icon: Icon(LucideIcons.x,
                          size: 18, color: widget.palette.textSec),
                      onPressed: widget.onClose,
                    ),
                  ],
                ),
              ),
              Divider(height: 1, thickness: 1, color: widget.palette.div),

              // Split Layout
              Expanded(
                child: Row(
                  children: [
                    // Left Tab Sidebar
                    Container(
                      width: 200,
                      decoration: BoxDecoration(
                        color: widget.palette.bgSurface,
                        border: Border(
                            right: BorderSide(color: widget.palette.div)),
                      ),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 12),
                      child: ListView(
                        children: _tabs.map((t) {
                          final active = _activeTab == t['id'];
                          return InkWell(
                            onTap: () => setState(() => _activeTab = t['id']),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              margin: const EdgeInsets.only(bottom: 3),
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 9),
                              decoration: BoxDecoration(
                                color: active
                                    ? widget.palette.bgElevated
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    t['icon'] as IconData,
                                    size: 15,
                                    color: active
                                        ? widget.palette.accent
                                        : widget.palette.textSec,
                                  ),
                                  const SizedBox(width: 10),
                                  Text(
                                    t['label'] as String,
                                    style: UnoTypography.body(
                                      color: active
                                          ? widget.palette.text
                                          : widget.palette.textSec,
                                      fontSize: 13,
                                      fontWeight: active
                                          ? FontWeight.w600
                                          : FontWeight.w400,
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
                        color: widget.palette.bgSurface,
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
        return _buildProfileTab();
      case 'general':
        return _buildGeneralTab();
      case 'personalization':
        return _buildPersonalizationTab();
      case 'data':
        return _buildDataTab();
      case 'apps':
        return _buildAppsTab();
      case 'security':
        return _buildSecurityTab();
      default:
        return _buildGeneralTab();
    }
  }

  Widget _buildProfileTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'User Profile',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: widget.palette.accent,
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  widget.user.name.trim().isNotEmpty
                      ? widget.user.name.trim().split(' ').map((s) => s.isNotEmpty ? s[0].toUpperCase() : '').take(2).join()
                      : (widget.user.email.isNotEmpty ? widget.user.email[0].toUpperCase() : 'U'),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.user.name.isNotEmpty ? widget.user.name : widget.user.email.split('@').first,
                  style: UnoTypography.body(
                    color: widget.palette.text,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    OutlinedButton(
                      onPressed: () {},
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(color: widget.palette.div),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14)),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 4),
                      ),
                      child: Text(
                        'Change picture',
                        style: UnoTypography.body(
                            color: widget.palette.text, fontSize: 12),
                      ),
                    ),
                    const SizedBox(width: 8),
                    TextButton(
                      onPressed: () {},
                      child: Text(
                        'Remove',
                        style: UnoTypography.body(
                            color: widget.palette.textSec, fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: 24),
        _buildTextField('Full Name',
            widget.user.name.isNotEmpty ? widget.user.name : widget.user.email.split('@').first),
        const SizedBox(height: 14),
        _buildTextField('Email Address',
            widget.user.email.isNotEmpty ? widget.user.email : 'lead@acme.com'),
        const SizedBox(height: 14),
        _buildTextField('Role in Workspace', widget.user.role.isNotEmpty ? widget.user.role : 'Pilot Admin'),
        const SizedBox(height: 14),
        _buildTextField('Connected Backend', 'http://10.0.0.59:28000'),
      ],
    );
  }

  Widget _buildGeneralTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Theme & Appearance',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: () => widget.onThemeChange(false),
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: !widget.isDark
                        ? widget.palette.accent.withValues(alpha: 0.08)
                        : widget.palette.bgSurface,
                    border: Border.all(
                      color: !widget.isDark
                          ? widget.palette.accent
                          : widget.palette.div,
                      width: !widget.isDark ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(LucideIcons.sun,
                          size: 16,
                          color: !widget.isDark
                              ? widget.palette.accent
                              : widget.palette.textSec),
                      const SizedBox(width: 10),
                      Text(
                        'Light Mode',
                        style: UnoTypography.body(
                          color: widget.palette.text,
                          fontWeight:
                              !widget.isDark ? FontWeight.w600 : FontWeight.w400,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: InkWell(
                onTap: () => widget.onThemeChange(true),
                borderRadius: BorderRadius.circular(12),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: widget.isDark
                        ? widget.palette.accent.withValues(alpha: 0.08)
                        : widget.palette.bgSurface,
                    border: Border.all(
                      color: widget.isDark
                          ? widget.palette.accent
                          : widget.palette.div,
                      width: widget.isDark ? 2 : 1,
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(LucideIcons.moon,
                          size: 16,
                          color: widget.isDark
                              ? widget.palette.accent
                              : widget.palette.textSec),
                      const SizedBox(width: 10),
                      Text(
                        'Dark Mode',
                        style: UnoTypography.body(
                          color: widget.palette.text,
                          fontWeight:
                              widget.isDark ? FontWeight.w600 : FontWeight.w400,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        _buildTextField('Display Language', 'English (US)'),
        const SizedBox(height: 14),
        _buildTextField('Voice Engine', 'Ember (Warm & Natural)'),
      ],
    );
  }

  Widget _buildPersonalizationTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Personalization Preferences',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Default Reasoning Tier',
          style: UnoTypography.mono(
            color: widget.palette.textSec,
            fontSize: 11,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            _buildTierChip('Warm (Balanced)', UnoPalette.queryWarm, true),
            const SizedBox(width: 8),
            _buildTierChip('Cold (Deep proof)', UnoPalette.queryCold, false),
            const SizedBox(width: 8),
            _buildTierChip('Hot (Quick lookup)', UnoPalette.queryHot, false),
          ],
        ),
        const SizedBox(height: 24),
        Text(
          'Code Generation & Spec Formats',
          style: UnoTypography.mono(
            color: widget.palette.textSec,
            fontSize: 11,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            _buildTierChip('Gherkin BDD', widget.palette.accent, true),
            const SizedBox(width: 8),
            _buildTierChip('TypeScript Contracts', widget.palette.textSec, false),
            const SizedBox(width: 8),
            _buildTierChip('Markdown ADRs', widget.palette.textSec, false),
          ],
        ),
      ],
    );
  }

  Widget _buildTierChip(String label, Color color, bool selected) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: selected ? color.withValues(alpha: 0.14) : widget.palette.bgSurface,
        border: Border.all(color: selected ? color : widget.palette.div),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: UnoTypography.body(
          color: selected ? color : widget.palette.textSec,
          fontSize: 12,
          fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
        ),
      ),
    );
  }

  Widget _buildDataTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Data & Privacy Controls',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        SwitchListTile(
          title: Text(
            'Share anonymised usage data to improve Unotusk',
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
          ),
          value: _shareUsageData,
          activeThumbColor: widget.palette.accent,
          onChanged: (val) => setState(() => _shareUsageData = val),
        ),
        SwitchListTile(
          title: Text(
            'Include project metadata in diagnostics',
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
          ),
          value: _includeMetadata,
          activeThumbColor: widget.palette.accent,
          onChanged: (val) => setState(() => _includeMetadata = val),
        ),
        SwitchListTile(
          title: Text(
            'Allow Unotusk to suggest similar specs across projects',
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
          ),
          value: _allowSpecMatching,
          activeThumbColor: widget.palette.accent,
          onChanged: (val) => setState(() => _allowSpecMatching = val),
        ),
      ],
    );
  }

  Widget _buildAppsTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Connected Integrations (Read-Only)',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 14),
        ..._connectedApps.map((app) {
          final isConnected = app['status'] == 'Connected';
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: widget.palette.bgSurface,
              border: Border.all(color: widget.palette.div),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: widget.palette.bgElevated,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Center(
                        child: Text(
                          app['icon']!,
                          style: UnoTypography.mono(
                            color: widget.palette.text,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      app['name']!,
                      style: UnoTypography.body(
                        color: widget.palette.text,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: isConnected
                        ? widget.palette.live.withValues(alpha: 0.12)
                        : widget.palette.textSec.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    app['status']!,
                    style: UnoTypography.mono(
                      color: isConnected
                          ? widget.palette.live
                          : widget.palette.textSec,
                      fontSize: 10,
                    ),
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }

  Widget _buildSecurityTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Enterprise OIDC Authentication',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: widget.palette.bgSurface,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'ACTIVE OIDC SESSION',
                style: UnoTypography.mono(
                  color: widget.palette.accent,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Issuer: https://accounts.google.com',
                style: UnoTypography.mono(color: widget.palette.text, fontSize: 12),
              ),
              const SizedBox(height: 4),
              Text(
                'Algorithm: RS256 with PKCE Code Verification',
                style: UnoTypography.mono(color: widget.palette.textSec, fontSize: 11),
              ),
              const SizedBox(height: 4),
              Text(
                'Claims: openid, profile, email, org, groups',
                style: UnoTypography.mono(color: widget.palette.textSec, fontSize: 11),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTextField(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 4),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            value,
            style: UnoTypography.body(
              color: widget.palette.text,
              fontSize: 13,
            ),
          ),
        ),
      ],
    );
  }
}
