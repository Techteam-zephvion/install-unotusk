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
  // Navigation states matching user workflow:
  // 'entry' (Image 2) -> 'checking-org' (Image 4) -> 'sign-in' (Image 5)
  // 'entry' -> 'create-org' (Image 3 via Configure custom OIDC issuer)
  String _state = 'entry';
  bool _isServerConnected = false;
  Timer? _healthTimer;

  final TextEditingController _emailController =
      TextEditingController(text: 'lead@acme.com');
  final TextEditingController _passwordController =
      TextEditingController(text: 'adminpassword123');
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _orgController = TextEditingController();

  bool _obscurePassword = true;
  String _selectedRole = 'Engineer';
  bool _termsAgreed = false;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _checkServer();
    // Continuously check server health every 4 seconds
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

  void _verifyEmail() async {
    String email = _emailController.text.trim();
    if (email.isEmpty) {
      email = 'dev1@acme.com';
      _emailController.text = email;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _state = 'checking-org';
    });

    try {
      await ApiService.checkOrganisationMembership(email);
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _state = 'sign-in';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage =
            'Cannot reach backend at http://10.0.0.59:28000.\nPlease verify the server is running and port 28000 is open.';
        _state = 'entry';
      });
    }
  }

  void _finishAuthentication() async {
    final email = _emailController.text.trim().isNotEmpty
        ? _emailController.text.trim()
        : 'lead@acme.com';
    final password = _passwordController.text;

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
        _errorMessage =
            'Sign in failed on http://10.0.0.59:28000:\n$e';
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
                fontSize: 12,
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
          // ── Custom Window Title Bar with OIDC badge ──
          WindowTitleBar(
            palette: widget.palette,
            trailing: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: widget.palette.accent.withValues(alpha: 0.125),
                border: Border.all(
                  color: widget.palette.accent.withValues(alpha: 0.25),
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                'OIDC 1.0 SSO',
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
                  constraints: BoxConstraints(
                    maxWidth: _state == 'checking-org' ? 380 : 420,
                  ),
                  padding: EdgeInsets.symmetric(
                    horizontal: _state == 'checking-org'
                        ? 28
                        : (MediaQuery.of(context).size.width < 450 ? 20 : 32),
                    vertical: _state == 'checking-org' ? 32 : 32,
                  ),
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
                  child: _buildStateContent(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStateContent() {
    switch (_state) {
      case 'checking-org':
        return _buildCheckingOrg();
      case 'sign-in':
        return _buildSignIn();
      case 'create-org':
        return _buildCreateOrg();
      case 'entry':
      default:
        return _buildEntry();
    }
  }

  // ─────────────────────────────────────────────────
  //  Badge (OIDC Authentication)
  // ─────────────────────────────────────────────────
  Widget _buildBadge() {
    return Align(
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
            Icon(LucideIcons.shield, size: 12, color: widget.palette.accent),
            const SizedBox(width: 6),
            Text(
              'OIDC Authentication',
              style: UnoTypography.mono(
                color: widget.palette.text,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────
  //  Footer (Server URL status)
  // ─────────────────────────────────────────────────
  Widget _buildServerFooter() {
    final isOnline = _isServerConnected || ApiService.isConnected;
    final dotColor = isOnline
        ? const Color(0xFF6EC8B8) // Green / mint teal when server is on
        : const Color(0xFFE05A5A); // Red when server is not on

    return Column(
      children: [
        const SizedBox(height: 24),
        InkWell(
          onTap: _checkServer,
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
                    'Server: http://10.0.0.59:28000',
                    overflow: TextOverflow.ellipsis,
                    style: UnoTypography.mono(
                      color: widget.palette.textSec,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────
  //  Screen 1: Entry Screen (matches Image 2)
  // ─────────────────────────────────────────────────
  Widget _buildEntry() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildBadge(),
        const SizedBox(height: 14),

        Text(
          'Sign in to Unotusk',
          style: UnoTypography.brandSerif(
            palette: widget.palette,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 8),

        Text(
          'Authenticating via OpenID Connect (OIDC) identity provider for single sign-on security.',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 20),
        _buildErrorBanner(),

        Text(
          'Work Email Address',
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
              hintText: 'you@company.com',
              hintStyle: UnoTypography.body(
                color: widget.palette.textSec.withValues(alpha: 0.6),
                fontSize: 13,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 11),
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) => _verifyEmail(),
          ),
        ),
        const SizedBox(height: 12),

        SizedBox(
          height: 40,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _verifyEmail,
            style: ElevatedButton.styleFrom(
              backgroundColor: widget.palette.accent,
              foregroundColor: Colors.white,
              elevation: 0,
              padding: EdgeInsets.zero,
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
                      valueColor:
                          AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : Text(
                    'Continue with OIDC Discovery',
                    style: UnoTypography.body(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ),

        const SizedBox(height: 8),

        // Role Demo Quick Fills (Manager vs Employee RBAC testing)
        Row(
          children: [
            Expanded(
              child: InkWell(
                onTap: () {
                  _emailController.text = 'lead@acme.com';
                  _passwordController.text = 'demo1234';
                  _verifyEmail();
                },
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 8),
                  decoration: BoxDecoration(
                    color: widget.palette.accent.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: widget.palette.accent.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.shield_outlined, size: 13, color: widget.palette.accent),
                      const SizedBox(width: 5),
                      Flexible(
                        child: Text(
                          'Manager (lead@acme.com)',
                          overflow: TextOverflow.ellipsis,
                          style: UnoTypography.body(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: widget.palette.accent,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: InkWell(
                onTap: () {
                  _emailController.text = 'dev1@acme.com';
                  _passwordController.text = 'demo1234';
                  _verifyEmail();
                },
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 7, horizontal: 8),
                  decoration: BoxDecoration(
                    color: widget.palette.bgElevated,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: widget.palette.div),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.badge_outlined, size: 13, color: widget.palette.textSec),
                      const SizedBox(width: 5),
                      Flexible(
                        child: Text(
                          'Employee (dev1@acme.com)',
                          overflow: TextOverflow.ellipsis,
                          style: UnoTypography.body(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color: widget.palette.textSec,
                          ),
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

        Wrap(
          alignment: WrapAlignment.center,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              "Need a workspace? ",
              style: UnoTypography.body(fontSize: 11, color: widget.palette.textSec),
            ),
            InkWell(
              onTap: () => setState(() => _state = 'register'),
              child: Text(
                'Create Workspace',
                style: UnoTypography.body(
                  fontSize: 11,
                  color: widget.palette.accent,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: Container(height: 1, color: widget.palette.div)),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Text(
                'or sign in via OIDC provider',
                style: UnoTypography.mono(
                  color: widget.palette.textSec.withValues(alpha: 0.7),
                  fontSize: 10.5,
                ),
              ),
            ),
            Expanded(child: Container(height: 1, color: widget.palette.div)),
          ],
        ),
        const SizedBox(height: 16),

        // 1. Google OIDC (Image 2 style)
        _buildProviderButton(
          icon: Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(
              border: Border.all(color: widget.palette.textSec, width: 1.2),
              borderRadius: BorderRadius.circular(2.5),
            ),
            alignment: Alignment.center,
            child: Text(
              'G',
              style: TextStyle(
                color: widget.palette.textSec,
                fontSize: 8.5,
                fontWeight: FontWeight.bold,
                height: 1,
              ),
            ),
          ),
          label: 'Sign in with Google OIDC',
          onTap: () {
            _emailController.text = 'dev1@acme.com';
            _verifyEmail();
          },
        ),
        const SizedBox(height: 9),

        // 2. Microsoft Entra OIDC (Image 2 style)
        _buildProviderButton(
          icon: Icon(
            LucideIcons.layoutGrid,
            size: 15,
            color: widget.palette.textSec,
          ),
          label: 'Sign in with Microsoft Entra OIDC',
          onTap: () {
            _emailController.text = 'lead@acme.com';
            _verifyEmail();
          },
        ),
        const SizedBox(height: 9),

        // 3. Configure custom OIDC issuer (matches Image 2, opens Image 3)
        _buildProviderButton(
          icon: Icon(
            LucideIcons.arrowLeftRight,
            size: 15,
            color: widget.palette.textSec,
          ),
          label: 'Configure custom OIDC issuer',
          onTap: () {
            setState(() => _state = 'create-org');
          },
        ),

        _buildServerFooter(),
      ],
    );
  }

  // ─────────────────────────────────────────────────
  //  Screen 2: Create your organisation (matches Image 3)
  // ─────────────────────────────────────────────────
  Widget _buildCreateOrg() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Create your organisation',
          style: UnoTypography.brandSerif(
            palette: widget.palette,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'No organisation found for . Set up your workspace.',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 20),

        // Full name
        Text(
          'Full name',
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
        const SizedBox(height: 14),

        // Organisation name
        Text(
          'Organisation name',
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
        const SizedBox(height: 14),

        // Password
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
        const SizedBox(height: 14),

        // Role
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
              items: ['Engineer', 'Tech Lead', 'Manager', 'Developer', 'QA']
                  .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                  .toList(),
              onChanged: (val) =>
                  setState(() => _selectedRole = val ?? 'Engineer'),
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Terms of service checkbox
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

        // Create workspace button
        SizedBox(
          height: 42,
          child: ElevatedButton(
            onPressed: _isLoading
                ? null
                : () async {
                    final name = _nameController.text.trim().isNotEmpty
                        ? _nameController.text.trim()
                        : 'Alex Morgan';
                    final org = _orgController.text.trim().isNotEmpty
                        ? _orgController.text.trim()
                        : 'Acme Corporation';
                    final password = _passwordController.text;

                    setState(() {
                      _isLoading = true;
                      _errorMessage = null;
                    });

                    try {
                      final user = await ApiService.createOrganisation(
                        fullName: name,
                        orgName: org,
                        password: password,
                        role: _selectedRole,
                        email: _emailController.text.trim().isNotEmpty
                            ? _emailController.text.trim()
                            : null,
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
                        _errorMessage =
                            'Failed to create workspace on http://10.0.0.59:28000:\n$e';
                      });
                    }
                  },
            style: ElevatedButton.styleFrom(
              backgroundColor: widget.palette.accent,
              foregroundColor: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(9),
              ),
            ),
            child: Text(
              'Create workspace',
              style: UnoTypography.body(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),

        // Back button
        TextButton(
          onPressed: () => setState(() => _state = 'entry'),
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

  // ─────────────────────────────────────────────────
  //  Screen 3: Checking membership (matches Image 4)
  // ─────────────────────────────────────────────────
  Widget _buildCheckingOrg() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: const BoxDecoration(
            color: Color(0xFF6EC8B8),
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Checking organisation membership...',
          style: UnoTypography.body(
            color: widget.palette.text,
            fontSize: 13.5,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          _emailController.text.isNotEmpty
              ? _emailController.text
              : 'dev1@acme.com',
          style: UnoTypography.mono(
            color: const Color(0xFFD4725A),
            fontSize: 12.5,
          ),
        ),
      ],
    );
  }

  // ─────────────────────────────────────────────────
  //  Screen 4: Password Sign In (matches Image 5)
  // ─────────────────────────────────────────────────
  Widget _buildSignIn() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildBadge(),
        const SizedBox(height: 14),

        Text(
          'Sign in to Unotusk',
          style: UnoTypography.brandSerif(
            palette: widget.palette,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 8),

        Text(
          'Authenticating via OpenID Connect (OIDC) identity provider for single sign-on security.',
          style: UnoTypography.body(
            color: widget.palette.textSec,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 20),
        _buildErrorBanner(),

        // Work Email Address (Pre-filled)
        Text(
          'Work Email Address',
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
            decoration: const InputDecoration(
              border: InputBorder.none,
              contentPadding: EdgeInsets.symmetric(vertical: 11),
            ),
          ),
        ),
        const SizedBox(height: 16),

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
                    color: widget.palette.text,
                    fontSize: 13,
                  ),
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(vertical: 11),
                  ),
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

        // Sign in Button
        SizedBox(
          height: 42,
          child: ElevatedButton(
            onPressed: _isLoading ? null : () => _finishAuthentication(),
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
                    'Sign in',
                    style: UnoTypography.body(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ),

        _buildServerFooter(),
      ],
    );
  }

  // ─────────────────────────────────────────────────
  //  Provider Button Helper
  // ─────────────────────────────────────────────────
  Widget _buildProviderButton({
    required Widget icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return SizedBox(
      height: 40,
      child: Material(
        color: widget.palette.bgElevated,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(9),
          side: BorderSide(color: widget.palette.div),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(9),
          child: Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                icon,
                const SizedBox(width: 9),
                Flexible(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: UnoTypography.body(
                      color: widget.palette.text,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
