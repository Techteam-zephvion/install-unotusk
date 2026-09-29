import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';

class AdminScreen extends StatefulWidget {
  final UnoPalette palette;
  final bool isDark;
  final Function(bool) onThemeChange;
  final UserModel user;
  final String defaultTab;

  const AdminScreen({
    super.key,
    required this.palette,
    required this.isDark,
    required this.onThemeChange,
    required this.user,
    this.defaultTab = 'personalization',
  });

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  late String _activeTab;
  bool _shareUsageData = true;
  bool _includeMetadata = true;
  bool _allowSpecMatching = true;

  final List<Map<String, dynamic>> _tabs = const [
    {'id': 'personalization', 'label': 'Personalization', 'icon': LucideIcons.sliders},
    {'id': 'profile', 'label': 'Profile', 'icon': LucideIcons.user},
    {'id': 'settings', 'label': 'Settings', 'icon': LucideIcons.settings},
    {'id': 'support', 'label': 'Support', 'icon': LucideIcons.lifeBuoy},
  ];

  @override
  void initState() {
    super.initState();
    _activeTab = widget.defaultTab;
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Settings Sub-sidebar
        Container(
          width: 210,
          decoration: BoxDecoration(
            color: widget.palette.bgSurface,
            border: Border(right: BorderSide(color: widget.palette.div)),
          ),
          padding: const EdgeInsets.symmetric(vertical: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Text(
                  'SETTINGS',
                  style: UnoTypography.mono(
                    color: widget.palette.textSec,
                    fontSize: 10,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              ..._tabs.map((tab) {
                final active = _activeTab == tab['id'];
                return InkWell(
                  onTap: () => setState(() => _activeTab = tab['id']),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      color: active
                          ? widget.palette.bgElevated
                          : Colors.transparent,
                      border: Border(
                        left: BorderSide(
                          color: active
                              ? widget.palette.accent
                              : Colors.transparent,
                          width: 3,
                        ),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          tab['icon'] as IconData,
                          size: 15,
                          color: active
                              ? widget.palette.accent
                              : widget.palette.textSec,
                        ),
                        const SizedBox(width: 10),
                        Text(
                          tab['label'] as String,
                          style: UnoTypography.body(
                            color: active
                                ? widget.palette.text
                                : widget.palette.textSec,
                            fontSize: 13,
                            fontWeight:
                                active ? FontWeight.w600 : FontWeight.w400,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        ),

        // Settings Content Pane
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(36),
            child: Container(
              constraints: const BoxConstraints(maxWidth: 680),
              child: _buildTabPane(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTabPane() {
    switch (_activeTab) {
      case 'profile':
        return _buildProfile();
      case 'settings':
        return _buildSettings();
      case 'support':
        return _buildSupport();
      case 'personalization':
      default:
        return _buildPersonalization();
    }
  }

  Widget _buildPersonalization() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Personalization',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Divider(color: widget.palette.div),
        const SizedBox(height: 18),

        Text('COLOR THEME',
            style: UnoTypography.mono(
                color: widget.palette.textSec, fontSize: 10)),
        const SizedBox(height: 10),
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
                      Text('Light Palette',
                          style: UnoTypography.body(
                              color: widget.palette.text, fontSize: 13)),
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
                      Text('Dark Palette',
                          style: UnoTypography.body(
                              color: widget.palette.text, fontSize: 13)),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 28),
        Text('PRIMARY BRAND ACCENT',
            style: UnoTypography.mono(
                color: widget.palette.textSec, fontSize: 10)),
        const SizedBox(height: 10),
        Row(
          children: [
            _buildAccentColor(const Color(0xFFDA7756), true),
            _buildAccentColor(const Color(0xFF6EC8B8), false),
            _buildAccentColor(const Color(0xFFD4909A), false),
            _buildAccentColor(const Color(0xFF7B5EA7), false),
          ],
        ),
      ],
    );
  }

  Widget _buildAccentColor(Color color, bool active) {
    return Container(
      margin: const EdgeInsets.only(right: 12),
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: active ? Border.all(color: Colors.white, width: 2.5) : null,
        boxShadow: active
            ? [BoxShadow(color: color.withValues(alpha: 0.5), blurRadius: 8)]
            : null,
      ),
    );
  }

  Widget _buildProfile() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Profile',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Divider(color: widget.palette.div),
        const SizedBox(height: 18),
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
                      fontSize: 18,
                      fontWeight: FontWeight.bold),
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
                      fontSize: 15,
                      fontWeight: FontWeight.w600),
                ),
                Text(
                  widget.user.org.isNotEmpty ? widget.user.org : 'Pilot Lead Workspace',
                  style: UnoTypography.mono(
                      color: widget.palette.textSec, fontSize: 11),
                ),
              ],
            ),
          ],
        ),
        const SizedBox(height: 24),
        _buildInfoField('FULL NAME', widget.user.name.isNotEmpty ? widget.user.name : widget.user.email.split('@').first),
        const SizedBox(height: 14),
        _buildInfoField('WORK EMAIL', widget.user.email),
        const SizedBox(height: 14),
        _buildInfoField('ORGANIZATION / TEAM', widget.user.org.isNotEmpty ? widget.user.org : 'Pilot Workspace (34b9ce85)'),
        const SizedBox(height: 14),
        _buildInfoField('ACTIVE BACKEND', 'http://10.0.0.59:8000'),
      ],
    );
  }

  Widget _buildSettings() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Settings & Privacy',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Divider(color: widget.palette.div),
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

  Widget _buildSupport() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Support & Docs',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        Divider(color: widget.palette.div),
        const SizedBox(height: 18),
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: widget.palette.bgSurface,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Unotusk Project Intelligence Center',
                style: UnoTypography.body(
                    color: widget.palette.text,
                    fontSize: 14,
                    fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 6),
              Text(
                'Version 1.0 · Hybrid Lexical-Vector & Knowledge Graph Indexing',
                style: UnoTypography.mono(
                    color: widget.palette.textSec, fontSize: 11),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildInfoField(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: UnoTypography.mono(
            color: widget.palette.textSec,
            fontSize: 10,
          ),
        ),
        const SizedBox(height: 5),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            value,
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
          ),
        ),
      ],
    );
  }
}
