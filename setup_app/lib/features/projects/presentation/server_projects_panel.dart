import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../data/server_project_client.dart';

class ServerProjectsPanel extends StatefulWidget {
  final String serverUrl;
  final String adminEmail;
  final String adminPassword;

  const ServerProjectsPanel({
    super.key,
    required this.serverUrl,
    required this.adminEmail,
    required this.adminPassword,
  });

  @override
  State<ServerProjectsPanel> createState() => _ServerProjectsPanelState();
}

class _ServerProjectsPanelState extends State<ServerProjectsPanel> {
  final _client = ServerProjectClient();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = true;
  String? _token;
  String? _orgId;
  String? _errorMessage;
  List<Map<String, dynamic>> _projects = [];

  @override
  void initState() {
    super.initState();
    _emailController.text = widget.adminEmail;
    _passwordController.text = widget.adminPassword;
    _initAndLoad();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _initAndLoad({String? emailOverride, String? passwordOverride}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final targetEmail = emailOverride ??
        (_emailController.text.trim().isNotEmpty
            ? _emailController.text.trim()
            : (widget.adminEmail.isNotEmpty ? widget.adminEmail : 'admin@unotusk.local'));
    final targetPassword = passwordOverride ??
        (_passwordController.text.isNotEmpty
            ? _passwordController.text
            : (widget.adminPassword.isNotEmpty ? widget.adminPassword : 'adminpassword123'));

    try {
      final auth = await _client.authenticateAdmin(
        serverUrl: widget.serverUrl,
        email: targetEmail,
        password: targetPassword,
      );

      if (auth == null) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'Could not authenticate with server. Ensure server is active and credentials are correct.';
        });
        return;
      }

      _token = auth.token;
      _orgId = auth.orgId;

      await _refreshProjects();
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'Failed to load projects: $e';
        });
      }
    }
  }

  Future<void> _refreshProjects() async {
    if (_token == null) return;
    final projects = await _client.listProjects(
      serverUrl: widget.serverUrl,
      token: _token!,
    );
    if (mounted) {
      setState(() {
        _projects = projects;
        _isLoading = false;
      });
    }
  }

  Future<void> _showCreateProjectDialog() async {
    if (_token == null || _orgId == null) return;

    final nameController = TextEditingController();
    final repoUrlController = TextEditingController();
    final branchController = TextEditingController(text: 'main');
    bool isCreating = false;
    String? dialogError;

    await showDialog(
      context: context,
      barrierDismissible: !isCreating,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            return AlertDialog(
              title: const Text('Provision New Project Workspace'),
              content: SizedBox(
                width: 480,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'The server will allocate an isolated Data Plane port and launch a dedicated compute instance for this codebase.',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate600),
                    ),
                    const SizedBox(height: 16),
                    AppTextField(
                      label: 'Project Name',
                      hintText: 'e.g. Core Engine',
                      controller: nameController,
                    ),
                    const SizedBox(height: 12),
                    AppTextField(
                      label: 'Git Repository URL',
                      hintText: 'https://github.com/org/repo.git',
                      controller: repoUrlController,
                    ),
                    const SizedBox(height: 12),
                    AppTextField(
                      label: 'Default Branch',
                      hintText: 'main',
                      controller: branchController,
                    ),
                    if (dialogError != null) ...[
                      const SizedBox(height: 12),
                      Text(dialogError!, style: const TextStyle(color: AppColors.error, fontSize: 12)),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: isCreating ? null : () => Navigator.pop(dialogContext),
                  child: const Text('Cancel'),
                ),
                AppButton(
                  label: 'Provision Project & Port',
                  isLoading: isCreating,
                  onPressed: () async {
                    final name = nameController.text.trim();
                    if (name.isEmpty) {
                      setDialogState(() => dialogError = 'Project name is required.');
                      return;
                    }

                    setDialogState(() {
                      isCreating = true;
                      dialogError = null;
                    });

                    final messenger = ScaffoldMessenger.of(context);
                    final nav = Navigator.of(dialogContext);

                    try {
                      final serverPort = Uri.tryParse(widget.serverUrl)?.port;
                      final created = await _client.createProject(
                        serverUrl: widget.serverUrl,
                        token: _token!,
                        name: name,
                        orgId: _orgId!,
                        repoUrl: repoUrlController.text.trim().isNotEmpty
                            ? repoUrlController.text.trim()
                            : null,
                        port: serverPort,
                      );

                      if (created != null) {
                        nav.pop();
                        if (mounted) {
                          await _refreshProjects();
                          final port = created['port'];
                          messenger.showSnackBar(
                            SnackBar(
                              content: Text('Project "$name" successfully created on Port :${port ?? "dynamic"}'),
                              backgroundColor: AppColors.success,
                            ),
                          );
                        }
                      } else {
                        setDialogState(() {
                          isCreating = false;
                          dialogError = 'Failed to provision project.';
                        });
                      }
                    } catch (e) {
                      setDialogState(() {
                        isCreating = false;
                        dialogError = 'Error: $e';
                      });
                    }
                  },
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 12),
              Text('Connecting to server project engine...'),
            ],
          ),
        ),
      );
    }

    if (_errorMessage != null || _token == null) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: AppCard(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Admin Authentication', style: AppTextStyles.h3),
              const SizedBox(height: 6),
              Text(
                'Enter admin credentials to manage projects and ports on ${widget.serverUrl}.',
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate600),
              ),
              const SizedBox(height: 16),
              AppTextField(
                label: 'Admin Email',
                hintText: 'admin@company.com',
                controller: _emailController,
              ),
              const SizedBox(height: 12),
              AppTextField(
                label: 'Password',
                hintText: '••••••••',
                obscureText: true,
                controller: _passwordController,
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 12),
                Text(_errorMessage!, style: const TextStyle(color: AppColors.error, fontSize: 13)),
              ],
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  AppButton(
                    label: 'Connect & Authenticate',
                    onPressed: () => _initAndLoad(),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Project Workspaces & Port Allocations', style: AppTextStyles.h3),
                const SizedBox(height: 2),
                Text(
                  'Connected on dedicated ports. Admin (lead@acme.com) allocates team access via the central workspace on port 28000.',
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate600),
                ),
              ],
            ),
            AppButton(
              label: 'Add Project',
              icon: Icons.add,
              onPressed: _showCreateProjectDialog,
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (_projects.isEmpty)
          AppCard(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: Column(
                children: [
                  const Icon(Icons.folder_open_outlined, size: 36, color: AppColors.slate400),
                  const SizedBox(height: 8),
                  Text('No projects provisioned on this server yet.', style: AppTextStyles.bodyMedium),
                  const SizedBox(height: 4),
                  Text(
                    'Click "Add Project" to allocate an isolated port and repository workspace.',
                    style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                  ),
                  const SizedBox(height: 16),
                  AppButton(
                    label: 'Provision First Project',
                    icon: Icons.add,
                    onPressed: _showCreateProjectDialog,
                  ),
                ],
              ),
            ),
          )
        else
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _projects.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final proj = _projects[index];
              final port = proj['port'];
              final status = proj['status']?.toString() ?? 'ACTIVE';
              final serverPort = Uri.tryParse(widget.serverUrl)?.port ?? 28000;
              final displayPort = port ?? serverPort;

              return AppCard(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Center(
                        child: Icon(Icons.code, color: AppColors.primary, size: 20),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(proj['name'] ?? 'Unnamed', style: AppTextStyles.h3),
                              const SizedBox(width: 8),
                              // Dedicated Port Badge
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: AppColors.successBg,
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: AppColors.successBorder),
                                ),
                                child: Text(
                                  'PORT :$displayPort',
                                  style: AppTextStyles.code.copyWith(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.success,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              // Status Badge
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: AppColors.slate100,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  status.toUpperCase(),
                                  style: AppTextStyles.bodySmall.copyWith(fontSize: 10, fontWeight: FontWeight.w600),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            proj['repository']?['full_name'] ?? proj['slug'] ?? 'Dedicated Data Plane Instance',
                            style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.08),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.admin_panel_settings_outlined, size: 14, color: AppColors.primary),
                          const SizedBox(width: 6),
                          Text(
                            'Open for Admin Access',
                            style: AppTextStyles.label.copyWith(fontSize: 12, color: AppColors.primary),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
      ],
    );
  }
}
