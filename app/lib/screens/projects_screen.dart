import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import 'dart:io';
import 'package:window_manager/window_manager.dart';
import '../widgets/desktop_window_controls.dart';
import '../widgets/unotusk_logo.dart';

/// Projects dashboard screen with top nav bar and project list.
/// Matches the reference design: Unotusk logo, Projects/Settings tabs,
/// theme toggle, Developer dropdown.
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
  bool _connectDialogOpen = false;
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
  bool _isReloadingMembers = false;
  String? _membersError;
  String? _membersSuccess;
  final _inviteMemberController = TextEditingController();
  String _selectedInviteRole = 'MEMBER';
  bool _isAddingMember = false;

  // Connect Server & Workspace State
  final _serverUrlController = TextEditingController();
  bool _connectWorkspaceDialogOpen = false;
  List<ProjectItem> _availableBackendProjects = [];
  bool _isLoadingWorkspaceProjects = false;
  bool _isRefreshingWorkspaceProjects = false;

  final List<ProjectItem> _projects = [];
  bool _isLoadingProjects = false;
  bool _isRefreshingProjects = false;

  @override
  void initState() {
    super.initState();
    // Restore any previously connected projects so they remain in workspace
    if (ApiService.connectedWorkspaceProjects.isNotEmpty) {
      _projects.addAll(ApiService.connectedWorkspaceProjects);
    } else {
      if (ApiService.connectedProjectIds.isEmpty) {
        ApiService.loadPersistedConnectedProjects();
      }
      for (final p in ApiService.cachedProjects) {
        if (ApiService.connectedProjectIds.contains(p.id) ||
            ApiService.connectedProjectIds.contains(p.name)) {
          _projects.add(p);
        }
      }
      ApiService.connectedWorkspaceProjects
        ..clear()
        ..addAll(_projects);
    }
    _checkServer();
    _fetchServerProjects(isSilent: true);
    _fetchAvailableWorkspaceProjects(isSilent: true);
    _serverTimer =
        Timer.periodic(const Duration(seconds: 4), (_) => _checkServer());
  }

  void _checkServer() async {
    await ApiService.checkHealth();
  }

  void _fetchServerProjects({bool isSilent = false}) async {
    if (_isRefreshingProjects) return;
    setState(() {
      _isRefreshingProjects = true;
    });

    final stopwatch = Stopwatch()..start();
    try {
      final serverProjects = await ApiService.fetchProjects();
      final elapsed = stopwatch.elapsedMilliseconds;
      if (elapsed < 450) {
        await Future.delayed(Duration(milliseconds: 450 - elapsed));
      }
      if (!mounted) return;
      setState(() {
        _isLoadingProjects = false;
        _isRefreshingProjects = false;
        _availableBackendProjects = serverProjects;
        // Only update status and attributes for projects explicitly connected to workspace
        for (final sp in serverProjects) {
          final isConnected = ApiService.connectedProjectIds.contains(sp.id) ||
              ApiService.connectedProjectIds.contains(sp.name);
          final idx = _projects.indexWhere((p) =>
              p.id.toLowerCase() == sp.id.toLowerCase() ||
              p.name.toLowerCase() == sp.name.toLowerCase());
          if (idx >= 0) {
            _projects[idx] = sp;
          } else if (isConnected) {
            _projects.add(sp);
          }
        }
        if (ApiService.connectedProjectIds.isNotEmpty) {
          _projects.removeWhere((p) =>
              !ApiService.connectedProjectIds.contains(p.id) &&
              !ApiService.connectedProjectIds.contains(p.name));
        }
        ApiService.connectedWorkspaceProjects
          ..clear()
          ..addAll(_projects);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoadingProjects = false;
        _isRefreshingProjects = false;
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



          // Connect Codebase Dialog Overlay
          if (_connectDialogOpen)
            _buildConnectCodebaseDialog(palette),

          // Connect Workspace Dialog Overlay (Manager RBAC)
          if (_connectWorkspaceDialogOpen)
            _buildConnectWorkspaceDialog(palette),

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

  // ignore: unused_element
  void _openConnectDialog() {
    _serverUrlController.text = ApiService.baseUrl;
    setState(() => _connectDialogOpen = true);
  }

  void _openConnectWorkspaceDialog() {
    setState(() => _connectWorkspaceDialogOpen = true);
    _fetchAvailableWorkspaceProjects();
  }

  void _fetchAvailableWorkspaceProjects({bool isSilent = false, bool isUserAction = false}) async {
    setState(() {
      _isRefreshingWorkspaceProjects = true;
      if (_availableBackendProjects.isEmpty && !isSilent) {
        _isLoadingWorkspaceProjects = true;
      }
    });

    try {
      final serverProjects = await ApiService.fetchProjects();
      if (!mounted) return;
      setState(() {
        _availableBackendProjects = serverProjects;
        // Keep any existing connected projects synchronized
        for (final sp in serverProjects) {
          final isConnected = ApiService.connectedProjectIds.contains(sp.id) ||
              ApiService.connectedProjectIds.contains(sp.name);
          final idx = _projects.indexWhere((p) =>
              p.id.toLowerCase() == sp.id.toLowerCase() ||
              p.name.toLowerCase() == sp.name.toLowerCase());
          if (idx >= 0) {
            _projects[idx] = sp;
          } else if (isConnected) {
            _projects.add(sp);
          }
        }
        ApiService.connectedWorkspaceProjects
          ..clear()
          ..addAll(_projects);
        _isLoadingWorkspaceProjects = false;
        _isRefreshingWorkspaceProjects = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          if (_availableBackendProjects.isEmpty) {
            _availableBackendProjects = ApiService.cachedProjects;
          }
          _isLoadingWorkspaceProjects = false;
          _isRefreshingWorkspaceProjects = false;
        });
      }
    }
  }

  void _toggleProjectConnection(ProjectItem project) {
    setState(() {
      final idx = _projects.indexWhere((p) =>
          p.id.toLowerCase() == project.id.toLowerCase() ||
          p.name.toLowerCase() == project.name.toLowerCase());
      if (idx >= 0) {
        _projects.removeAt(idx);
        ApiService.connectedProjectIds.remove(project.id);
        ApiService.connectedProjectIds.remove(project.name);
      } else {
        _projects.add(project);
        ApiService.connectedProjectIds.add(project.id);
        ApiService.connectedProjectIds.add(project.name);
      }
      ApiService.connectedWorkspaceProjects
        ..clear()
        ..addAll(_projects);
    });
    ApiService.savePersistedConnectedProjects();
  }

  void _connectAllWorkspaceProjects() {
    setState(() {
      for (final p in _availableBackendProjects) {
        final exists = _projects.any((item) =>
            item.id.toLowerCase() == p.id.toLowerCase() ||
            item.name.toLowerCase() == p.name.toLowerCase());
        if (!exists) {
          _projects.add(p);
        }
        ApiService.connectedProjectIds.add(p.id);
        ApiService.connectedProjectIds.add(p.name);
      }
      ApiService.connectedWorkspaceProjects
        ..clear()
        ..addAll(_projects);
    });
    ApiService.savePersistedConnectedProjects();
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

  // ─────────────────────────────────────────────────
  //  Connect Workspace Dialog (Manager RBAC)
  // ─────────────────────────────────────────────────
  Widget _buildConnectWorkspaceDialog(UnoPalette palette) {
    return GestureDetector(
      onTap: () => setState(() => _connectWorkspaceDialogOpen = false),
      child: Container(
        color: Colors.black.withValues(alpha: 0.55),
        child: Center(
          child: GestureDetector(
            onTap: () {}, // Absorb taps inside dialog
            child: Container(
              width: 540,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: palette.bgSurface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: palette.div),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.45),
                    blurRadius: 32,
                    offset: const Offset(0, 14),
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
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: palette.accent.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(
                              Icons.hub_outlined,
                              size: 20,
                              color: palette.accent,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Connect Workspace',
                                style: UnoTypography.body(
                                  color: palette.text,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                'Select backend projects to display in your workspace',
                                style: UnoTypography.body(
                                  color: palette.textSec,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                      InkWell(
                        onTap: () =>
                            setState(() => _connectWorkspaceDialogOpen = false),
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

                  // Lead Account Pill Info
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 9),
                    decoration: BoxDecoration(
                      color: palette.bgElevated,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: palette.div),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.shield_outlined,
                            size: 16, color: palette.accent),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Lead Account: ${widget.userName.isNotEmpty ? widget.userName : 'Lead Admin'}',
                                style: UnoTypography.body(
                                  color: palette.text,
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              Text(
                                'Role: Workspace Administrator · Access: Full Management',
                                style: UnoTypography.mono(
                                  color: palette.textSec,
                                  fontSize: 10.5,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: palette.live.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'LEAD',
                            style: UnoTypography.mono(
                              color: palette.live,
                              fontSize: 9.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 18),

                  // ── Projects Section Header ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'FETCHED BACKEND PROJECTS (${_availableBackendProjects.length})',
                        style: UnoTypography.mono(
                          color: palette.textSec,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Row(
                        children: [
                          InkWell(
                            onTap: _connectAllWorkspaceProjects,
                            borderRadius: BorderRadius.circular(6),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: palette.accent.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                    color: palette.accent.withValues(alpha: 0.3)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.done_all,
                                      size: 13, color: palette.accent),
                                  const SizedBox(width: 4),
                                  Text(
                                    'Connect All',
                                    style: UnoTypography.body(
                                      color: palette.accent,
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          InkWell(
                            onTap: _isRefreshingWorkspaceProjects
                                ? null
                                : () => _fetchAvailableWorkspaceProjects(isUserAction: true),
                            borderRadius: BorderRadius.circular(6),
                            child: Padding(
                              padding: const EdgeInsets.all(4),
                              child: _isRefreshingWorkspaceProjects
                                  ? SizedBox(
                                      width: 15,
                                      height: 15,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor: AlwaysStoppedAnimation<Color>(palette.accent),
                                      ),
                                    )
                                  : Icon(
                                      Icons.refresh,
                                      size: 15,
                                      color: palette.textSec,
                                    ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),

                  const SizedBox(height: 10),

                  // ── Scrollable Projects List ──
                  Container(
                    constraints: const BoxConstraints(maxHeight: 270),
                    decoration: BoxDecoration(
                      color: palette.bgElevated,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: palette.div),
                    ),
                    child: _isLoadingWorkspaceProjects
                        ? Center(
                            child: Padding(
                              padding: const EdgeInsets.all(32),
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
                                    'Fetching projects from backend...',
                                    style: UnoTypography.body(
                                      color: palette.textSec,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                        : _availableBackendProjects.isEmpty
                            ? Center(
                                child: Padding(
                                  padding: const EdgeInsets.all(28),
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.folder_off_outlined,
                                          size: 28, color: palette.textSec),
                                      const SizedBox(height: 8),
                                      Text(
                                        'No projects found on http://${ApiService.serverHost}',
                                        textAlign: TextAlign.center,
                                        style: UnoTypography.body(
                                          color: palette.text,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        'Ensure projects are created or registered on port 28000.',
                                        textAlign: TextAlign.center,
                                        style: UnoTypography.body(
                                          color: palette.textSec,
                                          fontSize: 11.5,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              )
                            : ListView.separated(
                                shrinkWrap: true,
                                padding: const EdgeInsets.all(8),
                                itemCount: _availableBackendProjects.length,
                                separatorBuilder: (_, unused) =>
                                    const SizedBox(height: 6),
                                itemBuilder: (context, idx) {
                                  final project =
                                      _availableBackendProjects[idx];
                                  final isConnected = _projects.any((p) =>
                                      p.id.toLowerCase() ==
                                          project.id.toLowerCase() ||
                                      p.name.toLowerCase() ==
                                          project.name.toLowerCase());

                                  return InkWell(
                                    onTap: () =>
                                        _toggleProjectConnection(project),
                                    borderRadius: BorderRadius.circular(8),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 12, vertical: 10),
                                      decoration: BoxDecoration(
                                        color: isConnected
                                            ? palette.accent
                                                .withValues(alpha: 0.08)
                                            : palette.bgSurface,
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(
                                          color: isConnected
                                              ? palette.accent
                                                  .withValues(alpha: 0.4)
                                              : palette.div,
                                        ),
                                      ),
                                      child: Row(
                                        children: [
                                          Container(
                                            width: 32,
                                            height: 32,
                                            decoration: BoxDecoration(
                                              color: palette.bgElevated,
                                              borderRadius:
                                                  BorderRadius.circular(6),
                                              border: Border.all(
                                                  color: palette.div),
                                            ),
                                            alignment: Alignment.center,
                                            child: Text(
                                              '<>',
                                              style: UnoTypography.mono(
                                                color: palette.textSec,
                                                fontSize: 11,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 10),
                                          Expanded(
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  project.name,
                                                  style: UnoTypography.body(
                                                    color: palette.text,
                                                    fontSize: 13.5,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                ),
                                                const SizedBox(height: 4),
                                                Builder(
                                                  builder: (context) {
                                                    final isReady = project.upsStatus.toUpperCase() == 'READY' ||
                                                        project.upsStatus.toUpperCase() == 'ACTIVE' ||
                                                        project.ingestionStatus.toLowerCase() == 'live';

                                                    if (isReady) {
                                                      return Tooltip(
                                                        message: 'Ready',
                                                        child: Container(
                                                          width: 14,
                                                          height: 14,
                                                          decoration: BoxDecoration(
                                                            shape: BoxShape.circle,
                                                            color: palette.live.withValues(alpha: 0.15),
                                                            border: Border.all(
                                                                color: palette.live.withValues(alpha: 0.45)),
                                                          ),
                                                          alignment: Alignment.center,
                                                          child: Container(
                                                            width: 6,
                                                            height: 6,
                                                            decoration: BoxDecoration(
                                                              shape: BoxShape.circle,
                                                              color: palette.live,
                                                              boxShadow: [
                                                                BoxShadow(
                                                                  color: palette.live.withValues(alpha: 0.7),
                                                                  blurRadius: 3,
                                                                  spreadRadius: 0.5,
                                                                ),
                                                              ],
                                                            ),
                                                          ),
                                                        ),
                                                      );
                                                    }

                                                    return Container(
                                                      padding: const EdgeInsets.symmetric(
                                                          horizontal: 6, vertical: 2),
                                                      decoration: BoxDecoration(
                                                        color: palette.bgBase,
                                                        border: Border.all(color: palette.div),
                                                        borderRadius: BorderRadius.circular(4),
                                                      ),
                                                      child: Text(
                                                        project.upsStatus.toUpperCase(),
                                                        style: UnoTypography.mono(
                                                          color: palette.textSec,
                                                          fontSize: 9,
                                                          fontWeight: FontWeight.w600,
                                                        ),
                                                      ),
                                                    );
                                                  },
                                                ),
                                              ],
                                            ),
                                          ),
                                          const SizedBox(width: 8),
                                          // Connection state badge / button
                                          if (isConnected)
                                            Container(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 9,
                                                      vertical: 5),
                                              decoration: BoxDecoration(
                                                color: palette.live
                                                    .withValues(alpha: 0.12),
                                                borderRadius:
                                                    BorderRadius.circular(6),
                                                border: Border.all(
                                                  color: palette.live
                                                      .withValues(alpha: 0.3),
                                                ),
                                              ),
                                              child: Row(
                                                mainAxisSize:
                                                    MainAxisSize.min,
                                                children: [
                                                  Icon(
                                                    Icons.check_circle,
                                                    size: 13,
                                                    color: palette.live,
                                                  ),
                                                  const SizedBox(width: 5),
                                                  Text(
                                                    'In Workspace',
                                                    style: UnoTypography.body(
                                                      color: palette.live,
                                                      fontSize: 11,
                                                      fontWeight:
                                                          FontWeight.w600,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            )
                                          else
                                            Container(
                                              padding:
                                                  const EdgeInsets.symmetric(
                                                      horizontal: 10,
                                                      vertical: 5),
                                              decoration: BoxDecoration(
                                                color: palette.accent,
                                                borderRadius:
                                                    BorderRadius.circular(6),
                                              ),
                                              child: Row(
                                                mainAxisSize:
                                                    MainAxisSize.min,
                                                children: [
                                                  const Icon(
                                                    Icons.add,
                                                    size: 13,
                                                    color: Colors.white,
                                                  ),
                                                  const SizedBox(width: 4),
                                                  Text(
                                                    'Connect',
                                                    style: UnoTypography.body(
                                                      color: Colors.white,
                                                      fontSize: 11,
                                                      fontWeight:
                                                          FontWeight.w600,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
                  ),

                  const SizedBox(height: 18),

                  // ── Dialog Footer ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '${_projects.length} project(s) displaying on workspace',
                        style: UnoTypography.body(
                          color: palette.textSec,
                          fontSize: 12,
                        ),
                      ),
                      InkWell(
                        onTap: () => setState(
                            () => _connectWorkspaceDialogOpen = false),
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 20, vertical: 9),
                          decoration: BoxDecoration(
                            color: palette.accent,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'Done',
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
      _isReloadingMembers = false;
      _membersError = null;
      _membersSuccess = null;
      _inviteMemberController.clear();
      _selectedInviteRole = 'MEMBER';
    });
    _loadProjectMembers(project.id);
  }

  void _loadProjectMembers(String projectId, {bool isReload = false}) async {
    if (_isReloadingMembers) return;
    setState(() {
      if (isReload || _projectMembers.isNotEmpty) {
        _isReloadingMembers = true;
      } else {
        _isLoadingMembers = true;
      }
      _membersError = null;
    });

    final stopwatch = Stopwatch()..start();
    try {
      final members = await ApiService.fetchProjectMembers(projectId);
      final elapsed = stopwatch.elapsedMilliseconds;
      if (isReload && elapsed < 400) {
        await Future.delayed(Duration(milliseconds: 400 - elapsed));
      }
      if (!mounted) return;
      setState(() {
        _projectMembers = members;
        _isLoadingMembers = false;
        _isReloadingMembers = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoadingMembers = false;
        _isReloadingMembers = false;
        _membersError = e.toString().replaceAll('Exception: ', '');
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
        _membersSuccess =
            'Successfully assigned $email as ${_selectedInviteRole == 'ADMIN' ? 'Manager' : 'Member'} on server';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isAddingMember = false;
        _membersError =
            'Failed to assign employee on server: ${e.toString().replaceAll('Exception: ', '')}';
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
      if (!mounted) return;
      setState(() {
        _projectMembers.removeWhere((m) =>
            m.id == member.id ||
            (m.userId == member.userId && m.userEmail == member.userEmail));
        _membersSuccess =
            'Removed ${member.userName ?? member.userEmail ?? 'member'} from project on server';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _membersError =
            'Failed to remove member on server: ${e.toString().replaceAll('Exception: ', '')}';
      });
    }
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
                        // Ready Green Button / Status badge
                        Builder(
                          builder: (context) {
                            final isReady = project.upsStatus.toUpperCase() ==
                                    'READY' ||
                                project.upsStatus.toUpperCase() == 'ACTIVE' ||
                                project.ingestionStatus.toLowerCase() == 'live';

                            if (isReady) {
                              return Tooltip(
                                message: 'Ready',
                                child: Container(
                                  width: 16,
                                  height: 16,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: palette.live.withValues(alpha: 0.15),
                                    border: Border.all(
                                        color: palette.live.withValues(alpha: 0.45)),
                                  ),
                                  alignment: Alignment.center,
                                  child: Container(
                                    width: 7,
                                    height: 7,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: palette.live,
                                      boxShadow: [
                                        BoxShadow(
                                          color: palette.live.withValues(alpha: 0.7),
                                          blurRadius: 4,
                                          spreadRadius: 0.5,
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            }

                            return Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 7, vertical: 2),
                              decoration: BoxDecoration(
                                color: palette.bgBase,
                                border: Border.all(color: palette.div),
                                borderRadius: BorderRadius.circular(5),
                              ),
                              child: Text(
                                project.upsStatus.toUpperCase(),
                                style: UnoTypography.mono(
                                  color: palette.textSec,
                                  fontSize: 9.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            );
                          },
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
                      // Role Selector Dropdown (opens DOWN below button)
                      PopupMenuButton<String>(
                        tooltip: '',
                        position: PopupMenuPosition.under,
                        offset: const Offset(0, 5),
                        color: palette.bgSurface,
                        elevation: 8,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: BorderSide(color: palette.div),
                        ),
                        onSelected: (val) {
                          setState(() => _selectedInviteRole = val);
                        },
                        itemBuilder: (context) => [
                          PopupMenuItem(
                            value: 'MEMBER',
                            height: 38,
                            child: Row(
                              children: [
                                Text(
                                  'Member (Dev)',
                                  style: UnoTypography.body(
                                    color: _selectedInviteRole == 'MEMBER'
                                        ? palette.live
                                        : palette.text,
                                    fontSize: 12.5,
                                    fontWeight: _selectedInviteRole == 'MEMBER'
                                        ? FontWeight.w600
                                        : FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          PopupMenuItem(
                            value: 'ADMIN',
                            height: 38,
                            child: Row(
                              children: [
                                Text(
                                  'Manager',
                                  style: UnoTypography.body(
                                    color: _selectedInviteRole == 'ADMIN'
                                        ? palette.accent
                                        : palette.text,
                                    fontSize: 12.5,
                                    fontWeight: _selectedInviteRole == 'ADMIN'
                                        ? FontWeight.w600
                                        : FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                        child: Container(
                          height: 38,
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          decoration: BoxDecoration(
                            color: palette.bgElevated,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: palette.div),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                _selectedInviteRole == 'ADMIN'
                                    ? 'Manager'
                                    : 'Member (Dev)',
                                style: UnoTypography.body(
                                  color: palette.text,
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Icon(
                                Icons.keyboard_arrow_down,
                                size: 16,
                                color: palette.textSec,
                              ),
                            ],
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
                        onTap: _isReloadingMembers
                            ? () {}
                            : () => _loadProjectMembers(project.id, isReload: true),
                        borderRadius: BorderRadius.circular(4),
                        child: Padding(
                          padding: const EdgeInsets.all(2),
                          child: Row(
                            children: [
                              SizedBox(
                                width: 13,
                                height: 13,
                                child: _isReloadingMembers
                                    ? CircularProgressIndicator(
                                        strokeWidth: 1.5,
                                        valueColor: AlwaysStoppedAnimation<Color>(
                                            palette.accent),
                                      )
                                    : Icon(Icons.refresh,
                                        size: 13, color: palette.textSec),
                              ),
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
                      child: _isLoadingMembers && _projectMembers.isEmpty
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
                              : AnimatedOpacity(
                                  opacity: _isReloadingMembers ? 0.75 : 1.0,
                                  duration: const Duration(milliseconds: 200),
                                  child: ListView.separated(
                                  shrinkWrap: true,
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 6, horizontal: 8),
                                  itemCount: _projectMembers.length,
                                  separatorBuilder: (_, unused) => Divider(
                                    height: 1,
                                    color: palette.div,
                                  ),
                                  itemBuilder: (context, idx) {
                                    final member = _projectMembers[idx];
                                    final role = member.role.toUpperCase();
                                    final isMemberAdmin = role == 'ADMIN' ||
                                        role == 'MANAGER' ||
                                        role == 'LEAD';
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
                                                        isMemberAdmin
                                                            ? 'MANAGER'
                                                            : role,
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
    final isDesktop =
        !kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS);

    return Container(
      height: 52,
      color: palette.bgBase,
      padding: EdgeInsets.only(
        left: isNarrow ? 12 : 20,
        right: isDesktop ? 0 : (isNarrow ? 12 : 20),
      ),
      child: Row(
        children: [
          // ── Left: Unotusk Logo & Name (Consistent with Workspace view) ──
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              UnotuskLogo(size: 18, onDark: widget.isDark),
              const SizedBox(width: 9),
              Text(
                'Unotusk',
                style: UnoTypography.brandSerif(
                  palette: palette,
                  fontSize: 14.5,
                ),
              ),
            ],
          ),

          // ── Draggable window area ──
          Expanded(
            child: isDesktop
                ? const DragToMoveArea(
                    child: SizedBox(
                      height: 52,
                      width: double.infinity,
                    ),
                  )
                : const SizedBox(height: 52),
          ),
          // ── Theme Toggle (Consistent with Workspace view) ──
          InkWell(
            onTap: widget.onToggleTheme,
            borderRadius: BorderRadius.circular(6),
            child: Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: Colors.transparent,
                border: Border.all(color: palette.div),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Icon(
                widget.isDark ? LucideIcons.moon : LucideIcons.sun,
                size: 14,
                color: palette.textSec,
              ),
            ),
          ),

          // Desktop Window Controls (Minimize, Maximize/Restore, Close)
          if (isDesktop) ...[
            const SizedBox(width: 8),
            DesktopWindowControls(palette: palette, height: 52),
          ],
        ],
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
                  _buildUserLoginButton(palette),
                  const SizedBox(width: 10),
                  _buildActionButton(
                    icon: Icons.refresh,
                    label: 'Refresh',
                    palette: palette,
                    filled: false,
                    isLoading: _isRefreshingProjects,
                    onTap: () => _fetchServerProjects(isSilent: false),
                  ),
                  if (_isManager) ...[
                    const SizedBox(width: 10),
                    _buildActionButton(
                      icon: Icons.hub_outlined,
                      label: 'Connect Workspace',
                      palette: palette,
                      filled: true,
                      onTap: _openConnectWorkspaceDialog,
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
                      'Loading workspace...',
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
                    _filterText.isNotEmpty
                        ? Icons.search_off_rounded
                        : Icons.folder_open_rounded,
                    size: 36,
                    color: palette.textSec,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _filterText.isNotEmpty
                        ? 'No matching projects found'
                        : 'No projects in workspace',
                    style: UnoTypography.body(
                      color: palette.text,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _filterText.isNotEmpty
                        ? 'Try adjusting your search filter.'
                        : (_isManager
                            ? 'Connect backend projects to display them in your workspace.'
                            : 'No projects have been connected to this workspace yet.'),
                    textAlign: TextAlign.center,
                    style: UnoTypography.body(
                      color: palette.textSec,
                      fontSize: 13,
                    ),
                  ),
                  if (_isManager && _filterText.isEmpty) ...[
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: _openConnectWorkspaceDialog,
                      icon: const Icon(Icons.hub_outlined, size: 16),
                      label: const Text('Connect Workspace'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: palette.accent,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 18, vertical: 11),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
                  ],
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
    bool isLoading = false,
  }) {
    return InkWell(
      onTap: isLoading ? () {} : onTap,
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
            SizedBox(
              width: 15,
              height: 15,
              child: isLoading
                  ? Center(
                      child: SizedBox(
                        width: 13,
                        height: 13,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            filled ? Colors.white : palette.accent,
                          ),
                        ),
                      ),
                    )
                  : Icon(
                      icon,
                      size: 15,
                      color: filled ? Colors.white : palette.textSec,
                    ),
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

          // Ready Green Button / Status badge
          Builder(
            builder: (context) {
              final isReady = project.upsStatus.toUpperCase() == 'READY' ||
                  project.upsStatus.toUpperCase() == 'ACTIVE' ||
                  project.ingestionStatus.toLowerCase() == 'live';

              if (isReady) {
                return Tooltip(
                  message: 'Ready',
                  child: Container(
                    width: 18,
                    height: 18,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: palette.live.withValues(alpha: 0.15),
                      border:
                          Border.all(color: palette.live.withValues(alpha: 0.45)),
                    ),
                    alignment: Alignment.center,
                    child: Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: palette.live,
                        boxShadow: [
                          BoxShadow(
                            color: palette.live.withValues(alpha: 0.7),
                            blurRadius: 4,
                            spreadRadius: 0.5,
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }

              return Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                decoration: BoxDecoration(
                  color: palette.bgElevated,
                  border: Border.all(color: palette.div),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  project.upsStatus.toUpperCase(),
                  style: UnoTypography.mono(
                    color: palette.textSec,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              );
            },
          ),

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
  //  User Login / Menu Button (Beside Refresh Button)
  // ─────────────────────────────────────────────────
  Widget _buildUserLoginButton(UnoPalette palette) {
    final displayName = widget.userName.isNotEmpty ? widget.userName : 'Lead Admin';
    final initial = displayName.isNotEmpty ? displayName[0].toUpperCase() : 'L';
    final email = widget.user?.email ?? 'lead@acme.com';

    return PopupMenuButton<String>(
      tooltip: '',
      position: PopupMenuPosition.under,
      offset: const Offset(0, 6),
      color: palette.bgSurface,
      elevation: 8,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: palette.div),
      ),
      onSelected: (val) {
        if (val == 'settings') {
          setState(() => _activeTab = 'settings');
        } else if (val == 'logout') {
          widget.onLogOut();
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem<String>(
          enabled: false,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                displayName,
                style: UnoTypography.body(
                  color: palette.text,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                email,
                style: UnoTypography.mono(
                  color: palette.textSec,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: palette.bgElevated,
                  border: Border.all(color: palette.div),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  _isManager ? 'MANAGER' : 'MEMBER',
                  style: UnoTypography.mono(
                    color: palette.textSec,
                    fontSize: 9,
                    letterSpacing: 0.8,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
        const PopupMenuDivider(height: 1),
        PopupMenuItem<String>(
          value: 'settings',
          height: 38,
          child: Row(
            children: [
              Icon(Icons.settings_outlined, size: 15, color: palette.textSec),
              const SizedBox(width: 10),
              Text(
                'Settings',
                style: UnoTypography.body(color: palette.text, fontSize: 13),
              ),
            ],
          ),
        ),
        const PopupMenuDivider(height: 1),
        PopupMenuItem<String>(
          value: 'logout',
          height: 38,
          child: Row(
            children: [
              const Icon(Icons.logout, size: 15, color: Color(0xFFE05A5A)),
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
      ],
      child: Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: Colors.transparent,
          border: Border.all(color: palette.div),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: palette.accent.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              alignment: Alignment.center,
              child: Text(
                initial,
                style: UnoTypography.body(
                  color: palette.accent,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              displayName,
              style: UnoTypography.body(
                color: palette.text,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: 6),
            Icon(
              Icons.keyboard_arrow_down,
              size: 15,
              color: palette.textSec,
            ),
          ],
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
