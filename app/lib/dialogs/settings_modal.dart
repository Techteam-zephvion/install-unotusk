import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class SettingsModal extends StatefulWidget {
  final UnoPalette palette;
  final bool isDark;
  final Function(bool) onThemeChange;
  final VoidCallback onClose;
  final String defaultTab;
  final UserModel user;
  final String? projectId;

  const SettingsModal({
    super.key,
    required this.palette,
    required this.isDark,
    required this.onThemeChange,
    required this.onClose,
    this.defaultTab = 'general',
    required this.user,
    this.projectId,
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

  List<Map<String, dynamic>> _connectedApps = [];
  bool _isLoadingApps = true;

  @override
  void initState() {
    super.initState();
    _activeTab = widget.defaultTab == 'settings' ? 'general' : widget.defaultTab;
    _loadConnectedApps();
  }

  Future<void> _loadConnectedApps() async {
    setState(() => _isLoadingApps = true);
    try {
      final apps = await ApiService.fetchConnectedApps(widget.projectId);
      if (mounted) {
        setState(() {
          _connectedApps = apps;
          _isLoadingApps = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoadingApps = false);
      }
    }
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
        _buildTextField('Connected Backend', ApiService.baseUrl),
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
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Connected Integrations',
                  style: UnoTypography.body(
                    color: widget.palette.text,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Real-time status synced with backend (${ApiService.serverHost})',
                  style: UnoTypography.mono(
                    color: widget.palette.textSec,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
            IconButton(
              icon: _isLoadingApps
                  ? SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: widget.palette.accent,
                      ),
                    )
                  : Icon(LucideIcons.refreshCw,
                      size: 14, color: widget.palette.textSec),
              tooltip: 'Refresh real-time status',
              onPressed: _isLoadingApps ? null : _loadConnectedApps,
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_isLoadingApps)
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 40),
              child: Column(
                children: [
                  SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color: widget.palette.accent,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Querying live server integrations...',
                    style: UnoTypography.mono(
                      color: widget.palette.textSec,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ..._connectedApps.map((app) {
            final isConnected = app['status'] == 'Connected' || app['is_connected'] == true;
            final details = app['details'] as String? ?? (isConnected ? 'Active' : 'Not configured');
            final provider = app['provider'] as String? ?? '';

            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: widget.palette.bgSurface,
                border: Border.all(color: widget.palette.div),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Container(
                          width: 32,
                          height: 32,
                          decoration: BoxDecoration(
                            color: widget.palette.bgElevated,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: widget.palette.div),
                          ),
                          child: Center(
                            child: Text(
                              (app['icon'] as String? ?? '??'),
                              style: UnoTypography.mono(
                                color: isConnected ? widget.palette.accent : widget.palette.textSec,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                app['name'] as String? ?? '',
                                style: UnoTypography.body(
                                  color: widget.palette.text,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                details,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: UnoTypography.mono(
                                  color: isConnected ? widget.palette.accent : widget.palette.textSec,
                                  fontSize: 10,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: isConnected
                              ? widget.palette.live.withValues(alpha: 0.12)
                              : widget.palette.textSec.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(
                            color: isConnected
                                ? widget.palette.live.withValues(alpha: 0.3)
                                : widget.palette.div,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: isConnected ? widget.palette.live : widget.palette.textSec,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              isConnected ? 'Connected' : 'Not connected',
                              style: UnoTypography.mono(
                                color: isConnected ? widget.palette.live : widget.palette.textSec,
                                fontSize: 10,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (provider == 'GITHUB' && !isConnected) ...[
                        const SizedBox(width: 8),
                        TextButton(
                          onPressed: _showConnectGitHubDialog,
                          style: TextButton.styleFrom(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          child: Text(
                            'Connect',
                            style: UnoTypography.mono(
                              color: widget.palette.accent,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            );
          }),
      ],
    );
  }

  void _showConnectGitHubDialog() {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: widget.palette.bgSurface,
        title: Text(
          'Connect GitHub Repository',
          style: UnoTypography.body(color: widget.palette.text, fontWeight: FontWeight.bold, fontSize: 16),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Enter a GitHub Personal Access Token (or repo owner token) to link with this project:',
              style: UnoTypography.body(color: widget.palette.textSec, fontSize: 12),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              obscureText: true,
              style: UnoTypography.mono(color: widget.palette.text, fontSize: 12),
              decoration: InputDecoration(
                hintText: 'ghp_...',
                hintStyle: UnoTypography.mono(color: widget.palette.textSec, fontSize: 12),
                filled: true,
                fillColor: widget.palette.bgElevated,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text('Cancel', style: UnoTypography.body(color: widget.palette.textSec)),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.of(ctx).pop();
              final token = controller.text.trim();
              if (token.isNotEmpty) {
                final ok = await ApiService.connectGitHub(token, widget.projectId);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(ok ? 'GitHub connected successfully!' : 'Failed to connect GitHub token'),
                      backgroundColor: ok ? widget.palette.live : widget.palette.warn,
                    ),
                  );
                  _loadConnectedApps();
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: widget.palette.accent),
            child: Text('Save Token', style: UnoTypography.body(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
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
