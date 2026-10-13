import 'dart:async';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/window_title_bar.dart';

class AuthScreen extends StatefulWidget {
  final UnoPalette palette;
  final Function(UserModel user) onAuthenticated;
  final String? sessionMsg;

  const AuthScreen({
    super.key,
    required this.palette,
    required this.onAuthenticated,
    this.sessionMsg,
  });

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  // Mode: 0 = Sign In, 1 = Create Workspace, 2 = Select Project Server
  int _activeMode = 0;
  bool _isServerConnected = false;
  Timer? _healthTimer;

  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _orgController =
      TextEditingController(text: 'Acme Corporation');

  bool _obscurePassword = true;
  String _selectedRole = 'Member (Dev)';
  bool _termsAgreed = true;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _checkServer();
    _healthTimer =
        Timer.periodic(const Duration(seconds: 4), (_) => _checkServer());
  }

  void _checkServer() async {
    final ok = await ApiService.checkHealth();
    if (mounted) {
      setState(() {
        _isServerConnected = ok;
      });
    }
  }

  @override
  void dispose() {
    _healthTimer?.cancel();
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    _orgController.dispose();
    super.dispose();
  }

  bool _validateAcmeEmail(String rawEmail) {
    final email = rawEmail.trim().toLowerCase();
    if (email.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter your organization email address.';
      });
      return false;
    }
    if (!email.contains('@')) {
      setState(() {
        _errorMessage = 'Please enter a valid email format (e.g. name@acme.com).';
      });
      return false;
    }
    if (!email.endsWith('@acme.com')) {
      setState(() {
        _errorMessage =
            'Access restricted: Only organization accounts ending in @acme.com are permitted.';
      });
      return false;
    }
    return true;
  }

  void _handleSignIn() async {
    final email = _emailController.text.trim().toLowerCase();
    final password = _passwordController.text;

    if (!_validateAcmeEmail(email)) return;

    if (password.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter your password.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final user = await ApiService.login(email: email, password: password);
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      widget.onAuthenticated(user);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  void _handleCreateWorkspace() async {
    final email = _emailController.text.trim().toLowerCase();
    final name = _nameController.text.trim();
    final org = _orgController.text.trim();
    final password = _passwordController.text;

    if (name.isEmpty) {
      setState(() {
        _errorMessage = 'Please enter your full name.';
      });
      return;
    }

    if (!_validateAcmeEmail(email)) return;

    if (password.length < 8) {
      setState(() {
        _errorMessage = 'Password must be at least 8 characters long.';
      });
      return;
    }

    if (!_termsAgreed) {
      setState(() {
        _errorMessage = 'Please accept the terms of service to proceed.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final user = await ApiService.createOrganisation(
        fullName: name,
        orgName: org.isNotEmpty ? org : 'Acme Corporation',
        password: password,
        role: _selectedRole,
        email: email,
      );
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      widget.onAuthenticated(user);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Widget _buildErrorBanner() {
    if (_errorMessage == null) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFD4725A).withValues(alpha: 0.12),
        border: Border.all(
          color: const Color(0xFFD4725A).withValues(alpha: 0.5),
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(LucideIcons.alertTriangle,
              size: 16, color: Color(0xFFD4725A)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _errorMessage!,
              style: UnoTypography.body(
                color: const Color(0xFFE89885),
                fontSize: 12.5,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: widget.palette.bgBase,
      body: Column(
        children: [
          // ── Window Title Bar ──
          WindowTitleBar(
            palette: widget.palette,
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: widget.palette.accent.withValues(alpha: 0.125),
                border: Border.all(
                  color: widget.palette.accent.withValues(alpha: 0.25),
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                'Acme Workspace',
                style: UnoTypography.mono(
                  color: widget.palette.accent,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),

          // ── Center Card ──
          Expanded(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(24, 40, 24, 48),
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 420),
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 32),
                  decoration: BoxDecoration(
                    color: widget.palette.bgSurface,
                    border: Border.all(color: widget.palette.div),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(
                            alpha: widget.palette.isDark ? 0.36 : 0.05),
                        blurRadius: widget.palette.isDark ? 56 : 36,
                        offset: const Offset(0, 16),
                      ),
                    ],
                  ),
                  child: _activeMode == 2
                      ? _buildServerList()
                      : _buildAuthCard(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAuthCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        // ── Organization Badge ──
        Align(
          alignment: Alignment.centerLeft,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: widget.palette.accent.withValues(alpha: 0.08),
              border: Border.all(
                color: widget.palette.accent.withValues(alpha: 0.20),
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(LucideIcons.shieldCheck,
                    size: 13, color: widget.palette.accent),
                const SizedBox(width: 6),
                Text(
                  'Acme Corporation Auth',
                  style: UnoTypography.mono(
                    color: widget.palette.text,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),

        // ── Heading & Subtitle ──
        Text(
          _activeMode == 0 ? 'Sign in to Unotusk' : 'Create Acme Workspace',
          style: UnoTypography.brandSerif(
            palette: widget.palette,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          _activeMode == 0
              ? 'Enter your organization email credentials (@acme.com) to access project intelligence.'
              : 'Register a new project intelligence workspace using your @acme.com corporate identity.',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 18),

        // ── Segmented Mode Switcher (Sign In vs Create Workspace) ──
        Container(
          height: 38,
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: widget.palette.div),
          ),
          child: Row(
            children: [
              Expanded(
                child: _buildTabButton(
                  'Sign In',
                  _activeMode == 0,
                  () => setState(() {
                    _activeMode = 0;
                    _errorMessage = null;
                  }),
                ),
              ),
              Expanded(
                child: _buildTabButton(
                  'Create Workspace',
                  _activeMode == 1,
                  () => setState(() {
                    _activeMode = 1;
                    _errorMessage = null;
                  }),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        _buildErrorBanner(),

        // ── Mode-specific form ──
        if (_activeMode == 0) _buildSignInForm() else _buildCreateWorkspaceForm(),

        _buildServerFooter(),
      ],
    );
  }

  Widget _buildTabButton(String label, bool isSelected, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(7),
      child: Container(
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: isSelected ? widget.palette.bgSurface : Colors.transparent,
          borderRadius: BorderRadius.circular(7),
          border: isSelected
              ? Border.all(color: widget.palette.div)
              : null,
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.1),
                    blurRadius: 4,
                    offset: const Offset(0, 1),
                  ),
                ]
              : null,
        ),
        child: Text(
          label,
          style: UnoTypography.body(
            color: isSelected ? widget.palette.text : widget.palette.textSec,
            fontSize: 12.5,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────
  //  Sign In Form
  // ─────────────────────────────────────────────────────────────
  Widget _buildSignInForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Work Email
        Text(
          'Work Email (@acme.com)',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: TextField(
            controller: _emailController,
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'alex@acme.com',
              hintStyle: UnoTypography.body(
                color: widget.palette.textSec.withValues(alpha: 0.6),
                fontSize: 13,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 11),
            ),
            onSubmitted: (_) => _handleSignIn(),
          ),
        ),
        const SizedBox(height: 14),

        // Password with eye toggle
        Text(
          'Password',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  style: UnoTypography.body(
                      color: widget.palette.text, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: '••••••••',
                    hintStyle: UnoTypography.body(
                      color: widget.palette.textSec.withValues(alpha: 0.6),
                      fontSize: 13,
                    ),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(vertical: 11),
                  ),
                  onSubmitted: (_) => _handleSignIn(),
                ),
              ),
              InkWell(
                onTap: () =>
                    setState(() => _obscurePassword = !_obscurePassword),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.all(4),
                  child: Icon(
                    _obscurePassword ? LucideIcons.eye : LucideIcons.eyeOff,
                    size: 16,
                    color: widget.palette.textSec,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // Submit Button
        SizedBox(
          height: 42,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _handleSignIn,
            style: ElevatedButton.styleFrom(
              backgroundColor: widget.palette.accent,
              foregroundColor: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(9),
              ),
            ),
            child: _isLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : Text(
                    'Sign In',
                    style: UnoTypography.body(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────
  //  Create Workspace Form
  // ─────────────────────────────────────────────────────────────
  Widget _buildCreateWorkspaceForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Full Name
        Text(
          'Full Name',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: TextField(
            controller: _nameController,
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Alex Morgan',
              hintStyle: UnoTypography.body(
                color: widget.palette.textSec.withValues(alpha: 0.6),
                fontSize: 13,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 11),
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Organisation Name
        Text(
          'Organisation Name',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: TextField(
            controller: _orgController,
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Acme Corporation',
              hintStyle: UnoTypography.body(
                color: widget.palette.textSec.withValues(alpha: 0.6),
                fontSize: 13,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 11),
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Work Email
        Text(
          'Work Email (@acme.com)',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: TextField(
            controller: _emailController,
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'alex@acme.com',
              hintStyle: UnoTypography.body(
                color: widget.palette.textSec.withValues(alpha: 0.6),
                fontSize: 13,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 11),
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Password
        Text(
          'Password (min 8 chars)',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: widget.palette.bgElevated,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: TextField(
            controller: _passwordController,
            obscureText: true,
            style: UnoTypography.body(color: widget.palette.text, fontSize: 13),
            decoration: InputDecoration(
              hintText: '••••••••',
              hintStyle: UnoTypography.body(
                color: widget.palette.textSec.withValues(alpha: 0.6),
                fontSize: 13,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 11),
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Role Dropdown
        Text(
          'Role',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: widget.palette.bgSurface,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(10),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: _selectedRole,
              dropdownColor: widget.palette.bgElevated,
              icon: Icon(Icons.arrow_drop_down, color: widget.palette.textSec),
              isExpanded: true,
              style:
                  UnoTypography.body(color: widget.palette.text, fontSize: 13),
              items: ['Member (Dev)', 'Manager']
                  .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                  .toList(),
              onChanged: (val) =>
                  setState(() => _selectedRole = val ?? 'Member (Dev)'),
            ),
          ),
        ),
        const SizedBox(height: 14),

        // Terms Checkbox
        Row(
          children: [
            Checkbox(
              value: _termsAgreed,
              activeColor: widget.palette.accent,
              onChanged: (val) => setState(() => _termsAgreed = val ?? false),
            ),
            Expanded(
              child: Text(
                'I agree to the Unotusk terms of service',
                style: UnoTypography.body(
                  color: widget.palette.textSec,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Submit Button
        SizedBox(
          height: 42,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _handleCreateWorkspace,
            style: ElevatedButton.styleFrom(
              backgroundColor: widget.palette.accent,
              foregroundColor: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(9),
              ),
            ),
            child: _isLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : Text(
                    'Create workspace',
                    style: UnoTypography.body(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────
  //  Server List Screen
  // ─────────────────────────────────────────────────────────────
  Widget _buildServerList() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Select project server',
          style: UnoTypography.brandSerif(
            palette: widget.palette,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Choose a running workspace instance to connect to.',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 20),

        FutureBuilder<List<ProjectItem>>(
          future: ApiService.fetchProjects(),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const SizedBox(
                height: 100,
                child: Center(
                  child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              );
            }
            if (snapshot.hasError) {
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Could not connect to registry: ${snapshot.error}',
                  style: UnoTypography.body(color: Colors.red.shade300, fontSize: 13),
                ),
              );
            }

            final servers = snapshot.data ?? [];
            if (servers.isEmpty) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  'No running servers found.',
                  style: UnoTypography.body(color: widget.palette.textSec, fontSize: 13),
                ),
              );
            }

            return Column(
              children: servers.map((project) {
                final port = project.port ?? 8000;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: InkWell(
                    onTap: () {
                      final uri = Uri.parse(ApiService.baseUrl);
                      ApiService.serverHost = '${uri.host}:$port';
                      ApiService.baseUrl = 'http://${ApiService.serverHost}';
                      setState(() => _activeMode = 0);
                    },
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: widget.palette.bgElevated,
                        border: Border.all(color: widget.palette.div),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.storage, color: widget.palette.textSec, size: 18),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  project.name,
                                  style: UnoTypography.body(
                                    color: widget.palette.text,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Text(
                                  'Port: $port',
                                  style: UnoTypography.mono(
                                    color: widget.palette.textSec,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right, color: widget.palette.textSec, size: 20),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            );
          },
        ),
        const SizedBox(height: 16),

        TextButton(
          onPressed: () => setState(() => _activeMode = 0),
          child: Text(
            'Back',
            style: UnoTypography.body(
              color: widget.palette.textSec,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────
  //  Server Status Footer
  // ─────────────────────────────────────────────────────────────
  Widget _buildServerFooter() {
    final isOnline = _isServerConnected || ApiService.isConnected;
    final dotColor = isOnline
        ? const Color(0xFF6EC8B8) // Green / mint teal when server is online
        : const Color(0xFFE05A5A); // Red when server is offline

    return Column(
      children: [
        const SizedBox(height: 24),
        InkWell(
          onTap: () {
            setState(() => _activeMode = 2);
          },
          borderRadius: BorderRadius.circular(4),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: dotColor,
                    boxShadow: [
                      BoxShadow(
                        color: dotColor.withValues(alpha: 0.45),
                        blurRadius: 4,
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    'Server: ${ApiService.baseUrl}',
                    overflow: TextOverflow.ellipsis,
                    style: UnoTypography.mono(
                      color: widget.palette.textSec,
                      fontSize: 11,
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                Icon(
                  LucideIcons.arrowLeftRight,
                  size: 11,
                  color: widget.palette.textSec.withValues(alpha: 0.7),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
