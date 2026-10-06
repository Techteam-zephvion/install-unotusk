import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
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

  List<ProjectMember> _members = [];
  bool _loadingMembers = false;
  String? _membersError;
  late final TextEditingController _serverController;

  final List<Map<String, dynamic>> _tabs = const [
    {'id': 'personalization', 'label': 'Personalization', 'icon': LucideIcons.sliders},
    {'id': 'profile', 'label': 'Profile', 'icon': LucideIcons.user},
    {'id': 'members', 'label': 'Workspace RBAC', 'icon': LucideIcons.users},
    {'id': 'settings', 'label': 'Settings & Network', 'icon': LucideIcons.settings},
    {'id': 'support', 'label': 'Support', 'icon': LucideIcons.lifeBuoy},
  ];

  @override
  void initState() {
    super.initState();
    _activeTab = widget.defaultTab;
    _serverController = TextEditingController(text: ApiService.baseUrl);
    _loadMembers();
  }

  @override
  void dispose() {
    _serverController.dispose();
    super.dispose();
  }

  Future<void> _loadMembers() async {
    setState(() {
      _loadingMembers = true;
      _membersError = null;
    });
    try {
      final members = await ApiService.fetchProjectMembers();
      if (mounted) {
        setState(() {
          _members = members;
          _loadingMembers = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _membersError = e.toString();
          _loadingMembers = false;
        });
      }
    }
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
      case 'members':
        return _buildMembers();
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
        _buildInfoField('ACTIVE BACKEND', 'http://10.0.0.59:28000'),
      ],
    );
  }

  Widget _buildMembers() {
    final emailCtrl = TextEditingController();
    String selectedRole = 'MEMBER';
    bool isSubmitting = false;

    return StatefulBuilder(
      builder: (context, setMemberState) {
        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Workspace RBAC & Team Access',
                        style: UnoTypography.body(
                          color: widget.palette.text,
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Phase 1 Role-Based Access Control · Dynamic Data Plane Isolation (28100-28999 Pool)',
                        style: UnoTypography.mono(
                          color: widget.palette.textSec,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                  InkWell(
                    onTap: _loadMembers,
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: widget.palette.bgElevated,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: widget.palette.div),
                      ),
                      child: Row(
                        children: [
                          Icon(LucideIcons.refreshCw, size: 13, color: widget.palette.accent),
                          const SizedBox(width: 6),
                          Text('Refresh', style: UnoTypography.body(color: widget.palette.accent, fontSize: 12)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Divider(color: widget.palette.div),
              const SizedBox(height: 16),

              // Security Guardrails Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: widget.palette.bgSurface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: widget.palette.div),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: widget.palette.live.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(LucideIcons.shieldCheck, size: 20, color: widget.palette.live),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Control Plane (Port 28000) · Data Plane Isolation Guardrails Active',
                            style: UnoTypography.body(color: widget.palette.text, fontSize: 13, fontWeight: FontWeight.w600),
                          ),
                          Text(
                            'Cross-project boundaries are cryptographically isolated. Member queries are scoped to assigned projects.',
                            style: UnoTypography.body(color: widget.palette.textSec, fontSize: 11.5),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),
              Text(
                'WORKSPACE MEMBERS',
                style: UnoTypography.mono(color: widget.palette.textSec, fontSize: 10.5, letterSpacing: 0.8),
              ),
              const SizedBox(height: 10),

              if (_membersError != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.redAccent.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.redAccent.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(LucideIcons.alertCircle, color: Colors.redAccent, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(_membersError!,
                            style: UnoTypography.body(color: Colors.redAccent, fontSize: 12)),
                      ),
                      IconButton(
                        icon: const Icon(LucideIcons.refreshCw, size: 14),
                        onPressed: _loadMembers,
                        tooltip: 'Retry',
                      ),
                    ],
                  ),
                ),

              if (_loadingMembers)
                Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: CircularProgressIndicator(color: widget.palette.accent, strokeWidth: 2),
                  ),
                )
              else if (_members.isEmpty)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: widget.palette.bgSurface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: widget.palette.div),
                  ),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 16,
                        backgroundColor: widget.palette.accent,
                        child: const Text('A', style: TextStyle(color: Colors.white, fontSize: 12)),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(widget.user.email.isNotEmpty ? widget.user.email : 'lead@acme.com',
                                style: UnoTypography.body(color: widget.palette.text, fontSize: 13, fontWeight: FontWeight.w600)),
                            Text('Workspace Owner · Full Administrative Rights',
                                style: UnoTypography.mono(color: widget.palette.textSec, fontSize: 11)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: widget.palette.accent.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: widget.palette.accent.withValues(alpha: 0.3)),
                        ),
                        child: Text('ADMIN', style: UnoTypography.mono(color: widget.palette.accent, fontSize: 10, fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                )
              else
                ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: _members.length,
                  separatorBuilder: (context, index) => const SizedBox(height: 8),
                  itemBuilder: (context, idx) {
                    final m = _members[idx];
                    return Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: widget.palette.bgSurface,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: widget.palette.div),
                      ),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 15,
                            backgroundColor: widget.palette.accent,
                            child: Text(
                              (m.userEmail?.isNotEmpty == true
                                      ? m.userEmail![0]
                                      : m.userName?.isNotEmpty == true
                                          ? m.userName![0]
                                          : 'U')
                                  .toUpperCase(),
                              style: const TextStyle(color: Colors.white, fontSize: 12),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  m.userEmail ?? m.userName ?? m.userId,
                                  style: UnoTypography.body(color: widget.palette.text, fontSize: 13, fontWeight: FontWeight.w500),
                                ),
                                if (m.userName != null && m.userEmail != null)
                                  Text(m.userName!, style: UnoTypography.body(color: widget.palette.textSec, fontSize: 11)),
                              ],
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: m.isAdmin
                                  ? widget.palette.accent.withValues(alpha: 0.12)
                                  : widget.palette.live.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(
                                color: m.isAdmin
                                    ? widget.palette.accent.withValues(alpha: 0.3)
                                    : widget.palette.live.withValues(alpha: 0.3),
                              ),
                            ),
                            child: Text(
                              m.role,
                              style: UnoTypography.mono(
                                color: m.isAdmin ? widget.palette.accent : widget.palette.live,
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            icon: Icon(LucideIcons.trash2, size: 14, color: widget.palette.textSec),
                            onPressed: () async {
                              try {
                                await ApiService.removeProjectMember(m.userId);
                                await _loadMembers();
                              } catch (_) {}
                            },
                          ),
                        ],
                      ),
                    );
                  },
                ),

              const SizedBox(height: 24),
              Text(
                'INVITE NEW MEMBER',
                style: UnoTypography.mono(color: widget.palette.textSec, fontSize: 10.5, letterSpacing: 0.8),
              ),
              const SizedBox(height: 10),

              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: emailCtrl,
                      style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'teammate@acme.com',
                        hintStyle: UnoTypography.body(color: widget.palette.textSec.withValues(alpha: 0.6), fontSize: 12.5),
                        filled: true,
                        fillColor: widget.palette.bgElevated,
                        isDense: true,
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: widget.palette.div)),
                        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: widget.palette.div)),
                        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: widget.palette.accent)),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  DropdownButtonHideUnderline(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                      decoration: BoxDecoration(
                        color: widget.palette.bgElevated,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: widget.palette.div),
                      ),
                      child: DropdownButton<String>(
                        value: selectedRole,
                        dropdownColor: widget.palette.bgSurface,
                        items: ['ADMIN', 'MEMBER', 'VIEWER'].map((r) {
                          return DropdownMenuItem(value: r, child: Text(r, style: UnoTypography.mono(color: widget.palette.text, fontSize: 11)));
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) setMemberState(() => selectedRole = val);
                        },
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  ElevatedButton(
                    onPressed: isSubmitting
                        ? null
                        : () async {
                            final email = emailCtrl.text.trim();
                            if (email.isEmpty) return;
                            setMemberState(() => isSubmitting = true);
                            try {
                              await ApiService.addProjectMember(email: email, role: selectedRole);
                              emailCtrl.clear();
                              await _loadMembers();
                            } catch (_) {}
                            setMemberState(() => isSubmitting = false);
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: widget.palette.accent,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: Text('Assign Role', style: UnoTypography.body(fontSize: 12.5, fontWeight: FontWeight.w600, color: Colors.white)),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSettings() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Settings & Network',
            style: UnoTypography.body(
              color: widget.palette.text,
              fontSize: 18,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Divider(color: widget.palette.div),
          const SizedBox(height: 16),

          // Backend Server URL Configuration
          Text(
            'PRIMARY BACKEND CONNECTION (PORT 28000 SERIES)',
            style: UnoTypography.mono(color: widget.palette.textSec, fontSize: 10.5, letterSpacing: 0.8),
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: widget.palette.bgSurface,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: widget.palette.div),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _serverController,
                        style: UnoTypography.mono(color: widget.palette.text, fontSize: 13),
                        decoration: InputDecoration(
                          prefixIcon: Icon(Icons.dns_outlined, size: 16, color: widget.palette.accent),
                          isDense: true,
                          filled: true,
                          fillColor: widget.palette.bgElevated,
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: widget.palette.div)),
                          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: widget.palette.div)),
                          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: widget.palette.accent)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton(
                      onPressed: () async {
                        final newUrl = _serverController.text.trim();
                        if (newUrl.isNotEmpty) {
                          ApiService.setBaseUrl(newUrl);
                          await ApiService.checkHealth();
                          if (mounted) setState(() {});
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: widget.palette.accent,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      child: Text('Save & Connect', style: UnoTypography.body(fontSize: 12.5, fontWeight: FontWeight.w600, color: Colors.white)),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Text('Presets: ', style: UnoTypography.body(color: widget.palette.textSec, fontSize: 11.5)),
                    InkWell(
                      onTap: () {
                        _serverController.text = 'http://10.0.0.59:28000';
                        ApiService.setBaseUrl('http://10.0.0.59:28000');
                        setState(() {});
                      },
                      child: Text('LAN (10.0.0.59:28000)', style: UnoTypography.mono(color: widget.palette.accent, fontSize: 11)),
                    ),
                    const SizedBox(width: 14),
                    InkWell(
                      onTap: () {
                        _serverController.text = 'http://localhost:28000';
                        ApiService.setBaseUrl('http://localhost:28000');
                        setState(() {});
                      },
                      child: Text('Localhost (28000)', style: UnoTypography.mono(color: widget.palette.accent, fontSize: 11)),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),
          Text(
            'DATA & PRIVACY PREFERENCES',
            style: UnoTypography.mono(color: widget.palette.textSec, fontSize: 10.5, letterSpacing: 0.8),
          ),
          const SizedBox(height: 10),
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
      ),
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
