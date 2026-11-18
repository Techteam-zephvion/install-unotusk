import 'dart:async';
import 'dart:math' as math;
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
  final List<ProjectItem>? initialConnectedProjects;
  final ValueChanged<List<ProjectItem>>? onConnectedProjectsChanged;

  const ProjectsScreen({
    super.key,
    required this.palette,
    required this.isDark,
    required this.onToggleTheme,
    required this.userName,
    this.user,
    required this.onOpenProject,
    required this.onLogOut,
    this.initialConnectedProjects,
    this.onConnectedProjectsChanged,
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
  List<ProjectMember> _workspaceEmployees = [];
  bool _isLoadingMembers = false;
  bool _isReloadingMembers = false;
  bool _isLoadingWorkspaceEmployees = false;
  String _workspaceMembersTab = 'available'; // Default to Available in Database tab
  String? _assigningUserId;
  final Map<String, String> _employeeAssignRole = {};
  String? _membersError;
  String? _membersSuccess;
  final _searchMemberController = TextEditingController();

  /// Returns employees retrieved from database that are not yet assigned to the current project
  List<ProjectMember> get _availableEmployees {
    final employees = _workspaceEmployees;
    if (employees.isEmpty) return [];
    final members = _projectMembers;
    final assignedEmails = members
        .map((m) => (m.userEmail ?? '').trim().toLowerCase())
        .where((e) => e.isNotEmpty)
        .toSet();
    final assignedUserIds = members
        .map((m) => m.userId.trim())
        .where((u) => u.isNotEmpty)
        .toSet();

    return employees.where((u) {
      final email = (u.userEmail ?? '').trim().toLowerCase();
      final name = (u.userName ?? '').trim().toLowerCase();
      // Exclude permanent Lead Admin
      if (email == 'admin@acme.com' || name == 'lead admin') return false;
      // Exclude employees already assigned to project
      if (assignedEmails.contains(email)) return false;
      if (assignedUserIds.contains(u.userId.trim())) return false;
      return true;
    }).toList();
  }

  // Connect Server & Workspace State
  final _serverUrlController = TextEditingController();
  final _workspaceScrollController = ScrollController();
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
    if (ApiService.connectedProjectIds.isEmpty) {
      ApiService.loadPersistedConnectedProjects();
    }
    if (ApiService.isControlPlane && ApiService.cachedProjects.isNotEmpty) {
      final validIds = ApiService.cachedProjects.map((p) => p.id.toLowerCase()).toSet();
      final validNames = ApiService.cachedProjects.map((p) => p.name.toLowerCase()).toSet();
      ApiService.connectedProjectIds.removeWhere((id) =>
          !validIds.contains(id.toLowerCase()) &&
          !validNames.contains(id.toLowerCase()));
    }
    if (widget.initialConnectedProjects != null && widget.initialConnectedProjects!.isNotEmpty) {
      _projects.addAll(widget.initialConnectedProjects!);
      for (final p in widget.initialConnectedProjects!) {
        ApiService.connectedProjectIds.add(p.id);
        ApiService.connectedProjectIds.add(p.name);
      }
      ApiService.connectedWorkspaceProjects
        ..clear()
        ..addAll(_projects);
    } else if (ApiService.connectedWorkspaceProjects.isNotEmpty) {
      _projects.addAll(ApiService.connectedWorkspaceProjects);
      for (final p in ApiService.connectedWorkspaceProjects) {
        ApiService.connectedProjectIds.add(p.id);
        ApiService.connectedProjectIds.add(p.name);
      }
    } else {
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
    _projects.removeWhere((p) =>
        p.upsStatus.toUpperCase() == 'STOPPED' ||
        p.upsStatus.toUpperCase() == 'DELETED' ||
        p.upsStatus.toUpperCase() == 'OFFLINE');
    _checkServer();
    _fetchServerProjects(isSilent: true);
    _fetchAvailableWorkspaceProjects(isSilent: true);
    _serverTimer =
        Timer.periodic(const Duration(seconds: 4), (_) => _checkServer());
  }

  void _checkServer() async {
    await ApiService.checkHealth();
    if (mounted) {
      _fetchServerProjects(isSilent: true);
    }
  }

  void _fetchServerProjects({bool isSilent = false}) async {
    if (_isRefreshingProjects) return;
    if (!isSilent) {
      setState(() {
        _isRefreshingProjects = true;
      });
    }

    final stopwatch = Stopwatch()..start();
    try {
      final serverProjects = await ApiService.fetchProjects();
      final elapsed = stopwatch.elapsedMilliseconds;
      final isTest = !kIsWeb && Platform.environment.containsKey('FLUTTER_TEST');
      if (elapsed < 450 && !isTest) {
        await Future.delayed(Duration(milliseconds: 450 - elapsed));
      }
      if (!mounted) return;
      setState(() {
        _isLoadingProjects = false;
        _isRefreshingProjects = false;
        _availableBackendProjects = List<ProjectItem>.from(serverProjects);
        
        if (ApiService.isControlPlane) {
          final validIds = serverProjects.map((p) => p.id.toLowerCase()).toSet();
          final validNames = serverProjects.map((p) => p.name.toLowerCase()).toSet();
          ApiService.connectedProjectIds.removeWhere((id) =>
              !validIds.contains(id.toLowerCase()) &&
              !validNames.contains(id.toLowerCase()));
        }

        _projects.clear();
        for (final p in serverProjects) {
          final isRunning = p.upsStatus.toUpperCase() != 'STOPPED' &&
              p.upsStatus.toUpperCase() != 'DELETED' &&
              p.upsStatus.toUpperCase() != 'OFFLINE';
          if (isRunning &&
              (ApiService.connectedProjectIds.contains(p.id) ||
                  ApiService.connectedProjectIds.contains(p.name))) {
            _projects.add(p);
          }
        }
        ApiService.savePersistedConnectedProjects();
        
        ApiService.connectedWorkspaceProjects
          ..clear()
          ..addAll(_projects);
        widget.onConnectedProjectsChanged?.call(_projects);
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
      body: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutCubic,
        decoration: BoxDecoration(gradient: palette.pageGradient),
        child: Stack(
          children: [
            Column(
              children: [
                // ─── Top Navigation Bar ───
                _buildTopBar(palette, isNarrow),

                // ─── Content Area ───
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 220),
                    layoutBuilder: (Widget? currentChild, List<Widget> previousChildren) {
                      return Stack(
                        alignment: Alignment.topCenter,
                        children: <Widget>[
                          ...previousChildren,
                          ?currentChild,
                        ],
                      );
                    },
                    switchInCurve: Curves.easeOutCubic,
                    switchOutCurve: Curves.easeInCubic,
                    transitionBuilder: (child, animation) {
                      return FadeTransition(opacity: animation, child: child);
                    },
                    child: KeyedSubtree(
                      key: ValueKey<String>('$_activeTab-${widget.isDark}'),
                      child: _activeTab == 'projects'
                          ? _buildProjectsContent(palette, isNarrow)
                          : _buildSettingsContent(palette),
                    ),
                  ),
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
      ),
    );
  }

  @override
  void dispose() {
    _serverTimer?.cancel();
    _serverUrlController.dispose();
    _workspaceScrollController.dispose();
    _searchMemberController.dispose();
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
        _availableBackendProjects = List<ProjectItem>.from(serverProjects);
        final validIds = serverProjects.map((p) => p.id.toLowerCase()).toSet();
        final validNames = serverProjects.map((p) => p.name.toLowerCase()).toSet();

        // Evict any deleted or stopped projects from _projects
        _projects.removeWhere((p) =>
            (!validIds.contains(p.id.toLowerCase()) &&
            !validNames.contains(p.name.toLowerCase())) ||
            p.upsStatus.toUpperCase() == 'STOPPED' ||
            p.upsStatus.toUpperCase() == 'DELETED' ||
            p.upsStatus.toUpperCase() == 'OFFLINE');

        // Keep any existing connected running projects synchronized
        for (final sp in serverProjects) {
          final isRunning = sp.upsStatus.toUpperCase() != 'STOPPED' &&
              sp.upsStatus.toUpperCase() != 'DELETED' &&
              sp.upsStatus.toUpperCase() != 'OFFLINE';
          final idx = _projects.indexWhere((p) =>
              p.id.toLowerCase() == sp.id.toLowerCase() ||
              p.name.toLowerCase() == sp.name.toLowerCase());
          if (idx >= 0) {
            if (isRunning) {
              _projects[idx] = sp;
            } else {
              _projects.removeAt(idx);
            }
          }
        }

        ApiService.connectedProjectIds.removeWhere((id) =>
            !validIds.contains(id.toLowerCase()) &&
            !validNames.contains(id.toLowerCase()));
        for (final p in _projects) {
          ApiService.connectedProjectIds.add(p.id);
          ApiService.connectedProjectIds.add(p.name);
        }
        ApiService.savePersistedConnectedProjects();

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
    final isStopped = project.upsStatus.toUpperCase() == 'STOPPED' ||
        project.upsStatus.toUpperCase() == 'DELETED' ||
        project.upsStatus.toUpperCase() == 'OFFLINE';
    if (isStopped) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Cannot connect ${project.name}: The project server is ${project.upsStatus.toLowerCase()} on the backend.',
          ),
          backgroundColor: Colors.red[800],
        ),
      );
      return;
    }

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
    widget.onConnectedProjectsChanged?.call(_projects);
    ApiService.savePersistedConnectedProjects();
  }

  void _connectAllWorkspaceProjects() {
    setState(() {
      for (final p in _availableBackendProjects) {
        final isRunning = p.upsStatus.toUpperCase() != 'STOPPED' &&
            p.upsStatus.toUpperCase() != 'DELETED' &&
            p.upsStatus.toUpperCase() != 'OFFLINE';
        if (!isRunning) continue;
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
    widget.onConnectedProjectsChanged?.call(_projects);
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
                              color: widget.isDark ? const Color(0xFF0A0F20) : Colors.white,
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
    final buttonFg = widget.isDark ? const Color(0xFF0A0F20) : Colors.white;

    return GestureDetector(
      onTap: () => setState(() => _connectWorkspaceDialogOpen = false),
      child: Container(
        color: Colors.black.withValues(alpha: widget.isDark ? 0.65 : 0.4),
        child: Center(
          child: GestureDetector(
            onTap: () {}, // Absorb taps inside dialog
            child: Container(
              width: 540,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: palette.bgSurface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: palette.div),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: widget.isDark ? 0.45 : 0.18),
                    blurRadius: 36,
                    offset: const Offset(0, 16),
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
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: palette.accent.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            alignment: Alignment.center,
                            child: Icon(
                              Icons.hub_outlined,
                              size: 19,
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
                                  fontSize: 17,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 2),
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
                        child: Container(
                          width: 28,
                          height: 28,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: Colors.transparent,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Icon(
                            Icons.close,
                            size: 18,
                            color: palette.textSec,
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  // ── Minimal Admin Status Strip ──
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: palette.bgElevated,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: palette.div),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.shield_outlined,
                          size: 14,
                          color: palette.textSec,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text.rich(
                            TextSpan(
                              text: widget.userName.isNotEmpty ? widget.userName : 'Lead Admin',
                              style: UnoTypography.body(
                                color: palette.text,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                              children: [
                                TextSpan(
                                  text: ' · Workspace Administrator',
                                  style: UnoTypography.body(
                                    color: palette.textSec,
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w400,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: palette.live.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'LEAD',
                            style: UnoTypography.mono(
                              color: palette.live,
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // ── Projects Section Header ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Text(
                            'PROJECT SERVERS',
                            style: UnoTypography.mono(
                              color: palette.textSec,
                              fontSize: 10.5,
                              letterSpacing: 0.8,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
                            decoration: BoxDecoration(
                              color: palette.bgElevated,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: palette.div),
                            ),
                            child: Text(
                              '${_availableBackendProjects.length}',
                              style: UnoTypography.mono(
                                color: palette.textSec,
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
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
                                color: palette.bgElevated,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: palette.div),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.done_all,
                                      size: 13, color: palette.textSec),
                                  const SizedBox(width: 5),
                                  Text(
                                    'Connect all',
                                    style: UnoTypography.body(
                                      color: palette.text,
                                      fontSize: 11.5,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 6),
                          InkWell(
                            onTap: _isRefreshingWorkspaceProjects
                                ? null
                                : () => _fetchAvailableWorkspaceProjects(isUserAction: true),
                            borderRadius: BorderRadius.circular(6),
                            child: Container(
                              width: 26,
                              height: 26,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: palette.bgElevated,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: palette.div),
                              ),
                              child: _isRefreshingWorkspaceProjects
                                  ? SizedBox(
                                      width: 12,
                                      height: 12,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 1.8,
                                        valueColor: AlwaysStoppedAnimation<Color>(palette.accent),
                                      ),
                                    )
                                  : Icon(
                                      Icons.refresh,
                                      size: 13,
                                      color: palette.textSec,
                                    ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),

                  const SizedBox(height: 10),

                  // ── Clean, Minimal Server List ──
                  Container(
                    constraints: const BoxConstraints(maxHeight: 280),
                    decoration: BoxDecoration(
                      color: palette.bgElevated,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: palette.div),
                    ),
                    clipBehavior: Clip.antiAlias,
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
                                    'Fetching project servers...',
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
                                          size: 26, color: palette.textSec),
                                      const SizedBox(height: 8),
                                      Text(
                                        'No servers found on http://${ApiService.serverHost}',
                                        textAlign: TextAlign.center,
                                        style: UnoTypography.body(
                                          color: palette.text,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        'Ensure project servers are running on port 28000+.',
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
                            : ScrollConfiguration(
                                behavior: ScrollConfiguration.of(context).copyWith(
                                  scrollbars: false,
                                ),
                                child: RawScrollbar(
                                  controller: _workspaceScrollController,
                                  thumbVisibility: false,
                                  trackVisibility: false,
                                  thickness: 2.0,
                                  radius: const Radius.circular(2),
                                  thumbColor: palette.textSec.withValues(alpha: 0.25),
                                  fadeDuration: const Duration(milliseconds: 250),
                                  padding: const EdgeInsets.only(right: 2, top: 4, bottom: 4),
                                  child: ListView.separated(
                                    controller: _workspaceScrollController,
                                    physics: const BouncingScrollPhysics(
                                      parent: AlwaysScrollableScrollPhysics(),
                                    ),
                                    shrinkWrap: true,
                                    padding: EdgeInsets.zero,
                                    itemCount: _availableBackendProjects.length,
                                    separatorBuilder: (_, unused) => Divider(
                                      height: 1,
                                      thickness: 1,
                                      color: palette.div.withValues(alpha: 0.5),
                                    ),
                                    itemBuilder: (context, idx) {
                                      final project = _availableBackendProjects[idx];
                                      final isConnected = _projects.any((p) =>
                                          p.id.toLowerCase() == project.id.toLowerCase() ||
                                          p.name.toLowerCase() == project.name.toLowerCase());

                                      final isStopped = project.upsStatus.toUpperCase() == 'STOPPED' ||
                                          project.upsStatus.toUpperCase() == 'DELETED' ||
                                          project.upsStatus.toUpperCase() == 'OFFLINE';

                                      final isReady = !isStopped && (
                                          project.upsStatus.toUpperCase() == 'READY' ||
                                          project.upsStatus.toUpperCase() == 'ACTIVE' ||
                                          project.ingestionStatus.toLowerCase() == 'live');

                                      return Container(
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 14, vertical: 11),
                                        color: isConnected
                                            ? palette.accent.withValues(alpha: widget.isDark ? 0.05 : 0.08)
                                            : Colors.transparent,
                                        child: Row(
                                          children: [
                                            // Status dot indicator
                                            Container(
                                              width: 8,
                                              height: 8,
                                              decoration: BoxDecoration(
                                                shape: BoxShape.circle,
                                                color: isStopped
                                                    ? palette.textSec.withValues(alpha: 0.35)
                                                    : (isReady ? palette.live : palette.textSec),
                                                boxShadow: isReady
                                                    ? [
                                                        BoxShadow(
                                                          color: palette.live.withValues(alpha: 0.5),
                                                          blurRadius: 4,
                                                        ),
                                                      ]
                                                    : null,
                                              ),
                                            ),
                                            const SizedBox(width: 12),
                                            // Project title & details
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    project.name,
                                                    style: UnoTypography.body(
                                                      color: isStopped
                                                          ? palette.textSec
                                                          : palette.text,
                                                      fontSize: 13.5,
                                                      fontWeight: FontWeight.w600,
                                                    ),
                                                  ),
                                                  const SizedBox(height: 2),
                                                  Text(
                                                    isStopped
                                                        ? 'Offline · Data plane inactive'
                                                        : (project.port != null
                                                            ? 'Port ${project.port} · Active server'
                                                            : 'Port 28000 · Ready'),
                                                    style: UnoTypography.mono(
                                                      color: palette.textSec.withValues(alpha: 0.75),
                                                      fontSize: 10.5,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ),
                                            const SizedBox(width: 10),
                                            // Action button / pill
                                            if (isStopped)
                                              Container(
                                                padding: const EdgeInsets.symmetric(
                                                    horizontal: 8, vertical: 3),
                                                decoration: BoxDecoration(
                                                  color: Colors.transparent,
                                                  border: Border.all(
                                                      color: palette.div.withValues(alpha: 0.6)),
                                                  borderRadius: BorderRadius.circular(4),
                                                ),
                                                child: Text(
                                                  'Offline',
                                                  style: UnoTypography.mono(
                                                    color: palette.textSec.withValues(alpha: 0.6),
                                                    fontSize: 10,
                                                    fontWeight: FontWeight.w500,
                                                  ),
                                                ),
                                              )
                                            else if (isConnected)
                                              InkWell(
                                                onTap: () => _toggleProjectConnection(project),
                                                borderRadius: BorderRadius.circular(6),
                                                child: Container(
                                                  padding: const EdgeInsets.symmetric(
                                                      horizontal: 10, vertical: 5),
                                                  decoration: BoxDecoration(
                                                    color: palette.live.withValues(alpha: 0.12),
                                                    borderRadius: BorderRadius.circular(6),
                                                    border: Border.all(
                                                        color: palette.live.withValues(alpha: 0.35)),
                                                  ),
                                                  child: Row(
                                                    mainAxisSize: MainAxisSize.min,
                                                    children: [
                                                      Icon(
                                                        Icons.check,
                                                        size: 13,
                                                        color: palette.live,
                                                      ),
                                                      const SizedBox(width: 4),
                                                      Text(
                                                        'Connected',
                                                        style: UnoTypography.body(
                                                          color: palette.live,
                                                          fontSize: 11.5,
                                                          fontWeight: FontWeight.w600,
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                              )
                                            else
                                              InkWell(
                                                onTap: () => _toggleProjectConnection(project),
                                                borderRadius: BorderRadius.circular(6),
                                                child: Container(
                                                  padding: const EdgeInsets.symmetric(
                                                      horizontal: 12, vertical: 5),
                                                  decoration: BoxDecoration(
                                                    color: palette.accent,
                                                    borderRadius: BorderRadius.circular(6),
                                                  ),
                                                  child: Row(
                                                    mainAxisSize: MainAxisSize.min,
                                                    children: [
                                                      Icon(
                                                        Icons.add,
                                                        size: 13,
                                                        color: buttonFg,
                                                      ),
                                                      const SizedBox(width: 4),
                                                      Text(
                                                        'Connect',
                                                        style: UnoTypography.body(
                                                          color: buttonFg,
                                                          fontSize: 11.5,
                                                          fontWeight: FontWeight.w600,
                                                        ),
                                                      ),
                                                    ],
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

                  const SizedBox(height: 18),

                  // ── Dialog Footer ──
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '${_projects.length} project(s) connected to workspace',
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
                              horizontal: 22, vertical: 8),
                          decoration: BoxDecoration(
                            color: palette.accent,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            'Done',
                            style: UnoTypography.body(
                              color: buttonFg,
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

  void _openManageWorkspace(ProjectItem project) async {
    setState(() {
      _managingWorkspaceProject = project;
      _isLoadingMembers = true;
      _isReloadingMembers = false;
      _isLoadingWorkspaceEmployees = true;
      _workspaceMembersTab = 'available'; // Default to Available in Database tab
      _membersError = null;
      _membersSuccess = null;
      _searchMemberController.clear();
    });

    final stopwatch = Stopwatch()..start();
    try {
      final membersFuture = ApiService.fetchProjectMembers(project.id);
      final employeesFuture = ApiService.fetchOrganizationEmployees();
      final results = await Future.wait([membersFuture, employeesFuture]);

      final elapsed = stopwatch.elapsedMilliseconds;
      final isTest = !kIsWeb && Platform.environment.containsKey('FLUTTER_TEST');
      if (elapsed < 400 && !isTest) {
        await Future.delayed(Duration(milliseconds: 400 - elapsed));
      }
      if (!mounted) return;

      final members = results[0];
      final employees = results[1];

      setState(() {
        _projectMembers = members;
        _workspaceEmployees = employees;
        _isLoadingMembers = false;
        _isLoadingWorkspaceEmployees = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _membersError = 'Failed to load team data: $e';
        _isLoadingMembers = false;
        _isLoadingWorkspaceEmployees = false;
      });
    }
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
      final membersFuture = ApiService.fetchProjectMembers(projectId);
      final employeesFuture = ApiService.fetchOrganizationEmployees();
      final results = await Future.wait([membersFuture, employeesFuture]);

      final elapsed = stopwatch.elapsedMilliseconds;
      if (isReload && elapsed < 400) {
        await Future.delayed(Duration(milliseconds: 400 - elapsed));
      }
      if (!mounted) return;
      setState(() {
        _projectMembers = results[0];
        _workspaceEmployees = results[1];
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

  void _handleAssignEmployee(ProjectMember employee, {String role = 'MEMBER'}) async {
    final projectId = _managingWorkspaceProject?.id;
    if (projectId == null) return;

    setState(() {
      _assigningUserId = employee.userId;
      _membersError = null;
      _membersSuccess = null;
    });

    try {
      final newMember = await ApiService.addProjectMember(
        projectId: projectId,
        userId: employee.userId,
        email: employee.userEmail,
        role: role,
      );
      if (!mounted) return;
      setState(() {
        _projectMembers.add(newMember);
        _assigningUserId = null;
        _membersSuccess = 'Assigned ${employee.userName ?? employee.userEmail} as $role';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _membersError = 'Failed to assign: $e';
        _assigningUserId = null;
      });
    }
  }

  void _handleRemoveMember(ProjectMember member) async {
    final projectId = _managingWorkspaceProject?.id;
    if (projectId == null) return;

    if (member.userEmail?.toLowerCase() == 'admin@acme.com' ||
        member.userName?.toLowerCase() == 'lead admin') {
      setState(() => _membersError = 'Cannot remove Lead Admin from project.');
      return;
    }

    setState(() {
      _membersError = null;
      _membersSuccess = null;
    });

    try {
      await ApiService.removeProjectMember(
        member.userId,
        projectId,
      );
      if (!mounted) return;
      setState(() {
        _projectMembers.removeWhere((m) => m.userId == member.userId);
        _membersSuccess = 'Removed ${member.userName ?? member.userEmail} from project';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _membersError = e.toString().replaceAll('Exception: ', '');
      });
    }
  }

  String _getMemberInitials(String? name, String? email) {
    if (email?.toLowerCase() == 'admin@acme.com' ||
        name?.toLowerCase() == 'lead admin') {
      return 'LA';
    }
    if (name != null && name.trim().isNotEmpty) {
      final parts = name.trim().split(RegExp(r'\s+'));
      if (parts.length >= 2) {
        return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
      }
      return parts[0].substring(0, math.min(2, parts[0].length)).toUpperCase();
    }
    if (email != null && email.isNotEmpty) {
      return email.substring(0, math.min(2, email.length)).toUpperCase();
    }
    return 'EM';
  }

  Widget _buildMemberTabButton({
    required String label,
    required int count,
    required bool isSelected,
    required VoidCallback onTap,
    required UnoPalette palette,
    Color? badgeColor,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected
              ? palette.accent.withValues(alpha: 0.15)
              : palette.bgElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSelected
                ? palette.accent.withValues(alpha: 0.4)
                : palette.div,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: UnoTypography.body(
                color: isSelected ? palette.text : palette.textSec,
                fontSize: 12,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1.5),
              decoration: BoxDecoration(
                color: (badgeColor ?? palette.accent)
                    .withValues(alpha: isSelected ? 0.25 : 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '$count',
                style: UnoTypography.mono(
                  color: isSelected
                      ? (badgeColor ?? palette.accent)
                      : palette.textSec,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildManageWorkspaceModal(UnoPalette palette) {
    final project = _managingWorkspaceProject;
    if (project == null) return const SizedBox.shrink();

    final rawQuery = _searchMemberController.text.trim().toLowerCase();

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
                            final isStopped = project.upsStatus.toUpperCase() == 'STOPPED' ||
                                project.upsStatus.toUpperCase() == 'DELETED' ||
                                project.upsStatus.toUpperCase() == 'OFFLINE';

                            if (isStopped) {
                              return Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.redAccent.withValues(alpha: 0.12),
                                  border: Border.all(color: Colors.redAccent.withValues(alpha: 0.35)),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  'STOPPED',
                                  style: UnoTypography.mono(
                                    color: Colors.redAccent,
                                    fontSize: 9,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              );
                            }

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

                  const SizedBox(height: 14),

                  // ── Search Input Row ──
                  Container(
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
                          Icons.search,
                          size: 16,
                          color: palette.textSec,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                            controller: _searchMemberController,
                            style: UnoTypography.body(
                              color: palette.text,
                              fontSize: 13,
                            ),
                            decoration: InputDecoration(
                              hintText: 'Search employees in database...',
                              hintStyle: UnoTypography.body(
                                color: palette.textSec.withValues(alpha: 0.6),
                                fontSize: 13,
                              ),
                              border: InputBorder.none,
                              isDense: true,
                              contentPadding: EdgeInsets.zero,
                            ),
                            onChanged: (_) => setState(() {}),
                          ),
                        ),
                        if (_searchMemberController.text.isNotEmpty)
                          InkWell(
                            onTap: () {
                              _searchMemberController.clear();
                              setState(() {});
                            },
                            child: Icon(Icons.close, size: 14, color: palette.textSec),
                          ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 14),

                  // ── Tabs Header: Assigned to Project vs Available in Database ──
                  Row(
                    children: [
                      _buildMemberTabButton(
                        label: 'Available in Database',
                        count: _availableEmployees.length,
                        isSelected: _workspaceMembersTab == 'available',
                        onTap: () => setState(() => _workspaceMembersTab = 'available'),
                        palette: palette,
                        badgeColor: palette.live,
                      ),
                      const SizedBox(width: 10),
                      _buildMemberTabButton(
                        label: 'Assigned to Project',
                        count: _projectMembers.length,
                        isSelected: _workspaceMembersTab == 'assigned',
                        onTap: () => setState(() => _workspaceMembersTab = 'assigned'),
                        palette: palette,
                      ),
                      const Spacer(),
                      InkWell(
                        onTap: _isReloadingMembers
                            ? () {}
                            : () => _loadProjectMembers(project.id, isReload: true),
                        borderRadius: BorderRadius.circular(4),
                        child: Padding(
                          padding: const EdgeInsets.all(4),
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

                  const SizedBox(height: 12),

                  // ── Members / Available List ──
                  Flexible(
                    child: Container(
                      decoration: BoxDecoration(
                        color: palette.bgElevated,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: palette.div),
                      ),
                      child: Builder(
                        builder: (context) {
                          if (_workspaceMembersTab == 'available') {
                            if (_isLoadingWorkspaceEmployees && _workspaceEmployees.isEmpty) {
                              return Center(
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
                                        'Retrieving employees from database...',
                                        style: UnoTypography.body(
                                          color: palette.textSec,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            }

                            final filteredAvailable = _availableEmployees.where((u) {
                              if (rawQuery.isEmpty) return true;
                              final name = (u.userName ?? '').toLowerCase();
                              final email = (u.userEmail ?? '').toLowerCase();
                              return name.contains(rawQuery) || email.contains(rawQuery);
                            }).toList();

                            if (filteredAvailable.isEmpty) {
                              return Center(
                                child: Padding(
                                  padding: const EdgeInsets.all(24),
                                  child: Text(
                                    rawQuery.isEmpty
                                        ? 'All registered employees are already assigned to this project!'
                                        : 'No employees found matching "$rawQuery"',
                                    textAlign: TextAlign.center,
                                    style: UnoTypography.body(
                                      color: palette.textSec,
                                      fontSize: 12.5,
                                    ),
                                  ),
                                ),
                              );
                            }

                            return ListView.separated(
                              shrinkWrap: true,
                              padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
                              itemCount: filteredAvailable.length,
                              separatorBuilder: (_, unused) => Divider(
                                height: 1,
                                color: palette.div,
                              ),
                              itemBuilder: (context, idx) {
                                final employee = filteredAvailable[idx];
                                final isAssigning = _assigningUserId == employee.userId;
                                final selectedRole = _employeeAssignRole[employee.userId] ?? 'MEMBER';

                                return Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 6),
                                  child: Row(
                                    children: [
                                      // Avatar
                                      Container(
                                        width: 32,
                                        height: 32,
                                        decoration: BoxDecoration(
                                          shape: BoxShape.circle,
                                          color: palette.live.withValues(alpha: 0.15),
                                          border: Border.all(
                                            color: palette.live.withValues(alpha: 0.35),
                                          ),
                                        ),
                                        alignment: Alignment.center,
                                        child: Text(
                                          _getMemberInitials(employee.userName, employee.userEmail),
                                          style: UnoTypography.mono(
                                            color: palette.live,
                                            fontSize: 11,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      // Name and Email
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              employee.userName ?? employee.userEmail ?? 'Employee',
                                              style: UnoTypography.body(
                                                color: palette.text,
                                                fontSize: 13,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              employee.userEmail ?? employee.userId,
                                              style: UnoTypography.body(
                                                color: palette.textSec,
                                                fontSize: 11.5,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      // Role selector dropdown
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
                                          setState(() {
                                            _employeeAssignRole[employee.userId] = val;
                                          });
                                        },
                                        itemBuilder: (context) => [
                                          PopupMenuItem(
                                            value: 'MEMBER',
                                            height: 36,
                                            child: Text('Member (Dev)',
                                                style: UnoTypography.body(
                                                    color: palette.text, fontSize: 12)),
                                          ),
                                          PopupMenuItem(
                                            value: 'ADMIN',
                                            height: 36,
                                            child: Text('Manager',
                                                style: UnoTypography.body(
                                                    color: palette.accent, fontSize: 12)),
                                          ),
                                          PopupMenuItem(
                                            value: 'VIEWER',
                                            height: 36,
                                            child: Text('Viewer',
                                                style: UnoTypography.body(
                                                    color: palette.textSec, fontSize: 12)),
                                          ),
                                        ],
                                        child: Container(
                                          height: 29,
                                          padding: const EdgeInsets.symmetric(horizontal: 8),
                                          decoration: BoxDecoration(
                                            color: palette.bgBase,
                                            borderRadius: BorderRadius.circular(6),
                                            border: Border.all(color: palette.div),
                                          ),
                                          child: Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              Text(
                                                selectedRole == 'ADMIN'
                                                    ? 'Manager'
                                                    : (selectedRole == 'VIEWER'
                                                        ? 'Viewer'
                                                        : 'Member'),
                                                style: UnoTypography.body(
                                                  color: palette.text,
                                                  fontSize: 11.5,
                                                  fontWeight: FontWeight.w500,
                                                ),
                                              ),
                                              const SizedBox(width: 4),
                                              Icon(Icons.keyboard_arrow_down,
                                                  size: 13, color: palette.textSec),
                                            ],
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      // + Assign Button
                                      InkWell(
                                        onTap: isAssigning
                                            ? null
                                            : () => _handleAssignEmployee(employee,
                                                role: selectedRole),
                                        borderRadius: BorderRadius.circular(6),
                                        child: Container(
                                          height: 29,
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 10),
                                          decoration: BoxDecoration(
                                            color: palette.accent,
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Center(
                                            child: isAssigning
                                                ? const SizedBox(
                                                    width: 12,
                                                    height: 12,
                                                    child: CircularProgressIndicator(
                                                      strokeWidth: 2,
                                                      color: Colors.white,
                                                    ),
                                                  )
                                                : Row(
                                                    mainAxisSize: MainAxisSize.min,
                                                    children: [
                                                      const Icon(Icons.add,
                                                          size: 13, color: Colors.white),
                                                      const SizedBox(width: 3),
                                                      Text(
                                                        'Assign',
                                                        style: UnoTypography.body(
                                                          color: Colors.white,
                                                          fontSize: 11.5,
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
                                );
                              },
                            );
                          }

                          // Assigned Tab
                          final filteredMembers = _projectMembers.where((m) {
                            if (rawQuery.isEmpty) return true;
                            final name = (m.userName ?? '').toLowerCase();
                            final email = (m.userEmail ?? '').toLowerCase();
                            return name.contains(rawQuery) || email.contains(rawQuery);
                          }).toList();

                          if (_isLoadingMembers && _projectMembers.isEmpty) {
                            return Center(
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
                            );
                          }

                          if (filteredMembers.isEmpty) {
                            return Center(
                              child: Padding(
                                padding: const EdgeInsets.all(24),
                                child: Text(
                                  rawQuery.isEmpty
                                      ? 'No employees assigned to this project yet.'
                                      : 'No members found matching "$rawQuery"',
                                  textAlign: TextAlign.center,
                                  style: UnoTypography.body(
                                    color: palette.textSec,
                                    fontSize: 12.5,
                                  ),
                                ),
                              ),
                            );
                          }

                          return AnimatedOpacity(
                            opacity: _isReloadingMembers ? 0.75 : 1.0,
                            duration: const Duration(milliseconds: 200),
                            child: ListView.separated(
                              shrinkWrap: true,
                              padding: const EdgeInsets.symmetric(
                                  vertical: 6, horizontal: 8),
                              itemCount: filteredMembers.length,
                              separatorBuilder: (_, unused) => Divider(
                                height: 1,
                                color: palette.div,
                              ),
                              itemBuilder: (context, idx) {
                                final member = filteredMembers[idx];
                                final role = member.role.toUpperCase();
                                final isMemberAdmin = role == 'ADMIN' ||
                                    role == 'MANAGER' ||
                                    role == 'LEAD';
                                final isMemberViewer = role == 'VIEWER';

                                final roleColor = isMemberAdmin
                                    ? palette.accent
                                    : (isMemberViewer
                                        ? palette.textSec
                                        : palette.live);

                                return Padding(
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 7, horizontal: 6),
                                  child: Row(
                                    children: [
                                      // Avatar
                                      Container(
                                        width: 32,
                                        height: 32,
                                        decoration: BoxDecoration(
                                          shape: BoxShape.circle,
                                          color: roleColor
                                              .withValues(alpha: 0.15),
                                          border: Border.all(
                                            color: roleColor
                                                .withValues(alpha: 0.35),
                                          ),
                                        ),
                                        alignment: Alignment.center,
                                        child: Text(
                                          _getMemberInitials(
                                              member.userName, member.userEmail),
                                          style: UnoTypography.mono(
                                            color: roleColor,
                                            fontSize: 11,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      // Name and Email
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              children: [
                                                Text(
                                                  member.userName ??
                                                      member.userEmail ??
                                                      'Employee',
                                                  style: UnoTypography.body(
                                                    color: palette.text,
                                                    fontSize: 13,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                ),
                                                const SizedBox(width: 8),
                                                // Role badge
                                                Container(
                                                  padding:
                                                      const EdgeInsets.symmetric(
                                                          horizontal: 6,
                                                          vertical: 1.5),
                                                  decoration: BoxDecoration(
                                                    color: roleColor
                                                        .withValues(alpha: 0.12),
                                                    border: Border.all(
                                                        color: roleColor
                                                            .withValues(
                                                                alpha: 0.3)),
                                                    borderRadius:
                                                        BorderRadius.circular(4),
                                                  ),
                                                  child: Text(
                                                    isMemberAdmin
                                                        ? 'MANAGER'
                                                        : role,
                                                    style: UnoTypography.mono(
                                                      color: roleColor,
                                                      fontSize: 9.5,
                                                      fontWeight:
                                                          FontWeight.w700,
                                                    ),
                                                  ),
                                                ),
                                              ],
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              member.userEmail ?? member.userId,
                                              style: UnoTypography.body(
                                                color: palette.textSec,
                                                fontSize: 11.5,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      // Remove button
                                      if (member.userEmail?.toLowerCase() != 'admin@acme.com' &&
                                          member.userName?.toLowerCase() != 'lead admin')
                                        Tooltip(
                                          message:
                                              'Remove employee from project',
                                          child: InkWell(
                                            onTap: () =>
                                                _handleRemoveMember(member),
                                            borderRadius:
                                                BorderRadius.circular(6),
                                            child: Padding(
                                              padding: const EdgeInsets.all(6),
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
                      Row(
                        children: [
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
      decoration: BoxDecoration(
        gradient: palette.headerGradient,
        border: Border(
          bottom: BorderSide(color: palette.div.withValues(alpha: 0.45)),
        ),
      ),
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
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOutCubic,
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: Colors.transparent,
                border: Border.all(color: palette.div),
                borderRadius: BorderRadius.circular(6),
              ),
              alignment: Alignment.center,
              child: AnimatedRotation(
                turns: widget.isDark ? 0.0 : 0.5,
                duration: const Duration(milliseconds: 240),
                curve: Curves.easeOutCubic,
                child: Icon(
                  widget.isDark ? LucideIcons.moon : LucideIcons.sun,
                  size: 14,
                  color: palette.textSec,
                ),
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
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1400),
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(
            horizontal: isNarrow ? 20 : 40,
            vertical: 24,
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
                    gradient: palette.sectionGradient,
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
                          icon: Icon(
                            Icons.hub_outlined,
                            size: 16,
                            color: widget.isDark ? const Color(0xFF0A0F20) : Colors.white,
                          ),
                          label: Text(
                            'Connect Workspace',
                            style: TextStyle(
                              color: widget.isDark ? const Color(0xFF0A0F20) : Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: palette.accent,
                            foregroundColor: widget.isDark ? const Color(0xFF0A0F20) : Colors.white,
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
        ),
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
    final Color buttonFg = filled
        ? (widget.isDark ? const Color(0xFF0A0F20) : Colors.white)
        : palette.text;
    final Color iconColor = filled
        ? (widget.isDark ? const Color(0xFF0A0F20) : Colors.white)
        : palette.textSec;

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
                          valueColor: AlwaysStoppedAnimation<Color>(buttonFg),
                        ),
                      ),
                    )
                  : Icon(
                      icon,
                      size: 15,
                      color: iconColor,
                    ),
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: UnoTypography.body(
                color: buttonFg,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProjectCard(ProjectItem project, UnoPalette palette) {
    return _OppositeProjectCard(
      project: project,
      isDark: widget.isDark,
      isManager: _isManager,
      onOpen: () => widget.onOpenProject(project),
      onManageWorkspace: () => _openManageWorkspace(project),
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
                    _buildSettingsRow('Primary Server URL', ApiService.baseUrl, palette),
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

/// Opposite-shade project card matching the Unotusk palette:
/// - Light page (#F2EFE9) -> Dark Obsidian Navy card (#0A0F20)
/// - Dark page  (#0A0F20) -> Light Sand Cream card   (#F5F2EB)
class _OppositeProjectCard extends StatefulWidget {
  final ProjectItem project;
  final bool isDark;
  final bool isManager;
  final VoidCallback onOpen;
  final VoidCallback onManageWorkspace;

  const _OppositeProjectCard({
    required this.project,
    required this.isDark,
    required this.isManager,
    required this.onOpen,
    required this.onManageWorkspace,
  });

  @override
  State<_OppositeProjectCard> createState() => _OppositeProjectCardState();
}

class _OppositeProjectCardState extends State<_OppositeProjectCard> {
  bool _isHovered = false;
  bool _isManageHovered = false;
  bool _isOpenHovered = false;

  @override
  Widget build(BuildContext context) {
    final project = widget.project;
    // Opposite shade to the page background
    final isCardDark = !widget.isDark;

    final isStopped = project.upsStatus.toUpperCase() == 'STOPPED' ||
        project.upsStatus.toUpperCase() == 'DELETED' ||
        project.upsStatus.toUpperCase() == 'OFFLINE' ||
        project.ingestionStatus.toLowerCase() == 'stopped' ||
        project.ingestionStatus.toLowerCase() == 'deleted';

    final isReady = !isStopped &&
        (project.upsStatus.toUpperCase() == 'READY' ||
            project.upsStatus.toUpperCase() == 'ACTIVE' ||
            project.ingestionStatus.toLowerCase() == 'live');

    // Exact palette tokens for opposite shade
    final cardBg = isCardDark
        ? (_isHovered ? const Color(0xFF12172A) : const Color(0xFF0A0F20))
        : (_isHovered ? const Color(0xFFFFFFFF) : const Color(0xFFF5F2EB));

    final cardBorder = isCardDark
        ? (_isHovered ? const Color(0xFF3A3F52) : const Color(0xFF222533))
        : (_isHovered ? const Color(0xFFD2C9BA) : const Color(0xFFE4DFD6));

    final iconBoxBg =
        isCardDark ? const Color(0xFF161A29) : const Color(0xFFFFFFFF);
    final iconBoxBorder =
        isCardDark ? const Color(0xFF2E313C) : const Color(0xFFE4DFD6);
    final iconColor =
        isCardDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20);

    final titleColor =
        isCardDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);
    final subtitleColor =
        isCardDark ? const Color(0xFF84878F) : const Color(0xFF6B686A);
    final portColor =
        isCardDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20);

    final manageBg = isCardDark
        ? (_isManageHovered ? const Color(0xFF1E2336) : const Color(0xFF161A29))
        : (_isManageHovered ? const Color(0xFFF0ECE4) : const Color(0xFFFFFFFF));
    final manageBorder =
        isCardDark ? const Color(0xFF2E313C) : const Color(0xFFE4DFD6);
    final manageFg =
        isCardDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20);

    final openBg = isCardDark
        ? (_isOpenHovered ? const Color(0xFFD8CFBF) : const Color(0xFFCBC1B4))
        : (_isOpenHovered ? const Color(0xFF161A29) : const Color(0xFF0A0F20));
    final openFg =
        isCardDark ? const Color(0xFF0A0F20) : const Color(0xFFFFFFFF);

    const liveGreen = Color(0xFF22C55E);

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      cursor: isStopped ? SystemMouseCursors.basic : SystemMouseCursors.click,
      child: GestureDetector(
        onTap: isStopped ? null : widget.onOpen,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            color: cardBg,
            border: Border.all(color: cardBorder, width: 1.1),
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: (isCardDark ? const Color(0xFF0A0F20) : Colors.black)
                    .withValues(
                  alpha: isCardDark
                      ? (_isHovered ? 0.28 : 0.16)
                      : (_isHovered ? 0.34 : 0.22),
                ),
                blurRadius: _isHovered ? 22 : 14,
                offset: Offset(0, _isHovered ? 6 : 3),
              ),
            ],
          ),
          child: Row(
            children: [
              // Repository / Project icon
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: iconBoxBg,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: iconBoxBorder),
                ),
                alignment: Alignment.center,
                child: Icon(
                  LucideIcons.folderGit2,
                  size: 18,
                  color: iconColor,
                ),
              ),

              const SizedBox(width: 15),

              // Project name, status & metadata
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Flexible(
                          child: Text(
                            project.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: UnoTypography.body(
                              color: titleColor,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        if (isStopped)
                          Tooltip(
                            message: 'Server Stopped on Backend',
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 7, vertical: 2.5),
                              decoration: BoxDecoration(
                                color: Colors.redAccent.withValues(alpha: 0.14),
                                border: Border.all(
                                    color: Colors.redAccent
                                        .withValues(alpha: 0.4)),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 6,
                                    height: 6,
                                    decoration: const BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: Colors.redAccent,
                                    ),
                                  ),
                                  const SizedBox(width: 4),
                                  Text(
                                    'STOPPED',
                                    style: UnoTypography.mono(
                                      color: Colors.redAccent,
                                      fontSize: 10,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                        else if (isReady)
                          Tooltip(
                            message: 'Active & Ready',
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 7, vertical: 2.5),
                              decoration: BoxDecoration(
                                color: liveGreen.withValues(
                                    alpha: isCardDark ? 0.12 : 0.14),
                                border: Border.all(
                                    color: liveGreen.withValues(alpha: 0.35)),
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    width: 6.5,
                                    height: 6.5,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: liveGreen,
                                      boxShadow: [
                                        BoxShadow(
                                          color: liveGreen.withValues(
                                              alpha: 0.65),
                                          blurRadius: 4,
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 5),
                                  Text(
                                    'Active',
                                    style: UnoTypography.body(
                                      color: isCardDark
                                          ? const Color(0xFF4ADE80)
                                          : const Color(0xFF15803D),
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                        else
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2.5),
                            decoration: BoxDecoration(
                              color: iconBoxBg,
                              border: Border.all(color: iconBoxBorder),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              project.upsStatus.toUpperCase(),
                              style: UnoTypography.mono(
                                color: subtitleColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                      ],
                    ),
                    if ((project.description != null &&
                            project.description!.isNotEmpty) ||
                        project.port != null) ...[
                      const SizedBox(height: 3.5),
                      Row(
                        children: [
                          if (project.description != null &&
                              project.description!.isNotEmpty)
                            Flexible(
                              child: Text(
                                project.description!,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: UnoTypography.mono(
                                  color: subtitleColor,
                                  fontSize: 11.5,
                                ),
                              ),
                            ),
                          if (project.port != null) ...[
                            if (project.description != null &&
                                project.description!.isNotEmpty)
                              Padding(
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 6),
                                child: Text(
                                  '·',
                                  style: UnoTypography.mono(
                                    color:
                                        subtitleColor.withValues(alpha: 0.65),
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                            Text(
                              'Port ${project.port}',
                              style: UnoTypography.mono(
                                color: portColor,
                                fontSize: 11.5,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(width: 16),

              // Manage Workspace button (Manager Role Only)
              if (widget.isManager) ...[
                MouseRegion(
                  onEnter: (_) => setState(() => _isManageHovered = true),
                  onExit: (_) => setState(() => _isManageHovered = false),
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: widget.onManageWorkspace,
                    behavior: HitTestBehavior.opaque,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 160),
                      curve: Curves.easeOutCubic,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 7.5),
                      decoration: BoxDecoration(
                        color: manageBg,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: manageBorder),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            LucideIcons.users,
                            size: 13.5,
                            color: subtitleColor,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'Manage Workspace',
                            style: UnoTypography.body(
                              color: manageFg,
                              fontSize: 12.5,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
              ],

              // Primary Open CTA / Server Stopped indicator
              if (isStopped)
                Tooltip(
                  message: 'Cannot open: Project server is stopped on backend',
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 7.5),
                    decoration: BoxDecoration(
                      color: iconBoxBg,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: iconBoxBorder),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.power_off, size: 13, color: subtitleColor),
                        const SizedBox(width: 6),
                        Text(
                          'Server Stopped',
                          style: UnoTypography.body(
                            color: subtitleColor,
                            fontSize: 12.5,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              else
                MouseRegion(
                  onEnter: (_) => setState(() => _isOpenHovered = true),
                  onExit: (_) => setState(() => _isOpenHovered = false),
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: widget.onOpen,
                    behavior: HitTestBehavior.opaque,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 160),
                      curve: Curves.easeOutCubic,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 7.5),
                      decoration: BoxDecoration(
                        color: openBg,
                        borderRadius: BorderRadius.circular(8),
                        boxShadow: [
                          BoxShadow(
                            color: openBg.withValues(
                                alpha: _isOpenHovered ? 0.30 : 0.12),
                            blurRadius: _isOpenHovered ? 10 : 4,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Open',
                            style: UnoTypography.body(
                              color: openFg,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(width: 5),
                          AnimatedSlide(
                            duration: const Duration(milliseconds: 160),
                            curve: Curves.easeOutCubic,
                            offset: _isOpenHovered
                                ? const Offset(0.18, 0)
                                : Offset.zero,
                            child: Icon(
                              Icons.arrow_forward_rounded,
                              size: 14.5,
                              color: openFg,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
