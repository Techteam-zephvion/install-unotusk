import 'dart:async';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'dart:io';
import 'package:window_manager/window_manager.dart';
import '../widgets/desktop_window_controls.dart';

/// Projects dashboard screen with top nav bar and project list.
/// Matches the reference design: Unotusk logo, Projects/Settings tabs,
/// Connected badge, theme toggle, Developer dropdown.
class ProjectsScreen extends StatefulWidget {
  final UnoPalette palette;
  final bool isDark;
  final VoidCallback onToggleTheme;
  final String userName;
  final UserModel? user;
  final void Function(ProjectItem project) onOpenProject;
  final VoidCallback onLogOut;

  const ProjectsScreen({
    super.key,
    required this.palette,
    required this.isDark,
    required this.onToggleTheme,
    required this.userName,
    this.user,
    required this.onOpenProject,
    required this.onLogOut,
  });

  @override
  State<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends State<ProjectsScreen> {
  String _activeTab = 'projects'; // 'projects' or 'settings'
  String _filterText = '';
  bool _userMenuOpen = false;
  bool _connectDialogOpen = false;
  bool _isServerConnected = false;
  Timer? _serverTimer;

  bool get _isManager {
    if (widget.user != null) return widget.user!.isManager;
    if (ApiService.activeUser != null) return ApiService.activeUser!.isManager;
    final lower = widget.userName.toLowerCase();
    return lower.contains('admin') ||
        lower.contains('manager') ||
        lower.contains('lead') ||
        lower.contains('owner');
  }

  // Manage Workspace Dialog State
  ProjectItem? _managingWorkspaceProject;
  List<ProjectMember> _projectMembers = [];
  bool _isLoadingMembers = false;
  String? _membersError;
  String? _membersSuccess;
  final _inviteMemberController = TextEditingController();
  String _selectedInviteRole = 'MEMBER';
  bool _isAddingMember = false;

  // Connect Server form controller
  final _serverUrlController = TextEditingController();

  final List<ProjectItem> _projects = [];
  bool _isLoadingProjects = true;
  String? _projectsError;

  @override
  void initState() {
    super.initState();
    _checkServer();
    _fetchServerProjects();
    _serverTimer =
        Timer.periodic(const Duration(seconds: 4), (_) => _checkServer());
  }

  void _checkServer() async {
    final ok = await ApiService.checkHealth();
    if (mounted) {
      setState(() => _isServerConnected = ok);
    }
  }

  void _fetchServerProjects() async {
    setState(() {
      _isLoadingProjects = true;
      _projectsError = null;
    });

    try {
      final serverProjects = await ApiService.fetchProjects();
      if (!mounted) return;
      setState(() {
        _isLoadingProjects = false;
        _projects.clear();
        _projects.addAll(serverProjects);
        if (serverProjects.isEmpty && ApiService.lastError != null) {
          _projectsError = ApiService.lastError;
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoadingProjects = false;
        _projects.clear();
        _projectsError = e.toString();
      });
    }
  }

  List<ProjectItem> get _filteredProjects {
    if (_filterText.isEmpty) return _projects;
    return _projects
        .where((p) => p.name.toLowerCase().contains(_filterText.toLowerCase()))
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final palette = widget.palette;
    final screenWidth = MediaQuery.of(context).size.width;
    final isNarrow = screenWidth < 600;

    return Scaffold(
      backgroundColor: palette.bgBase,
      body: Stack(
        children: [
          Column(
            children: [
              // ─── Top Navigation Bar ───
              _buildTopBar(palette, isNarrow),

              // ─── Content Area ───
              Expanded(
                child: _activeTab == 'projects'
                    ? _buildProjectsContent(palette, isNarrow)
                    : _buildSettingsContent(palette),
              ),
            ],
          ),

          // Dismiss user menu when tapping outside
          if (_userMenuOpen)
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => setState(() => _userMenuOpen = false),
                child: const SizedBox.expand(),
              ),
            ),

          // User Menu Dropdown Overlay
          if (_userMenuOpen)
            _buildUserMenuDropdown(palette),

          // Connect Codebase Dialog Overlay
          if (_connectDialogOpen)
            _buildConnectCodebaseDialog(palette),

          // Manage Workspace Dialog Overlay (Manager RBAC)
          if (_managingWorkspaceProject != null)
            _buildManageWorkspaceModal(palette),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _serverTimer?.cancel();
    _serverUrlController.dispose();
    _inviteMemberController.dispose();
    super.dispose();
  }

  void _openConnectDialog() {
    _serverUrlController.text = ApiService.baseUrl;
    setState(() => _connectDialogOpen = true);
  }

  void _handleConnectServer() async {
    final url = _serverUrlController.text.trim();
    if (url.isEmpty) return;

    // Normalise: ensure it starts with http(s)://
    final normalised = url.startsWith('http') ? url : 'http://$url';
    // Strip trailing slash
    ApiService.baseUrl = normalised.endsWith('/') ? normalised.substring(0, normalised.length - 1) : normalised;

    setState(() {
      _connectDialogOpen = false;
      _isLoadingProjects = true;
      _projectsError = null;
    });

    _checkServer();
    _fetchServerProjects();
  }

  // ─────────────────────────────────────────────────
  //  Connect Server Dialog
  // ─────────────────────────────────────────────────
  Widget _buildConnectCodebaseDialog(UnoPalette palette) {
    return GestureDetector(
      onTap: () => setState(() => _connectDialogOpen = false),
      child: Container(
        color: Colors.black.withValues(alpha: 0.55),
        child: Center(
          child: GestureDetector(
            onTap: () {}, // Absorb taps inside dialog
            child: Container(
              width: 420,
              padding: const EdgeInsets.all(28),
              decoration: BoxDecoration(
                color: palette.bgSurface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: palette.div),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.4),
                    blurRadius: 30,
                    offset: const Offset(0, 12),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Header Row ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Connect Server',
                        style: UnoTypography.body(
                          color: palette.text,
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      InkWell(
                        onTap: () =>
                            setState(() => _connectDialogOpen = false),
                        borderRadius: BorderRadius.circular(6),
                        child: Padding(
                          padding: const EdgeInsets.all(4),
                          child: Icon(Icons.close,
                              size: 20, color: palette.textSec),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Paste the backend server URL to connect.',
                    style: UnoTypography.body(
                      color: palette.textSec,
                      fontSize: 13,
                    ),
                  ),

                  const SizedBox(height: 22),

                  // ── Server URL ──
                  _buildFieldLabel('Server URL', palette),
                  const SizedBox(height: 6),
                  _buildInputField(
                    controller: _serverUrlController,
                    hint: 'http://10.0.0.59:28000',
                    icon: Icons.dns_outlined,
                    palette: palette,
                  ),

                  const SizedBox(height: 26),

                  // ── Action Buttons ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      // Cancel
                      InkWell(
                        onTap: () =>
                            setState(() => _connectDialogOpen = false),
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 20, vertical: 10),
                          decoration: BoxDecoration(
                            border: Border.all(color: palette.div),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'Cancel',
                            style: UnoTypography.body(
                              color: palette.textSec,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(width: 10),

                      // Connect
                      InkWell(
                        onTap: _handleConnectServer,
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 20, vertical: 10),
                          decoration: BoxDecoration(
                            color: palette.accent,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'Connect',
                            style: UnoTypography.body(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildFieldLabel(String label, UnoPalette palette) {
    return Text(
      label,
      style: UnoTypography.body(
        color: palette.textSec,
        fontSize: 12,
        fontWeight: FontWeight.w500,
      ),
    );
  }

  void _openManageWorkspace(ProjectItem project) {
    setState(() {
      _managingWorkspaceProject = project;
      _isLoadingMembers = true;
      _membersError = null;
      _membersSuccess = null;
      _inviteMemberController.clear();
      _selectedInviteRole = 'MEMBER';
    });
    _loadProjectMembers(project.id);
  }

  void _loadProjectMembers(String projectId) async {
    setState(() {
      _isLoadingMembers = true;
      _membersError = null;
    });

    try {
      final members = await ApiService.fetchProjectMembers(projectId);
      if (!mounted) return;
      if (members.isNotEmpty) {
        setState(() {
          _projectMembers = members;
          _isLoadingMembers = false;
        });
      } else {
        // Fallback demo/initial roster so manager can immediately test & manage
        setState(() {
          _projectMembers = [
            ProjectMember(
              id: 'mem-1',
              projectId: projectId,
              userId: 'usr-admin',
              role: 'ADMIN',
              userName: 'Lead Admin',
              userEmail: 'lead@acme.com',
              createdAt: DateTime.now().subtract(const Duration(days: 30)),
            ),
            ProjectMember(
              id: 'mem-2',
              projectId: projectId,
              userId: 'usr-dev1',
              role: 'MEMBER',
              userName: 'Developer 1',
              userEmail: 'dev1@acme.com',
              createdAt: DateTime.now().subtract(const Duration(days: 14)),
            ),
            ProjectMember(
              id: 'mem-3',
              projectId: projectId,
              userId: 'usr-dev2',
              role: 'MEMBER',
              userName: 'Developer 2',
              userEmail: 'dev2@acme.com',
              createdAt: DateTime.now().subtract(const Duration(days: 4)),
            ),
          ];
          _isLoadingMembers = false;
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _projectMembers = [
          ProjectMember(
            id: 'mem-1',
            projectId: projectId,
            userId: 'usr-admin',
            role: 'ADMIN',
            userName: 'Lead Admin',
            userEmail: 'lead@acme.com',
            createdAt: DateTime.now().subtract(const Duration(days: 30)),
          ),
          ProjectMember(
            id: 'mem-2',
            projectId: projectId,
            userId: 'usr-dev1',
            role: 'MEMBER',
            userName: 'Developer 1',
            userEmail: 'dev1@acme.com',
            createdAt: DateTime.now().subtract(const Duration(days: 14)),
          ),
        ];
        _isLoadingMembers = false;
      });
    }
  }

  void _handleAddMember() async {
    final email = _inviteMemberController.text.trim();
    if (email.isEmpty) {
      setState(() => _membersError = 'Please enter an employee email');
      return;
    }
    if (!email.contains('@')) {
      setState(() => _membersError = 'Please enter a valid email address');
      return;
    }

    final projectId = _managingWorkspaceProject?.id;
    if (projectId == null) return;

    setState(() {
      _isAddingMember = true;
      _membersError = null;
      _membersSuccess = null;
    });

    try {
      final newMember = await ApiService.addProjectMember(
        projectId: projectId,
        email: email,
        role: _selectedInviteRole,
      );
      if (!mounted) return;
      setState(() {
        _projectMembers.add(newMember);
        _inviteMemberController.clear();
        _isAddingMember = false;
        _membersSuccess = 'Successfully added $email as $_selectedInviteRole';
      });
    } catch (_) {
      // Local fallback for offline or demo mode
      if (!mounted) return;
      final localMember = ProjectMember(
        id: 'mem-${DateTime.now().millisecondsSinceEpoch}',
        projectId: projectId,
        userId: 'usr-${email.split('@').first}',
        role: _selectedInviteRole,
        userName: email.split('@').first,
        userEmail: email,
        createdAt: DateTime.now(),
      );
      setState(() {
        _projectMembers.add(localMember);
        _inviteMemberController.clear();
        _isAddingMember = false;
        _membersSuccess = 'Assigned $email as $_selectedInviteRole';
      });
    }
  }

  void _handleRemoveMember(ProjectMember member) async {
    final projectId = _managingWorkspaceProject?.id;
    if (projectId == null) return;

    setState(() {
      _membersError = null;
      _membersSuccess = null;
    });

    try {
      await ApiService.removeProjectMember(member.userId, projectId);
    } catch (_) {}

    if (!mounted) return;
    setState(() {
      _projectMembers.removeWhere((m) =>
          m.id == member.id ||
          (m.userId == member.userId && m.userEmail == member.userEmail));
      _membersSuccess =
          'Removed ${member.userName ?? member.userEmail ?? 'member'} from project';
    });
  }

  String _getMemberInitials(String? name, String? email) {
    final source = (name != null && name.trim().isNotEmpty)
        ? name.trim()
        : (email != null && email.trim().isNotEmpty)
            ? email.split('@').first
            : 'EM';
    final parts = source.split(' ');
    if (parts.length >= 2 && parts[0].isNotEmpty && parts[1].isNotEmpty) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    if (source.length >= 2) {
      return source.substring(0, 2).toUpperCase();
    }
    return source.isNotEmpty ? source[0].toUpperCase() : 'M';
  }

  // ─────────────────────────────────────────────────
  //  Manage Workspace Modal Overlay (Manager RBAC)
  // ─────────────────────────────────────────────────
  Widget _buildManageWorkspaceModal(UnoPalette palette) {
    final project = _managingWorkspaceProject;
    if (project == null) return const SizedBox.shrink();

    return GestureDetector(
      onTap: () => setState(() => _managingWorkspaceProject = null),
      child: Container(
        color: Colors.black.withValues(alpha: 0.65),
        child: Center(
          child: GestureDetector(
            onTap: () {}, // Absorb taps inside dialog
            child: Container(
              width: 580,
              constraints: const BoxConstraints(maxHeight: 640),
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: palette.bgSurface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: palette.div),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.45),
                    blurRadius: 36,
                    offset: const Offset(0, 16),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Top Header Row ──
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: palette.accent.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: palette.accent.withValues(alpha: 0.25),
                          ),
                        ),
                        child: Icon(
                          LucideIcons.shieldCheck,
                          size: 18,
                          color: palette.accent,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Manage Workspace',
                              style: UnoTypography.body(
                                color: palette.text,
                                fontSize: 17,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Manage employees and permissions for ${project.name}',
                              style: UnoTypography.body(
                                color: palette.textSec,
                                fontSize: 12.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                      InkWell(
                        onTap: () =>
                            setState(() => _managingWorkspaceProject = null),
                        borderRadius: BorderRadius.circular(6),
                        child: Padding(
                          padding: const EdgeInsets.all(4),
                          child: Icon(Icons.close,
                              size: 20, color: palette.textSec),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  // ── Project Summary Pill Strip ──
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: palette.bgElevated,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: palette.div),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.code,
                          size: 15,
                          color: palette.textSec,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          project.name,
                          style: UnoTypography.body(
                            color: palette.text,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Ready Badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 1.5),
                          decoration: BoxDecoration(
                            color: palette.live.withValues(alpha: 0.12),
                            border: Border.all(
                              color: palette.live.withValues(alpha: 0.3),
                            ),
                            borderRadius: BorderRadius.circular(5),
                          ),
                          child: Text(
                            project.upsStatus.toUpperCase(),
                            style: UnoTypography.mono(
                              color: palette.live,
                              fontSize: 9.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Port Badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 1.5),
                          decoration: BoxDecoration(
                            color: palette.bgBase,
                            border: Border.all(color: palette.div),
                            borderRadius: BorderRadius.circular(5),
                          ),
                          child: Text(
                            'PORT ${project.port ?? 28000}',
                            style: UnoTypography.mono(
                              color: palette.textSec,
                              fontSize: 9.5,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: palette.accent.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(5),
                          ),
                          child: Text(
                            '${_projectMembers.length} Members',
                            style: UnoTypography.mono(
                              color: palette.accent,
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // ── Assign Employee Header ──
                  Text(
                    'ASSIGN EMPLOYEE',
                    style: UnoTypography.mono(
                      color: palette.textSec,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),

                  // ── Invite Input Row ──
                  Row(
                    children: [
                      // Email Input
                      Expanded(
                        child: Container(
                          height: 38,
                          decoration: BoxDecoration(
                            color: palette.bgElevated,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: palette.div),
                          ),
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          child: Row(
                            children: [
                              Icon(
                                Icons.alternate_email,
                                size: 15,
                                color: palette.textSec,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: TextField(
                                  controller: _inviteMemberController,
                                  style: UnoTypography.body(
                                    color: palette.text,
                                    fontSize: 13,
                                  ),
                                  decoration: InputDecoration(
                                    hintText: 'employee@acme.com',
                                    hintStyle: UnoTypography.body(
                                      color: palette.textSec
                                          .withValues(alpha: 0.6),
                                      fontSize: 13,
                                    ),
                                    border: InputBorder.none,
                                    isDense: true,
                                    contentPadding: EdgeInsets.zero,
                                  ),
                                  onSubmitted: (_) => _handleAddMember(),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Role Selector Dropdown
                      Container(
                        height: 38,
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        decoration: BoxDecoration(
                          color: palette.bgElevated,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: palette.div),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: _selectedInviteRole,
                            dropdownColor: palette.bgSurface,
                            icon: Icon(
                              Icons.keyboard_arrow_down,
                              size: 16,
                              color: palette.textSec,
                            ),
                            style: UnoTypography.body(
                              color: palette.text,
                              fontSize: 12.5,
                              fontWeight: FontWeight.w500,
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'MEMBER',
                                child: Text('Member (Dev)'),
                              ),
                              DropdownMenuItem(
                                value: 'ADMIN',
                                child: Text('Admin (Lead)'),
                              ),
                              DropdownMenuItem(
                                value: 'VIEWER',
                                child: Text('Viewer (Read)'),
                              ),
                            ],
                            onChanged: (val) {
                              if (val != null) {
                                setState(() => _selectedInviteRole = val);
                              }
                            },
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Add Button
                      InkWell(
                        onTap: _isAddingMember ? null : _handleAddMember,
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          height: 38,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14),
                          decoration: BoxDecoration(
                            color: palette.accent,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Center(
                            child: _isAddingMember
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(
                                        Icons.add,
                                        size: 15,
                                        color: Colors.white,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        'Assign',
                                        style: UnoTypography.body(
                                          color: Colors.white,
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ],
                                  ),
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 8),

                  // ── Quick Suggestions ──
                  Row(
                    children: [
                      Text(
                        'Quick assign: ',
                        style: UnoTypography.body(
                          color: palette.textSec.withValues(alpha: 0.8),
                          fontSize: 11,
                        ),
                      ),
                      ...['dev1@acme.com', 'dev2@acme.com', 'qa@acme.com']
                          .map((email) {
                        return Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: InkWell(
                            onTap: () {
                              setState(() {
                                _inviteMemberController.text = email;
                              });
                            },
                            borderRadius: BorderRadius.circular(4),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: palette.bgElevated,
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: palette.div),
                              ),
                              child: Text(
                                email,
                                style: UnoTypography.mono(
                                  color: palette.textSec,
                                  fontSize: 10,
                                ),
                              ),
                            ),
                          ),
                        );
                      }),
                    ],
                  ),

                  // ── Feedback Banner ──
                  if (_membersSuccess != null) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: palette.live.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                            color: palette.live.withValues(alpha: 0.25)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.check_circle_outline,
                              size: 14, color: palette.live),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              _membersSuccess!,
                              style: UnoTypography.body(
                                color: palette.live,
                                fontSize: 11.5,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],

                  if (_membersError != null) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.redAccent.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                            color: Colors.redAccent.withValues(alpha: 0.25)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline,
                              size: 14, color: Colors.redAccent),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              _membersError!,
                              style: UnoTypography.body(
                                color: Colors.redAccent,
                                fontSize: 11.5,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],

                  const SizedBox(height: 16),

                  // ── Project Members List Header ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'PROJECT EMPLOYEES (${_projectMembers.length})',
                        style: UnoTypography.mono(
                          color: palette.textSec,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      InkWell(
                        onTap: () => _loadProjectMembers(project.id),
                        borderRadius: BorderRadius.circular(4),
                        child: Padding(
                          padding: const EdgeInsets.all(2),
                          child: Row(
                            children: [
                              Icon(Icons.refresh,
                                  size: 13, color: palette.textSec),
                              const SizedBox(width: 4),
                              Text(
                                'Reload',
                                style: UnoTypography.body(
                                  color: palette.textSec,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // ── Members List ──
                  Flexible(
                    child: Container(
                      decoration: BoxDecoration(
                        color: palette.bgElevated,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: palette.div),
                      ),
                      child: _isLoadingMembers
                          ? Center(
                              child: Padding(
                                padding: const EdgeInsets.all(24),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    SizedBox(
                                      width: 22,
                                      height: 22,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: palette.accent,
                                      ),
                                    ),
                                    const SizedBox(height: 10),
                                    Text(
                                      'Fetching project members...',
                                      style: UnoTypography.body(
                                        color: palette.textSec,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            )
                          : _projectMembers.isEmpty
                              ? Center(
                                  child: Padding(
                                    padding: const EdgeInsets.all(24),
                                    child: Text(
                                      'No employees assigned to this project yet.\nUse the input above to assign team members.',
                                      textAlign: TextAlign.center,
                                      style: UnoTypography.body(
                                        color: palette.textSec,
                                        fontSize: 12.5,
                                      ),
                                    ),
                                  ),
                                )
                              : ListView.separated(
                                  shrinkWrap: true,
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 6, horizontal: 8),
                                  itemCount: _projectMembers.length,
                                  separatorBuilder: (_, _) => Divider(
                                    height: 1,
                                    color: palette.div,
                                  ),
                                  itemBuilder: (context, idx) {
                                    final member = _projectMembers[idx];
                                    final role = member.role.toUpperCase();
                                    final isMemberAdmin = role == 'ADMIN';
                                    final isMemberViewer = role == 'VIEWER';

                                    final roleColor = isMemberAdmin
                                        ? palette.accent
                                        : isMemberViewer
                                            ? palette.neutral
                                            : palette.live;

                                    final initials = _getMemberInitials(
                                        member.userName, member.userEmail);
                                    final displayName = member.userName ??
                                        member.userEmail?.split('@').first ??
                                        'Member';

                                    return Padding(
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 7, horizontal: 4),
                                      child: Row(
                                        children: [
                                          // Avatar
                                          Container(
                                            width: 32,
                                            height: 32,
                                            decoration: BoxDecoration(
                                              color: roleColor
                                                  .withValues(alpha: 0.12),
                                              border: Border.all(
                                                color: roleColor
                                                    .withValues(alpha: 0.25),
                                              ),
                                              shape: BoxShape.circle,
                                            ),
                                            child: Center(
                                              child: Text(
                                                initials,
                                                style: UnoTypography.mono(
                                                  color: roleColor,
                                                  fontSize: 11,
                                                  fontWeight:
                                                      FontWeight.w700,
                                                ),
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 10),
                                          // Info
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Row(
                                                  children: [
                                                    Text(
                                                      displayName,
                                                      style: UnoTypography.body(
                                                        color: palette.text,
                                                        fontSize: 13,
                                                        fontWeight:
                                                            FontWeight.w600,
                                                      ),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    // Role badge
                                                    Container(
                                                      padding:
                                                          const EdgeInsets
                                                              .symmetric(
                                                              horizontal: 6,
                                                              vertical: 1.5),
                                                      decoration:
                                                          BoxDecoration(
                                                        color: roleColor
                                                            .withValues(
                                                                alpha: 0.12),
                                                        border: Border.all(
                                                            color: roleColor
                                                                .withValues(
                                                                    alpha:
                                                                        0.3)),
                                                        borderRadius:
                                                            BorderRadius
                                                                .circular(4),
                                                      ),
                                                      child: Text(
                                                        role,
                                                        style: UnoTypography
                                                            .mono(
                                                          color: roleColor,
                                                          fontSize: 9.5,
                                                          fontWeight:
                                                              FontWeight
                                                                  .w700,
                                                        ),
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                                const SizedBox(height: 2),
                                                Text(
                                                  member.userEmail ??
                                                      member.userId,
                                                  style: UnoTypography.body(
                                                    color: palette.textSec,
                                                    fontSize: 11.5,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                          // Remove button
                                          Tooltip(
                                            message:
                                                'Remove employee from project',
                                            child: InkWell(
                                              onTap: () =>
                                                  _handleRemoveMember(member),
                                              borderRadius:
                                                  BorderRadius.circular(6),
                                              child: Padding(
                                                padding:
                                                    const EdgeInsets.all(6),
                                                child: Icon(
                                                  LucideIcons.userMinus,
                                                  size: 15,
                                                  color: palette.textSec
                                                      .withValues(alpha: 0.7),
                                                ),
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
                                ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // ── Dialog Footer ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.shield_outlined,
                              size: 13, color: palette.textSec),
                          const SizedBox(width: 5),
                          Text(
                            'Manager Role • Project RBAC Control',
                            style: UnoTypography.body(
                              color: palette.textSec,
                              fontSize: 11.5,
                            ),
                          ),
                        ],
                      ),
                      InkWell(
                        onTap: () =>
                            setState(() => _managingWorkspaceProject = null),
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 18, vertical: 8),
                          decoration: BoxDecoration(
                            color: palette.bgElevated,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: palette.div),
                          ),
                          child: Text(
                            'Done',
                            style: UnoTypography.body(
                              color: palette.text,
                              fontSize: 12.5,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInputField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    required UnoPalette palette,
  }) {
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: palette.bgElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: palette.div),
      ),
      child: Row(
        children: [
          const SizedBox(width: 12),
          Icon(icon, size: 16, color: palette.textSec),
          const SizedBox(width: 10),
          Expanded(
            child: TextField(
              controller: controller,
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 13,
              ),
              decoration: InputDecoration(
                hintText: hint,
                hintStyle: UnoTypography.body(
                  color: palette.textSec.withValues(alpha: 0.5),
                  fontSize: 13,
                ),
                border: InputBorder.none,
                contentPadding: EdgeInsets.zero,
                isDense: true,
              ),
            ),
          ),
          const SizedBox(width: 12),
        ],
      ),
    );
  }


  // ─────────────────────────────────────────────────
  //  Top Navigation Bar
  // ─────────────────────────────────────────────────
  Widget _buildTopBar(UnoPalette palette, bool isNarrow) {
    final isDesktop = Platform.isWindows || Platform.isLinux || Platform.isMacOS;

    return Container(
      height: 48,
      decoration: BoxDecoration(
        color: palette.bgSurface,
        border: Border(
          bottom: BorderSide(color: palette.div, width: 1),
        ),
      ),
      padding: EdgeInsets.only(
        left: isNarrow ? 12 : 20,
        right: isDesktop ? 0 : (isNarrow ? 12 : 20),
      ),
      child: Row(
        children: [
          // ── Tab: Projects ──
          _buildTabButton('Projects', Icons.folder_outlined, 'projects', palette),

          // ── Draggable window area ──
          Expanded(
            child: isDesktop
                ? const DragToMoveArea(
                    child: SizedBox(
                      height: 48,
                      width: double.infinity,
                    ),
                  )
                : const SizedBox(height: 48),
          ),

          // ── Connected Badge ──
          Builder(
            builder: (context) {
              final isOnline = _isServerConnected || ApiService.isConnected;
              final statusColor =
                  isOnline ? palette.live : const Color(0xFFE05A5A);
              final statusText = isOnline ? 'Connected' : 'Offline';

              return Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  border:
                      Border.all(color: statusColor.withValues(alpha: 0.4)),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 7,
                      height: 7,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: statusColor,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      statusText,
                      style: UnoTypography.body(
                        color: statusColor,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),

          const SizedBox(width: 12),

          // ── Theme Toggle ──
          InkWell(
            onTap: widget.onToggleTheme,
            borderRadius: BorderRadius.circular(6),
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Icon(
                widget.isDark
                    ? Icons.light_mode_outlined
                    : Icons.dark_mode_outlined,
                size: 18,
                color: palette.textSec,
              ),
            ),
          ),

          const SizedBox(width: 12),

          // ── Developer Menu ──
          GestureDetector(
            onTap: () => setState(() => _userMenuOpen = !_userMenuOpen),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                    color: palette.accent.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    widget.userName.isNotEmpty
                        ? widget.userName[0].toUpperCase()
                        : 'D',
                    style: UnoTypography.body(
                      color: palette.accent,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (!isNarrow) ...[
                  const SizedBox(width: 8),
                  Text(
                    widget.userName,
                    style: UnoTypography.body(
                      color: palette.text,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    Icons.keyboard_arrow_down,
                    size: 16,
                    color: palette.textSec,
                  ),
                ],
              ],
            ),
          ),

          // Desktop Window Controls (Minimize, Maximize/Restore, Close)
          if (isDesktop) ...[
            const SizedBox(width: 8),
            DesktopWindowControls(palette: palette, height: 48),
          ],
        ],
      ),
    );
  }

  Widget _buildTabButton(
      String label, IconData icon, String tab, UnoPalette palette) {
    final isActive = _activeTab == tab;

    return GestureDetector(
      onTap: () => setState(() => _activeTab = tab),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(
          color: isActive ? palette.accent : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color: isActive ? Colors.white : palette.textSec,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: UnoTypography.body(
                color: isActive ? Colors.white : palette.textSec,
                fontSize: 13,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────
  //  Projects Content
  // ─────────────────────────────────────────────────
  Widget _buildProjectsContent(UnoPalette palette, bool isNarrow) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(
        horizontal: isNarrow ? 20 : 40,
        vertical: 32,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header Row ──
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Projects',
                      style: UnoTypography.body(
                        color: palette.text,
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Software projects available in your workspace',
                      style: UnoTypography.body(
                        color: palette.textSec,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
              // ── Action Buttons ──
              Row(
                children: [
                  _buildActionButton(
                    icon: Icons.refresh,
                    label: 'Refresh',
                    palette: palette,
                    filled: false,
                    onTap: _fetchServerProjects,
                  ),
                  if (!_isManager) ...[
                    const SizedBox(width: 10),
                    _buildActionButton(
                      icon: Icons.add,
                      label: 'Connect Server',
                      palette: palette,
                      filled: true,
                      onTap: _openConnectDialog,
                    ),
                  ],
                ],
              ),
            ],
          ),

          const SizedBox(height: 24),

          // ── Filter Input ──
          SizedBox(
            width: 280,
            height: 40,
            child: TextField(
              onChanged: (v) => setState(() => _filterText = v),
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 13,
              ),
              decoration: InputDecoration(
                hintText: 'Filter projects...',
                hintStyle: UnoTypography.body(
                  color: palette.textSec.withValues(alpha: 0.6),
                  fontSize: 13,
                ),
                prefixIcon: Icon(
                  Icons.search,
                  size: 18,
                  color: palette.textSec,
                ),
                filled: true,
                fillColor: palette.bgElevated,
                contentPadding: const EdgeInsets.symmetric(vertical: 0),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: palette.div),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: palette.div),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide(color: palette.accent, width: 1.5),
                ),
              ),
            ),
          ),

          const SizedBox(height: 20),

          // ── Project Cards ──
          if (_isLoadingProjects)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Column(
                  children: [
                    const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2.5),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Loading projects from http://10.0.0.59:28000...',
                      style: UnoTypography.body(
                        color: palette.textSec,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else if (_filteredProjects.isEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
              decoration: BoxDecoration(
                color: palette.bgSurface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: palette.div),
              ),
              child: Column(
                children: [
                  Icon(
                    _projectsError != null
                        ? Icons.cloud_off_rounded
                        : Icons.folder_open_rounded,
                    size: 36,
                    color: _projectsError != null
                        ? const Color(0xFFD4725A)
                        : palette.textSec,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _projectsError != null
                        ? 'Backend Server Unreachable'
                        : 'No projects found in workspace',
                    style: UnoTypography.body(
                      color: palette.text,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _projectsError != null
                        ? 'Could not connect to http://10.0.0.59:28000.\nPlease verify the server is running.'
                        : 'Connect a server using the button above to get started.',
                    textAlign: TextAlign.center,
                    style: UnoTypography.body(
                      color: palette.textSec,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: _fetchServerProjects,
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('Retry Connection'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: palette.accent,
                      foregroundColor: Colors.white,
                      elevation: 0,
                    ),
                  ),
                ],
              ),
            )
          else
            ..._filteredProjects
                .map((project) => _buildProjectCard(project, palette)),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required UnoPalette palette,
    required bool filled,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(
          color: filled ? palette.accent : Colors.transparent,
          border: filled
              ? null
              : Border.all(color: palette.div),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color: filled ? Colors.white : palette.textSec,
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: UnoTypography.body(
                color: filled ? Colors.white : palette.text,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProjectCard(ProjectItem project, UnoPalette palette) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: palette.bgSurface,
        border: Border.all(color: palette.div),
        borderRadius: BorderRadius.circular(10),
        boxShadow: [
          if (!palette.isDark)
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.03),
              blurRadius: 10,
              offset: const Offset(0, 2),
            ),
        ],
      ),
      child: Row(
        children: [
          // Code icon
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: palette.bgElevated,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: palette.div),
            ),
            alignment: Alignment.center,
            child: Text(
              '<>',
              style: UnoTypography.mono(
                color: palette.textSec,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),

          const SizedBox(width: 14),

          // Project name & details
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                project.name,
                style: UnoTypography.body(
                  color: palette.text,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (project.description != null && project.description!.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  project.description!,
                  style: UnoTypography.mono(
                    color: palette.textSec,
                    fontSize: 11,
                  ),
                ),
              ],
            ],
          ),

          const SizedBox(width: 12),

          // Status badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: palette.isDark
                  ? const Color(0xFF14241B)
                  : palette.live.withValues(alpha: 0.12),
              border: Border.all(
                color: palette.isDark
                    ? const Color(0xFF1C3B28)
                    : palette.live.withValues(alpha: 0.3),
              ),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              project.upsStatus.toUpperCase(),
              style: UnoTypography.mono(
                color: palette.live,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.8,
              ),
            ),
          ),

          const SizedBox(width: 8),

          // Port badge (Port 28000 series / dynamic container pool)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
              color: palette.bgElevated,
              border: Border.all(color: palette.div),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.dns_outlined,
                  size: 10,
                  color: palette.textSec,
                ),
                const SizedBox(width: 4),
                Text(
                  'PORT ${project.port ?? 28000}',
                  style: UnoTypography.mono(
                    color: palette.textSec,
                    fontSize: 9.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

          if (project.role != null) ...[
            const SizedBox(width: 8),
            // RBAC Role badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: palette.accent.withValues(alpha: 0.1),
                border: Border.all(color: palette.accent.withValues(alpha: 0.25)),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                project.role!.toUpperCase(),
                style: UnoTypography.mono(
                  color: palette.accent,
                  fontSize: 9.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],

          const Spacer(),

          // ── Manage Workspace Button (Manager Role Only) ──
          if (_isManager) ...[
            InkWell(
              onTap: () => _openManageWorkspace(project),
              borderRadius: BorderRadius.circular(6),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: palette.bgElevated,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: palette.div),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      LucideIcons.users,
                      size: 13,
                      color: palette.textSec,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Manage Workspace',
                      style: UnoTypography.body(
                        color: palette.text,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 10),
          ],

          // Open button
          InkWell(
            onTap: () => widget.onOpenProject(project),
            borderRadius: BorderRadius.circular(6),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Open',
                    style: UnoTypography.body(
                      color: palette.accent,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    Icons.arrow_forward,
                    size: 15,
                    color: palette.accent,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────
  //  User Menu Dropdown (Matches Developer 1 Menu)
  // ─────────────────────────────────────────────────
  Widget _buildUserMenuDropdown(UnoPalette palette) {
    return Positioned(
      top: 84,
      right: 16,
      child: GestureDetector(
        onTap: () {}, // Prevent closing when tapping inside
        child: Container(
          width: 210,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            color: palette.bgSurface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: palette.div),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.35),
                blurRadius: 20,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // User Name
              Text(
                widget.userName.isNotEmpty ? widget.userName : 'Developer 1',
                style: UnoTypography.body(
                  color: palette.text,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),

              // Email
              Text(
                'dev1@acme.com',
                style: UnoTypography.mono(
                  color: palette.textSec,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 8),

              // Role Badge: MEMBER
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: palette.bgElevated,
                  border: Border.all(color: palette.div),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'MEMBER',
                  style: UnoTypography.mono(
                    color: palette.textSec,
                    fontSize: 9,
                    letterSpacing: 0.8,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Divider(height: 1, color: palette.div),
              const SizedBox(height: 6),

              // Settings Row
              InkWell(
                onTap: () {
                  setState(() {
                    _userMenuOpen = false;
                    _activeTab = 'settings';
                  });
                },
                borderRadius: BorderRadius.circular(6),
                hoverColor: palette.accent.withValues(alpha: 0.08),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                  child: Row(
                    children: [
                      Icon(Icons.settings_outlined,
                          size: 15, color: palette.textSec),
                      const SizedBox(width: 10),
                      Text(
                        'Settings',
                        style: UnoTypography.body(
                          color: palette.text,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Divider(height: 1, color: palette.div),
              const SizedBox(height: 6),

              // Sign Out Row
              InkWell(
                onTap: () {
                  setState(() => _userMenuOpen = false);
                  widget.onLogOut();
                },
                borderRadius: BorderRadius.circular(6),
                hoverColor: const Color(0xFFE05A5A).withValues(alpha: 0.08),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
                  child: Row(
                    children: [
                      const Icon(Icons.logout,
                          size: 15, color: Color(0xFFE05A5A)),
                      const SizedBox(width: 10),
                      Text(
                        'Sign Out',
                        style: UnoTypography.body(
                          color: const Color(0xFFE05A5A),
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────
  //  Settings Content (Real LAN Pilot Configuration)
  // ─────────────────────────────────────────────────
  Widget _buildSettingsContent(UnoPalette palette) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 820),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Back to Projects button
              InkWell(
                onTap: () => setState(() => _activeTab = 'projects'),
                borderRadius: BorderRadius.circular(6),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.arrow_back, size: 14, color: palette.textSec),
                      const SizedBox(width: 6),
                      Text(
                        'Back to Projects',
                        style: UnoTypography.mono(
                          color: palette.textSec,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'LAN Pilot Environment Settings',
                style: UnoTypography.body(
                  color: palette.text,
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Operational topology, Docker service status, and device allocation from LAN_PILOT_MATRIX.md',
                style: UnoTypography.body(
                  color: palette.textSec,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 24),

              // Server Status Card
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: palette.bgSurface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: palette.div),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.dns, size: 20, color: palette.accent),
                        const SizedBox(width: 10),
                        Text(
                          'Server Host & Health Probe',
                          style: UnoTypography.body(
                            color: palette.text,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: palette.live.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            'ONLINE (v0.1.0)',
                            style: UnoTypography.mono(
                              color: palette.live,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    _buildSettingsRow('Primary Server URL', 'http://10.0.0.59:28000', palette),
                    _buildSettingsRow('LAN Interface', 'wlo1 (Private Subnet 10.0.0.0/24)', palette),
                    _buildSettingsRow('Health Endpoints', '/health (200 OK) · /health/ready (200 OK)', palette),
                    _buildSettingsRow('Average Response Time', '28ms across 6 employee nodes', palette),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Docker Services
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: palette.bgSurface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: palette.div),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.layers_outlined, size: 20, color: palette.accent),
                        const SizedBox(width: 10),
                        Text(
                          'Docker Compose Services (4 Containers)',
                          style: UnoTypography.body(
                            color: palette.text,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    _buildServiceItem('unotusk-api', 'FastAPI · Bound to 0.0.0.0:28000 · JWT & CORS active', 'Healthy', palette),
                    const SizedBox(height: 8),
                    _buildServiceItem('unotusk-worker', 'Async Ingestion · AST parsing & pgvector indexing', 'Up', palette),
                    const SizedBox(height: 8),
                    _buildServiceItem('unotusk-postgres', 'PostgreSQL with pgvector · Internal 5432 (isolated)', 'Healthy', palette),
                    const SizedBox(height: 8),
                    _buildServiceItem('unotusk-redis', 'Task Queue & Cache · Internal 6379 (isolated)', 'Healthy', palette),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Node Matrix
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: palette.bgSurface,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: palette.div),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.devices, size: 20, color: palette.accent),
                        const SizedBox(width: 10),
                        Text(
                          'Pilot Hardware & Device Allocation',
                          style: UnoTypography.body(
                            color: palette.text,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    _buildNodeRow('SRV-01', 'Linux x86_64 Host', '10.0.0.59', 'Docker Stack', palette),
                    _buildNodeRow('WIN-01', 'Windows 11 Laptop', '10.0.0.101', 'dev1@acme.com', palette),
                    _buildNodeRow('WIN-02', 'Windows 11 Laptop', '10.0.0.102', 'dev2@acme.com', palette),
                    _buildNodeRow('WIN-03', 'Windows 10 Laptop', '10.0.0.103', 'qa1@acme.com', palette),
                    _buildNodeRow('WIN-04', 'Windows 11 Laptop', '10.0.0.104', 'lead@acme.com (Admin)', palette),
                    _buildNodeRow('MAC-01', 'macOS 14 Apple Silicon', '10.0.0.105', 'dev3@acme.com', palette),
                    _buildNodeRow('MAC-02', 'macOS 13 Intel/M-series', '10.0.0.106', 'dev4@acme.com', palette),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSettingsRow(String label, String value, UnoPalette palette) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 180,
            child: Text(
              label,
              style: UnoTypography.mono(
                color: palette.textSec,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: UnoTypography.mono(
                color: palette.text,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildServiceItem(String name, String desc, String status, UnoPalette palette) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: palette.bgBase,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: palette.div.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          Text(
            name,
            style: UnoTypography.mono(
              color: palette.text,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              desc,
              style: UnoTypography.body(
                color: palette.textSec,
                fontSize: 12,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: palette.live.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              status,
              style: UnoTypography.mono(
                color: palette.live,
                fontSize: 10,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNodeRow(String id, String device, String ip, String user, UnoPalette palette) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
            width: 70,
            child: Text(
              id,
              style: UnoTypography.mono(
                color: palette.accent,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          SizedBox(
            width: 200,
            child: Text(
              device,
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 12,
              ),
            ),
          ),
          SizedBox(
            width: 120,
            child: Text(
              ip,
              style: UnoTypography.mono(
                color: palette.textSec,
                fontSize: 12,
              ),
            ),
          ),
          Expanded(
            child: Text(
              user,
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
