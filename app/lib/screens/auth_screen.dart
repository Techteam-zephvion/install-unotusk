import 'dart:async';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/server_discovery_service.dart';
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
  bool _isScanning = false;
  ServerDiscoveryResult? _discoveryResult;
  Timer? _healthTimer;

  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _orgController = TextEditingController();

  bool _obscurePassword = true;
  String _selectedRole = 'Member (Dev)';
  bool _termsAgreed = true;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initServer();
    _healthTimer =
        Timer.periodic(const Duration(seconds: 4), (_) => _checkServer());
  }

  void _initServer({bool forceRescan = false}) async {
    setState(() {
      _isScanning = true;
    });
    final result = await ApiService.autoDetectWithResult(forceRescan: forceRescan);
    if (mounted) {
      setState(() {
        _isScanning = false;
        _isServerConnected = ApiService.isConnected;
        _discoveryResult = result;
      });
    }
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

  Widget _buildServerDiscoveryStatusCard() {
    if (_isScanning) {
      return Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: widget.palette.bgElevated,
          border: Border.all(color: widget.palette.div),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(widget.palette.accent),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Searching network for active Unotusk server...',
                style: UnoTypography.body(
                  color: widget.palette.textSec,
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
      );
    }

    if (_isServerConnected) {
      return const SizedBox.shrink();
    }

    final result = _discoveryResult ?? ApiService.lastDiscoveryResult;
    if (result == null || result.isSuccess) {
      return const SizedBox.shrink();
    }

    final subnet = result.scannedSubnet ?? 'local network';

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFD4725A).withValues(alpha: 0.08),
        border: Border.all(color: const Color(0xFFD4725A).withValues(alpha: 0.35)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(
                LucideIcons.serverOff,
                size: 16,
                color: Color(0xFFD4725A),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'No servers are available',
                  style: UnoTypography.body(
                    color: const Color(0xFFE89885),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFD4725A).withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '0/${result.totalScanned > 0 ? result.totalScanned : 254} alive',
                  style: UnoTypography.mono(
                    color: const Color(0xFFE89885),
                    fontSize: 10.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Scanned $subnet on port 28000. No running Unotusk Control Plane responded.',
            style: UnoTypography.body(
              color: widget.palette.textSec,
              fontSize: 11.5,
            ),
          ),
          const SizedBox(height: 8),

          // Clean terminal error log box
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFF141412),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: widget.palette.div),
            ),
            constraints: const BoxConstraints(maxHeight: 110),
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: result.logs.map((line) {
                  final isErr = line.contains('[ERROR]');
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 2),
                    child: Text(
                      line,
                      style: UnoTypography.mono(
                        color: isErr
                            ? const Color(0xFFE89885)
                            : widget.palette.textSec.withValues(alpha: 0.85),
                        fontSize: 10,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),

          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              InkWell(
                onTap: _showServerSwitchDialog,
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: Text(
                    'Manual IP',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 11.5,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              InkWell(
                onTap: () => _initServer(forceRescan: true),
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: widget.palette.bgElevated,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: widget.palette.div),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        LucideIcons.refreshCw,
                        size: 11,
                        color: widget.palette.text,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Re-scan Subnet',
                        style: UnoTypography.body(
                          color: widget.palette.text,
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
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
          ),

          // ── Center Card (Fitted & strictly non-scrollable) ──
          Expanded(
            child: Center(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.center,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  curve: Curves.easeOutCubic,
                  constraints: BoxConstraints(
                    maxWidth: _activeMode == 1 ? 580 : (_activeMode == 2 ? 460 : 440),
                  ),
                  margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 22),
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
        // ── Heading & Subtitle ──
        Text(
          _activeMode == 0 ? 'Sign in to Unotusk' : 'Sign up to Unotusk',
          style: UnoTypography.brandSerif(
            palette: widget.palette,
            fontSize: 22,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          _activeMode == 0
              ? 'Enter your work email and password to access your workspace.'
              : 'Register a new project intelligence workspace.',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12.5,
          ),
        ),
        const SizedBox(height: 14),

        // ── Segmented Mode Switcher (Sign In vs Sign Up) ──
        Container(
          height: 36,
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
                  'Sign Up',
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
        const SizedBox(height: 14),

        _buildErrorBanner(),

        _buildServerDiscoveryStatusCard(),

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
          'Work Email',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 5),
        Container(
          height: 38,
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
              contentPadding: const EdgeInsets.symmetric(vertical: 9),
              isDense: true,
            ),
            onSubmitted: (_) => _handleSignIn(),
          ),
        ),
        const SizedBox(height: 10),

        // Password with eye toggle
        Text(
          'Password',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 5),
        Container(
          height: 38,
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
                    contentPadding: const EdgeInsets.symmetric(vertical: 9),
                    isDense: true,
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
        const SizedBox(height: 16),

        // Submit Button
        SizedBox(
          height: 40,
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
  //  Create Workspace / Sign Up Form (Horizontal 2-Column Layout)
  // ─────────────────────────────────────────────────────────────
  Widget _buildCreateWorkspaceForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Row 1: Full Name & Organisation Name
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Full Name',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Container(
                    height: 38,
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    decoration: BoxDecoration(
                      color: widget.palette.bgElevated,
                      border: Border.all(color: widget.palette.div),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: TextField(
                      controller: _nameController,
                      style: UnoTypography.body(
                          color: widget.palette.text, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'Alex Morgan',
                        hintStyle: UnoTypography.body(
                          color: widget.palette.textSec.withValues(alpha: 0.6),
                          fontSize: 13,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(vertical: 9),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Organisation Name',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Container(
                    height: 38,
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    decoration: BoxDecoration(
                      color: widget.palette.bgElevated,
                      border: Border.all(color: widget.palette.div),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: TextField(
                      controller: _orgController,
                      style: UnoTypography.body(
                          color: widget.palette.text, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'Your organization',
                        hintStyle: UnoTypography.body(
                          color: widget.palette.textSec.withValues(alpha: 0.6),
                          fontSize: 13,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(vertical: 9),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // Row 2: Work Email & Password
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Work Email',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Container(
                    height: 38,
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    decoration: BoxDecoration(
                      color: widget.palette.bgElevated,
                      border: Border.all(color: widget.palette.div),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: TextField(
                      controller: _emailController,
                      style: UnoTypography.body(
                          color: widget.palette.text, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'alex@acme.com',
                        hintStyle: UnoTypography.body(
                          color: widget.palette.textSec.withValues(alpha: 0.6),
                          fontSize: 13,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(vertical: 9),
                        isDense: true,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Password (min 8 chars)',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Container(
                    height: 38,
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
                              contentPadding: const EdgeInsets.symmetric(vertical: 9),
                              isDense: true,
                            ),
                          ),
                        ),
                        InkWell(
                          onTap: () => setState(
                              () => _obscurePassword = !_obscurePassword),
                          borderRadius: BorderRadius.circular(4),
                          child: Padding(
                            padding: const EdgeInsets.all(4),
                            child: Icon(
                              _obscurePassword
                                  ? LucideIcons.eye
                                  : LucideIcons.eyeOff,
                              size: 16,
                              color: widget.palette.textSec,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // Row 3: Role Dropdown & Terms Checkbox
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Role',
                    style: UnoTypography.body(
                      color: widget.palette.textSec,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Container(
                    height: 38,
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
                        icon: Icon(Icons.arrow_drop_down,
                            color: widget.palette.textSec),
                        isExpanded: true,
                        style: UnoTypography.body(
                            color: widget.palette.text, fontSize: 13),
                        items: ['Member (Dev)', 'Manager']
                            .map((r) =>
                                DropdownMenuItem(value: r, child: Text(r)))
                            .toList(),
                        onChanged: (val) =>
                            setState(() => _selectedRole = val ?? 'Member (Dev)'),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Container(
                height: 38,
                alignment: Alignment.centerLeft,
                child: Row(
                  children: [
                    SizedBox(
                      width: 20,
                      height: 20,
                      child: Checkbox(
                        value: _termsAgreed,
                        activeColor: widget.palette.accent,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(4),
                        ),
                        onChanged: (val) =>
                            setState(() => _termsAgreed = val ?? false),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: GestureDetector(
                        onTap: () =>
                            setState(() => _termsAgreed = !_termsAgreed),
                        child: Text(
                          'I agree to terms of service',
                          style: UnoTypography.body(
                            color: widget.palette.textSec,
                            fontSize: 12,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Submit Button (Sign Up)
        SizedBox(
          height: 40,
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
                    'Sign Up',
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

            return ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 220),
              child: SingleChildScrollView(
                child: Column(
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
                ),
              ),
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

  void _showServerSwitchDialog() {
    final controller = TextEditingController(text: ApiService.baseUrl);
    ServerDiscoveryResult? dialogResult = _discoveryResult ?? ApiService.lastDiscoveryResult;
    bool isScanningDialog = false;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: widget.palette.bgSurface,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: widget.palette.div),
              ),
              title: Text(
                'Connect to Server',
                style: UnoTypography.brandSerif(palette: widget.palette, fontSize: 18),
              ),
              content: SizedBox(
                width: 460,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Enter the Control Plane address (Port 28000):',
                      style: UnoTypography.body(color: widget.palette.textSec, fontSize: 13),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: controller,
                      style: UnoTypography.mono(color: widget.palette.text, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: 'http://127.0.0.1:28000',
                        hintStyle: UnoTypography.mono(color: widget.palette.textSec, fontSize: 13),
                        filled: true,
                        fillColor: widget.palette.bgBase,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: BorderSide(color: widget.palette.div),
                        ),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ActionChip(
                          avatar: isScanningDialog
                              ? SizedBox(
                                  width: 12,
                                  height: 12,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    valueColor: AlwaysStoppedAnimation<Color>(widget.palette.accent),
                                  ),
                                )
                              : const Icon(Icons.autorenew, size: 14),
                          label: Text(
                            isScanningDialog ? 'Scanning Subnet...' : 'Auto-Detect',
                            style: UnoTypography.mono(color: widget.palette.text, fontSize: 11),
                          ),
                          backgroundColor: widget.palette.bgBase,
                          onPressed: isScanningDialog
                              ? null
                              : () async {
                                  setDialogState(() {
                                    isScanningDialog = true;
                                  });
                                  final result = await ApiService.autoDetectWithResult(forceRescan: true);
                                  if (context.mounted) {
                                    setDialogState(() {
                                      isScanningDialog = false;
                                      dialogResult = result;
                                      if (result.isSuccess && result.serverUrl != null) {
                                        controller.text = result.serverUrl!;
                                      }
                                    });
                                  }
                                  _checkServer();
                                  if (mounted) {
                                    setState(() {
                                      _discoveryResult = result;
                                      _isServerConnected = ApiService.isConnected;
                                    });
                                  }
                                },
                        ),
                        ActionChip(
                          label: Text('Localhost (28000)', style: UnoTypography.mono(color: widget.palette.text, fontSize: 11)),
                          backgroundColor: widget.palette.bgBase,
                          onPressed: () {
                            controller.text = 'http://127.0.0.1:28000';
                          },
                        ),
                        ActionChip(
                          label: Text('This PC LAN (10.0.0.35)', style: UnoTypography.mono(color: widget.palette.text, fontSize: 11)),
                          backgroundColor: widget.palette.bgBase,
                          onPressed: () {
                            controller.text = 'http://10.0.0.35:28000';
                          },
                        ),
                        ActionChip(
                          label: Text('Linux (10.0.0.59)', style: UnoTypography.mono(color: widget.palette.text, fontSize: 11)),
                          backgroundColor: widget.palette.bgBase,
                          onPressed: () {
                            controller.text = 'http://10.0.0.59:28000';
                          },
                        ),
                      ],
                    ),

                    if (isScanningDialog) ...[
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        decoration: BoxDecoration(
                          color: widget.palette.bgBase,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: widget.palette.div),
                        ),
                        child: Row(
                          children: [
                            SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(widget.palette.accent),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Probing local endpoints & scanning subnet .1 to .254...',
                                style: UnoTypography.body(color: widget.palette.textSec, fontSize: 11),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ] else if (dialogResult != null) ...[
                      const SizedBox(height: 14),
                      if (dialogResult!.isSuccess)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                          decoration: BoxDecoration(
                            color: const Color(0xFF6EC8B8).withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFF6EC8B8).withValues(alpha: 0.4)),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.check_circle, size: 14, color: Color(0xFF6EC8B8)),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Server discovered: ${dialogResult!.serverUrl}',
                                  style: UnoTypography.mono(color: const Color(0xFF6EC8B8), fontSize: 11),
                                ),
                              ),
                            ],
                          ),
                        )
                      else
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: const Color(0xFFD4725A).withValues(alpha: 0.09),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFFD4725A).withValues(alpha: 0.35)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  const Icon(LucideIcons.alertTriangle, size: 13, color: Color(0xFFD4725A)),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      'No servers available on local network',
                                      style: UnoTypography.body(
                                        color: const Color(0xFFE89885),
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    '0/254 alive',
                                    style: UnoTypography.mono(color: const Color(0xFFE89885), fontSize: 10),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Scanned ${dialogResult!.scannedSubnet ?? "subnet"} on port 28000: 0 responsive servers.',
                                style: UnoTypography.body(color: widget.palette.textSec, fontSize: 11),
                              ),
                              const SizedBox(height: 6),
                              Container(
                                padding: const EdgeInsets.all(6),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF141412),
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: widget.palette.div),
                                ),
                                constraints: const BoxConstraints(maxHeight: 75),
                                child: SingleChildScrollView(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: dialogResult!.logs.map((l) => Text(
                                      l,
                                      style: UnoTypography.mono(
                                        color: l.contains('[ERROR]')
                                            ? const Color(0xFFE89885)
                                            : widget.palette.textSec.withValues(alpha: 0.85),
                                        fontSize: 9.5,
                                      ),
                                    )).toList(),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: Text('Cancel', style: UnoTypography.body(color: widget.palette.textSec, fontSize: 13)),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: widget.palette.accent,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () {
                    final target = controller.text.trim();
                    if (target.isNotEmpty) {
                      ApiService.setBaseUrl(target);
                      _checkServer();
                    }
                    Navigator.of(ctx).pop();
                    setState(() {});
                  },
                  child: const Text('Connect'),
                ),
              ],
            );
          },
        );
      },
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
        const SizedBox(height: 14),
        InkWell(
          onTap: _showServerSwitchDialog,
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
