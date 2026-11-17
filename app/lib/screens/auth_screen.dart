import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/server_discovery_service.dart';
import '../theme/app_theme.dart';
import '../widgets/unotusk_logo.dart';
import '../widgets/window_title_bar.dart';

// ─────────────────────────────────────────────────────────────
//  Exact Palette Sampled Directly from Reference Image
// ─────────────────────────────────────────────────────────────
class _AuthColors {
  static const Color obsidianNavy = Color(0xFF0A0F20);   // Dominant dark: rgb(10, 15, 32)
  static const Color warmSand = Color(0xFFCBC1B4);       // Elephant logo / cream: rgb(203, 193, 180)
  static const Color slateNavy = Color(0xFF161A29);      // Elevated dark surface: rgb(22, 26, 41)
  static const Color darkBorder = Color(0xFF222533);     // Dark divider / border: rgb(34, 37, 51)
  static const Color darkBorderHover = Color(0xFF2E313C);// Subtle dark stroke: rgb(46, 49, 60)
  static const Color coolSlate = Color(0xFF84878F);      // Secondary / muted slate: rgb(132, 135, 143)
  static const Color mutedDark = Color(0xFF6B686A);      // Dark slate text / icon: rgb(107, 104, 106)
  static const Color pureWhite = Color(0xFFFFFFFF);      // Pure white: rgb(255, 255, 255)
  static const Color sandTint = Color(0xFFC0B7AB);       // Warm sand tint: rgb(192, 183, 171)
  static const Color sandLight = Color(0xFFF7F5F1);      // Soft cream light surface
  static const Color sandCream = Color(0xFFF5F2EB);      // Light oyster cream card surface
  static const Color sandCreamBorder = Color(0xFFE4DFD6);// Light card inner border
  static const Color sandBg = Color(0xFFF2EFE9);         // Soft light background
}

class AuthScreen extends StatefulWidget {
  final UnoPalette palette;
  final Function(UserModel user) onAuthenticated;
  final String? sessionMsg;
  final bool? isDark;
  final VoidCallback? onToggleTheme;

  const AuthScreen({
    super.key,
    required this.palette,
    required this.onAuthenticated,
    this.sessionMsg,
    this.isDark,
    this.onToggleTheme,
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
  late bool _localIsDark;

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
    _localIsDark = widget.isDark ?? widget.palette.isDark;

    if (!kIsWeb && Platform.environment.containsKey('FLUTTER_TEST')) {
      _isServerConnected = true;
    } else {
      _initServer();
      _healthTimer =
          Timer.periodic(const Duration(seconds: 4), (_) => _checkServer());
    }
  }

  @override
  void didUpdateWidget(covariant AuthScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isDark != null && widget.isDark != oldWidget.isDark) {
      _localIsDark = widget.isDark!;
    } else if (widget.palette.isDark != oldWidget.palette.isDark) {
      _localIsDark = widget.palette.isDark;
    }
  }

  void _toggleTheme() {
    setState(() {
      _localIsDark = !_localIsDark;
    });
    if (widget.onToggleTheme != null) {
      widget.onToggleTheme!();
    }
  }

  UnoPalette _getEffectivePalette(bool isDark) {
    return isDark
        ? const UnoPalette(
            bgBase: _AuthColors.obsidianNavy,
            bgSurface: _AuthColors.sandCream,
            bgElevated: _AuthColors.sandCreamBorder,
            div: _AuthColors.sandTint,
            accent: _AuthColors.obsidianNavy,
            output: _AuthColors.obsidianNavy,
            live: Color(0xFF22C55E),
            confirmed: _AuthColors.obsidianNavy,
            inferred: _AuthColors.obsidianNavy,
            neutral: _AuthColors.mutedDark,
            text: _AuthColors.obsidianNavy,
            textSec: _AuthColors.mutedDark,
          )
        : const UnoPalette(
            bgBase: _AuthColors.sandBg,
            bgSurface: _AuthColors.obsidianNavy,
            bgElevated: _AuthColors.slateNavy,
            div: _AuthColors.darkBorderHover,
            accent: _AuthColors.warmSand,
            output: _AuthColors.warmSand,
            live: Color(0xFF22C55E),
            confirmed: _AuthColors.warmSand,
            inferred: _AuthColors.warmSand,
            neutral: _AuthColors.coolSlate,
            text: _AuthColors.pureWhite,
            textSec: _AuthColors.coolSlate,
          );
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

  Widget _buildErrorBanner(bool isCardLight) {
    if (_errorMessage == null) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isCardLight
            ? const Color(0xFFFEE2E2)
            : const Color(0xFFD4725A).withValues(alpha: 0.14),
        border: Border.all(
          color: isCardLight
              ? const Color(0xFFFCA5A5)
              : const Color(0xFFD4725A).withValues(alpha: 0.5),
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            LucideIcons.alertTriangle,
            size: 16,
            color: isCardLight ? const Color(0xFFDC2626) : const Color(0xFFD4725A),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _errorMessage!,
              style: UnoTypography.body(
                color: isCardLight ? const Color(0xFF991B1B) : const Color(0xFFE89885),
                fontSize: 12.5,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildServerDiscoveryStatusCard(bool isCardLight, UnoPalette palette) {
    if (_isScanning) {
      return Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isCardLight ? _AuthColors.sandCreamBorder : _AuthColors.slateNavy,
          border: Border.all(color: palette.div),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(
                  isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'Searching network for active Unotusk server...',
                style: UnoTypography.body(
                  color: palette.textSec,
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

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFD4725A).withValues(alpha: isCardLight ? 0.08 : 0.12),
        border: Border.all(
          color: const Color(0xFFD4725A).withValues(alpha: isCardLight ? 0.35 : 0.40),
        ),
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
                    color: isCardLight ? const Color(0xFFB94A32) : const Color(0xFFE89885),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'No running Unotusk Control Plane was found on the local network. Make sure your server is running or configure the server address manually.',
            style: UnoTypography.body(
              color: palette.textSec,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 10),
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
                      color: palette.textSec,
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
                    color: isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: palette.div),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        LucideIcons.refreshCw,
                        size: 11,
                        color: palette.text,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Re-scan Subnet',
                        style: UnoTypography.body(
                          color: palette.text,
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
    final isDark = _localIsDark;
    // Opposite Shade Rule:
    // When screen is dark (isDark == true), middle card is LIGHT (_isCardLight == true).
    // When screen is light (isDark == false), middle card is DARK (_isCardLight == false).
    final isCardLight = isDark;
    final palette = _getEffectivePalette(isDark);

    return Scaffold(
      backgroundColor: isDark ? _AuthColors.obsidianNavy : _AuthColors.sandBg,
      body: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutCubic,
        color: isDark ? _AuthColors.obsidianNavy : _AuthColors.sandBg,
        child: Column(
          children: [
            // ── Window Title Bar ──
            WindowTitleBar(
              palette: isDark
                  ? const UnoPalette(
                      bgBase: _AuthColors.obsidianNavy,
                      bgSurface: _AuthColors.slateNavy,
                      bgElevated: _AuthColors.obsidianNavy,
                      div: _AuthColors.darkBorderHover,
                      accent: _AuthColors.warmSand,
                      output: _AuthColors.warmSand,
                      live: Color(0xFF22C55E),
                      confirmed: _AuthColors.warmSand,
                      inferred: _AuthColors.warmSand,
                      neutral: _AuthColors.coolSlate,
                      text: _AuthColors.pureWhite,
                      textSec: _AuthColors.coolSlate,
                    )
                  : const UnoPalette(
                      bgBase: _AuthColors.sandBg,
                      bgSurface: _AuthColors.pureWhite,
                      bgElevated: _AuthColors.sandLight,
                      div: _AuthColors.sandTint,
                      accent: _AuthColors.obsidianNavy,
                      output: _AuthColors.obsidianNavy,
                      live: Color(0xFF22C55E),
                      confirmed: _AuthColors.obsidianNavy,
                      inferred: _AuthColors.obsidianNavy,
                      neutral: _AuthColors.coolSlate,
                      text: _AuthColors.obsidianNavy,
                      textSec: _AuthColors.mutedDark,
                    ),
            ),

            // ── Center Card (Opposite shade from the outer screen) ──
            Expanded(
              child: Center(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.center,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 220),
                    curve: Curves.easeOutCubic,
                    constraints: BoxConstraints(
                      maxWidth: _activeMode == 1 ? 580 : (_activeMode == 2 ? 460 : 440),
                    ),
                    margin: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                    padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
                    decoration: BoxDecoration(
                      color: isCardLight ? _AuthColors.sandCream : _AuthColors.obsidianNavy,
                      border: Border.all(
                        color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover,
                        width: 1.5,
                      ),
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(
                          color: isDark
                              ? Colors.black.withValues(alpha: 0.65)
                              : _AuthColors.obsidianNavy.withValues(alpha: 0.12),
                          blurRadius: isDark ? 48 : 36,
                          offset: const Offset(0, 16),
                        ),
                        if (!isCardLight)
                          BoxShadow(
                            color: _AuthColors.warmSand.withValues(alpha: 0.05),
                            blurRadius: 1,
                            offset: const Offset(0, 1),
                          ),
                      ],
                    ),
                    child: _activeMode == 2
                        ? _buildServerList(isCardLight, palette)
                        : _buildAuthCard(isCardLight, palette),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThemeToggleBtn(bool isCardLight) {
    final isDark = _localIsDark;
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: Tooltip(
        message: isDark ? 'Switch to light mode' : 'Switch to dark mode',
        preferBelow: false,
        verticalOffset: 16,
        child: GestureDetector(
          onTap: _toggleTheme,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
            decoration: BoxDecoration(
              color: isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy,
              border: Border.all(
                color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover,
                width: 1.0,
              ),
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: isCardLight
                      ? _AuthColors.obsidianNavy.withValues(alpha: 0.06)
                      : Colors.black.withValues(alpha: 0.3),
                  blurRadius: 4,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                AnimatedRotation(
                  turns: isDark ? 0.0 : 0.5,
                  duration: const Duration(milliseconds: 220),
                  curve: Curves.easeOutCubic,
                  child: Icon(
                    isDark ? LucideIcons.moon : LucideIcons.sun,
                    size: 13,
                    color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  isDark ? 'Dark' : 'Light',
                  style: GoogleFonts.inter(
                    color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAuthCard(bool isCardLight, UnoPalette palette) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        // ── Brand Header inside Card ──
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                UnotuskLogo(size: 26, onDark: !isCardLight),
                const SizedBox(width: 9),
                Text(
                  'Unotusk',
                  style: GoogleFonts.youngSerif(
                    color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
            _buildThemeToggleBtn(isCardLight),
          ],
        ),
        const SizedBox(height: 18),

        // ── Heading & Subtitle ──
        Text(
          _activeMode == 0 ? 'Sign in to Unotusk' : 'Sign up to Unotusk',
          style: GoogleFonts.youngSerif(
            color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 5),
        Text(
          _activeMode == 0
              ? 'Enter your work email and password to access your workspace.'
              : 'Register a new project intelligence workspace.',
          style: GoogleFonts.inter(
            color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
            fontSize: 13,
            height: 1.4,
          ),
        ),
        const SizedBox(height: 18),

        // ── Segmented Mode Switcher (Sign In vs Sign Up) ──
        AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          height: 40,
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            color: isCardLight ? _AuthColors.sandCreamBorder : _AuthColors.slateNavy,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorder,
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: _buildTabButton(
                  'Sign In',
                  _activeMode == 0,
                  isCardLight,
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
                  isCardLight,
                  () => setState(() {
                    _activeMode = 1;
                    _errorMessage = null;
                  }),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),

        _buildErrorBanner(isCardLight),

        _buildServerDiscoveryStatusCard(isCardLight, palette),

        // ── Mode-specific form ──
        if (_activeMode == 0)
          _buildSignInForm(isCardLight, palette)
        else
          _buildCreateWorkspaceForm(isCardLight, palette),

        _buildServerFooter(isCardLight, palette),
      ],
    );
  }

  Widget _buildTabButton(
    String label,
    bool isSelected,
    bool isCardLight,
    VoidCallback onTap,
  ) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: isSelected
                ? (isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: isCardLight
                          ? _AuthColors.obsidianNavy.withValues(alpha: 0.25)
                          : Colors.black.withValues(alpha: 0.25),
                      blurRadius: 4,
                      offset: const Offset(0, 1),
                    ),
                  ]
                : null,
          ),
          child: Text(
            label,
            style: GoogleFonts.inter(
              color: isSelected
                  ? (isCardLight ? _AuthColors.pureWhite : _AuthColors.obsidianNavy)
                  : (isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate),
              fontSize: 13,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────
  //  Reusable Perfectly Centered Text Input Box
  // ─────────────────────────────────────────────────────────────
  Widget _buildCenteredInputBox({
    required TextEditingController controller,
    required String hintText,
    required bool isCardLight,
    bool obscureText = false,
    Widget? suffix,
    VoidCallback? onSubmitted,
  }) {
    final bgColor = isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy;
    final borderColor = isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover;
    final textColor = isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite;
    final hintColor = isCardLight
        ? _AuthColors.mutedDark.withValues(alpha: 0.7)
        : _AuthColors.coolSlate.withValues(alpha: 0.7);

    return Container(
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: bgColor,
        border: Border.all(color: borderColor, width: 1.2),
        borderRadius: BorderRadius.circular(10),
        boxShadow: [
          BoxShadow(
            color: isCardLight
                ? _AuthColors.obsidianNavy.withValues(alpha: 0.04)
                : Colors.black.withValues(alpha: 0.2),
            blurRadius: 4,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              obscureText: obscureText,
              textAlignVertical: TextAlignVertical.center,
              style: GoogleFonts.inter(
                fontSize: 13.5,
                fontWeight: FontWeight.w500,
                color: textColor,
              ),
              decoration: InputDecoration(
                isDense: true,
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
                hintText: hintText,
                hintStyle: GoogleFonts.inter(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w400,
                  color: hintColor,
                ),
              ),
              onSubmitted: onSubmitted != null ? (_) => onSubmitted() : null,
            ),
          ),
          ?suffix,
        ],
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────
  //  Sign In Form
  // ─────────────────────────────────────────────────────────────
  Widget _buildSignInForm(bool isCardLight, UnoPalette palette) {
    final labelColor = isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand;
    // Button Rule:
    // "sign up sign in button to dark when light and light when dark"
    // When card is Light -> button is DARK (_AuthColors.obsidianNavy).
    // When card is Dark -> button is LIGHT (_AuthColors.warmSand).
    final btnBg = isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand;
    final btnFg = isCardLight ? _AuthColors.pureWhite : _AuthColors.obsidianNavy;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Work Email Label
        Text(
          'Work Email',
          style: GoogleFonts.inter(
            color: labelColor,
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.2,
          ),
        ),
        const SizedBox(height: 6),
        _buildCenteredInputBox(
          controller: _emailController,
          hintText: 'alex@acme.com',
          isCardLight: isCardLight,
          onSubmitted: _handleSignIn,
        ),
        const SizedBox(height: 14),

        // Password Label with eye toggle
        Text(
          'Password',
          style: GoogleFonts.inter(
            color: labelColor,
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.2,
          ),
        ),
        const SizedBox(height: 6),
        _buildCenteredInputBox(
          controller: _passwordController,
          hintText: '••••••••',
          isCardLight: isCardLight,
          obscureText: _obscurePassword,
          onSubmitted: _handleSignIn,
          suffix: MouseRegion(
            cursor: SystemMouseCursors.click,
            child: GestureDetector(
              onTap: () => setState(() => _obscurePassword = !_obscurePassword),
              child: Padding(
                padding: const EdgeInsets.only(left: 8),
                child: Icon(
                  _obscurePassword ? LucideIcons.eye : LucideIcons.eyeOff,
                  size: 16.5,
                  color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 20),

        // Submit Button (ElevatedButton)
        SizedBox(
          height: 44,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _handleSignIn,
            style: ElevatedButton.styleFrom(
              backgroundColor: btnBg,
              foregroundColor: btnFg,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              shadowColor: btnBg.withValues(alpha: 0.3),
            ),
            child: _isLoading
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(btnFg),
                    ),
                  )
                : Text(
                    'Sign In',
                    style: GoogleFonts.inter(
                      color: btnFg,
                      fontSize: 14.5,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.1,
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
  Widget _buildCreateWorkspaceForm(bool isCardLight, UnoPalette palette) {
    final labelColor = isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand;
    final btnBg = isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand;
    final btnFg = isCardLight ? _AuthColors.pureWhite : _AuthColors.obsidianNavy;

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
                    style: GoogleFonts.inter(
                      color: labelColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 5),
                  _buildCenteredInputBox(
                    controller: _nameController,
                    hintText: 'Alex Morgan',
                    isCardLight: isCardLight,
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
                    style: GoogleFonts.inter(
                      color: labelColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 5),
                  _buildCenteredInputBox(
                    controller: _orgController,
                    hintText: 'Your organization',
                    isCardLight: isCardLight,
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

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
                    style: GoogleFonts.inter(
                      color: labelColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 5),
                  _buildCenteredInputBox(
                    controller: _emailController,
                    hintText: 'alex@acme.com',
                    isCardLight: isCardLight,
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
                    style: GoogleFonts.inter(
                      color: labelColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 5),
                  _buildCenteredInputBox(
                    controller: _passwordController,
                    hintText: '••••••••',
                    isCardLight: isCardLight,
                    obscureText: _obscurePassword,
                    suffix: MouseRegion(
                      cursor: SystemMouseCursors.click,
                      child: GestureDetector(
                        onTap: () => setState(
                            () => _obscurePassword = !_obscurePassword),
                        child: Padding(
                          padding: const EdgeInsets.only(left: 8),
                          child: Icon(
                            _obscurePassword
                                ? LucideIcons.eye
                                : LucideIcons.eyeOff,
                            size: 16.5,
                            color: isCardLight
                                ? _AuthColors.mutedDark
                                : _AuthColors.coolSlate,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

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
                    style: GoogleFonts.inter(
                      color: labelColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Container(
                    height: 44,
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy,
                      border: Border.all(
                        color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover,
                        width: 1.2,
                      ),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: _selectedRole,
                        dropdownColor: isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy,
                        icon: Icon(
                          Icons.arrow_drop_down,
                          color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                        ),
                        isExpanded: true,
                        style: GoogleFonts.inter(
                          color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
                          fontSize: 13,
                        ),
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
                height: 44,
                alignment: Alignment.centerLeft,
                child: Row(
                  children: [
                    SizedBox(
                      width: 20,
                      height: 20,
                      child: Checkbox(
                        value: _termsAgreed,
                        activeColor: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                        checkColor: isCardLight ? _AuthColors.pureWhite : _AuthColors.obsidianNavy,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(4),
                        ),
                        side: BorderSide(
                          color: isCardLight ? _AuthColors.sandTint : _AuthColors.coolSlate,
                        ),
                        onChanged: (val) =>
                            setState(() => _termsAgreed = val ?? false),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: MouseRegion(
                        cursor: SystemMouseCursors.click,
                        child: GestureDetector(
                          onTap: () =>
                              setState(() => _termsAgreed = !_termsAgreed),
                          child: Text(
                            'I agree to terms of service',
                            style: GoogleFonts.inter(
                              color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                              fontSize: 12,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),

        // Submit Button (Sign Up)
        SizedBox(
          height: 44,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _handleCreateWorkspace,
            style: ElevatedButton.styleFrom(
              backgroundColor: btnBg,
              foregroundColor: btnFg,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              shadowColor: btnBg.withValues(alpha: 0.3),
            ),
            child: _isLoading
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(btnFg),
                    ),
                  )
                : Text(
                    'Sign Up',
                    style: GoogleFonts.inter(
                      color: btnFg,
                      fontSize: 14.5,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.1,
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
  Widget _buildServerList(bool isCardLight, UnoPalette palette) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Select project server',
          style: GoogleFonts.youngSerif(
            color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Choose a running workspace instance to connect to.',
          style: GoogleFonts.inter(
            color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 20),

        FutureBuilder<List<ProjectItem>>(
          future: ApiService.fetchProjects(),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return SizedBox(
                height: 100,
                child: Center(
                  child: SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                      ),
                    ),
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
                  style: GoogleFonts.inter(color: Colors.red.shade300, fontSize: 13),
                ),
              );
            }

            final servers = snapshot.data ?? [];
            if (servers.isEmpty) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(
                  'No running servers found.',
                  style: GoogleFonts.inter(
                    color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                    fontSize: 13,
                  ),
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
                      child: MouseRegion(
                        cursor: SystemMouseCursors.click,
                        child: InkWell(
                          onTap: () {
                            final uri = Uri.parse(ApiService.baseUrl);
                            ApiService.serverHost = '${uri.host}:$port';
                            ApiService.baseUrl = 'http://${ApiService.serverHost}';
                            setState(() => _activeMode = 0);
                          },
                          borderRadius: BorderRadius.circular(10),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            decoration: BoxDecoration(
                              color: isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy,
                              border: Border.all(
                                color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover,
                              ),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Row(
                              children: [
                                Icon(
                                  Icons.storage,
                                  color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                                  size: 18,
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        project.name,
                                        style: GoogleFonts.inter(
                                          color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
                                          fontSize: 14,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                      Text(
                                        'Port: $port',
                                        style: GoogleFonts.ibmPlexMono(
                                          color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Icon(
                                  Icons.chevron_right,
                                  color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                                  size: 20,
                                ),
                              ],
                            ),
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
            style: GoogleFonts.inter(
              color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  void _showServerSwitchDialog() {
    final isDark = _localIsDark;
    final isCardLight = isDark;
    final controller = TextEditingController(text: ApiService.baseUrl);
    ServerDiscoveryResult? dialogResult = _discoveryResult ?? ApiService.lastDiscoveryResult;
    bool isScanningDialog = false;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(
                  color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover,
                ),
              ),
              title: Text(
                'Connect to Server',
                style: GoogleFonts.youngSerif(
                  color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
                  fontSize: 19,
                ),
              ),
              content: SizedBox(
                width: 460,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Enter the Control Plane address (Port 28000):',
                      style: GoogleFonts.inter(
                        color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 12),
                    _buildCenteredInputBox(
                      controller: controller,
                      hintText: 'http://127.0.0.1:28000',
                      isCardLight: isCardLight,
                    ),
                    const SizedBox(height: 12),
                    Material(
                      color: Colors.transparent,
                      borderRadius: BorderRadius.circular(8),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(8),
                        onTap: isScanningDialog
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
                        child: Ink(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                          decoration: BoxDecoration(
                            color: isCardLight ? _AuthColors.sandCream : _AuthColors.obsidianNavy,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover,
                              width: 1.0,
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (isScanningDialog)
                                SizedBox(
                                  width: 13,
                                  height: 13,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    valueColor: AlwaysStoppedAnimation<Color>(
                                      isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                                    ),
                                  ),
                                )
                              else
                                Icon(
                                  LucideIcons.refreshCw,
                                  size: 13,
                                  color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                                ),
                              const SizedBox(width: 8),
                              Text(
                                isScanningDialog ? 'Scanning Subnet...' : 'Auto-Detect',
                                style: GoogleFonts.inter(
                                  color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),

                    if (isScanningDialog) ...[
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        decoration: BoxDecoration(
                          color: isCardLight ? _AuthColors.sandCreamBorder : _AuthColors.slateNavy,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover,
                          ),
                        ),
                        child: Row(
                          children: [
                            SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Probing local endpoints & scanning subnet .1 to .254...',
                                style: GoogleFonts.inter(
                                  color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                                  fontSize: 11,
                                ),
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
                                  style: GoogleFonts.ibmPlexMono(color: const Color(0xFF6EC8B8), fontSize: 11),
                                ),
                              ),
                            ],
                          ),
                        )
                      else
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          decoration: BoxDecoration(
                            color: const Color(0xFFD4725A).withValues(alpha: 0.09),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: const Color(0xFFD4725A).withValues(alpha: 0.35)),
                          ),
                          child: Row(
                            children: [
                              const Icon(LucideIcons.alertTriangle, size: 14, color: Color(0xFFD4725A)),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'No servers found on the local network. Make sure your server is running or enter the address manually.',
                                  style: GoogleFonts.inter(
                                    color: const Color(0xFFE89885),
                                    fontSize: 12,
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
                  child: Text(
                    'Cancel',
                    style: GoogleFonts.inter(
                      color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                      fontSize: 13,
                    ),
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand,
                    foregroundColor: isCardLight ? _AuthColors.pureWhite : _AuthColors.obsidianNavy,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
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
  Widget _buildServerFooter(bool isCardLight, UnoPalette palette) {
    final isOnline = _isServerConnected || ApiService.isConnected;
    final dotColor = isOnline
        ? const Color(0xFF22C55E) // Green when online
        : const Color(0xFFE05A5A); // Red when offline

    return Column(
      children: [
        const SizedBox(height: 16),
        MouseRegion(
          cursor: SystemMouseCursors.click,
          child: InkWell(
            onTap: _showServerSwitchDialog,
            borderRadius: BorderRadius.circular(6),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    width: 6.5,
                    height: 6.5,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: dotColor,
                      boxShadow: [
                        BoxShadow(
                          color: dotColor.withValues(alpha: 0.5),
                          blurRadius: 5,
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
                      style: GoogleFonts.ibmPlexMono(
                        color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                        fontSize: 11,
                      ),
                    ),
                  ),
                  const SizedBox(width: 5),
                  Icon(
                    LucideIcons.arrowLeftRight,
                    size: 11,
                    color: isCardLight
                        ? _AuthColors.mutedDark.withValues(alpha: 0.8)
                        : _AuthColors.coolSlate.withValues(alpha: 0.8),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
