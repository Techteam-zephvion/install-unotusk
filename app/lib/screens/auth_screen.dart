import 'dart:async';
import 'dart:io';
import 'dart:ui';
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

class _AuthScreenState extends State<AuthScreen>
    with SingleTickerProviderStateMixin {
  // Mode: 0 = Sign In, 1 = Create Workspace, 2 = Select Project Server
  int _activeMode = 0;
  // Sign Up sub-section step: 0 = Profile & Workspace, 1 = Credentials, 2 = Role & Confirm
  int _signUpStep = 0;
  bool _isServerConnected = false;
  bool _isScanning = false;
  ServerDiscoveryResult? _discoveryResult;
  Timer? _healthTimer;
  String? _serverToastTitle;
  String? _serverToastDescription;
  Timer? _serverNotificationTimer;
  late bool _localIsDark;

  late final AnimationController _entranceController;
  late final Animation<double> _entranceFade;
  late final Animation<Offset> _heroSlide;
  late final Animation<Offset> _cardSlide;

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

    _entranceController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 480),
    );
    _entranceFade = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    );
    _heroSlide = Tween<Offset>(
      begin: const Offset(-0.02, 0.02),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    ));
    _cardSlide = Tween<Offset>(
      begin: const Offset(0.0, 0.03),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    ));
    _entranceController.forward();

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

  void _showServerErrorToast({
    required String title,
    String description = '',
  }) {
    _serverNotificationTimer?.cancel();
    if (!mounted) return;
    setState(() {
      _serverToastTitle = title;
      _serverToastDescription = description;
    });
    _serverNotificationTimer = Timer(const Duration(seconds: 4), () {
      if (mounted) {
        setState(() {
          _serverToastTitle = null;
          _serverToastDescription = null;
        });
      }
    });
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
      if (!_isServerConnected && !result.isSuccess) {
        _showServerErrorToast(
          title: 'Unable to Connect to Server',
          description: 'No active Unotusk instance was found on local network',
        );
      }
    }
  }

  void _checkServer() async {
    final ok = await ApiService.checkHealth();
    if (mounted) {
      final wasConnected = _isServerConnected;
      setState(() {
        _isServerConnected = ok;
      });
      if (wasConnected && !ok) {
        _showServerErrorToast(
          title: 'Server Connection Lost',
          description: 'The Unotusk Control Plane is no longer responding',
        );
      }
    }
  }

  @override
  void dispose() {
    _healthTimer?.cancel();
    _serverNotificationTimer?.cancel();
    _entranceController.dispose();
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
      final msg = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _isLoading = false;
      });
      final lower = msg.toLowerCase();
      if (!_isServerConnected ||
          lower.contains('failed to connect') ||
          lower.contains('connection refused') ||
          lower.contains('network is unreachable') ||
          lower.contains('timed out')) {
        _showServerErrorToast(
          title: 'Unable to Connect to Server',
          description: 'Please ensure your local Unotusk server is running',
        );
      } else {
        setState(() {
          _errorMessage = msg;
        });
      }
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
      final msg = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _isLoading = false;
      });
      final lower = msg.toLowerCase();
      if (!_isServerConnected ||
          lower.contains('failed to connect') ||
          lower.contains('connection refused') ||
          lower.contains('network is unreachable') ||
          lower.contains('timed out')) {
        _showServerErrorToast(
          title: 'Unable to Connect to Server',
          description: 'Please ensure your local Unotusk server is running',
        );
      } else {
        setState(() {
          _errorMessage = msg;
        });
      }
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

  Widget _buildFloatingServerToast(bool isDark, UnoPalette palette) {
    final isShowing = _serverToastTitle != null;
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 320),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      transitionBuilder: (child, animation) {
        return SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0.0, -0.4),
            end: Offset.zero,
          ).animate(CurvedAnimation(
            parent: animation,
            curve: Curves.easeOutCubic,
          )),
          child: FadeTransition(
            opacity: CurvedAnimation(
              parent: animation,
              curve: Curves.easeOutCubic,
            ),
            child: child,
          ),
        );
      },
      child: !isShowing
          ? const SizedBox.shrink(key: ValueKey('empty-server-toast'))
          : _ServerToastHUD(
              key: ValueKey(
                  'server-toast-$_serverToastTitle-$_serverToastDescription'),
              title: _serverToastTitle!,
              description: _serverToastDescription ?? '',
              isDark: isDark,
            ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = _localIsDark;
    // Opposite Shade Rule:
    // When screen is dark (isDark == true), auth card is LIGHT (isCardLight == true).
    // When screen is light (isDark == false), auth card is DARK (isCardLight == false).
    final isCardLight = isDark;
    final palette = _getEffectivePalette(isDark);

    return Scaffold(
      backgroundColor: isDark ? _AuthColors.obsidianNavy : _AuthColors.sandBg,
      body: TweenAnimationBuilder<double>(
        tween: Tween<double>(end: isDark ? 1.0 : 0.0),
        duration: const Duration(milliseconds: 420),
        curve: Curves.easeInOutCubic,
        builder: (context, t, _) {
          // Smoothly interpolated palette values for Dark (t=1) <-> Light (t=0)
          final baseTopLeft = Color.lerp(
            const Color(0xFFFAF8F4),
            const Color(0xFF060A16),
            t,
          )!;
          final baseMid = Color.lerp(
            _AuthColors.sandBg,
            _AuthColors.obsidianNavy,
            t,
          )!;
          final baseBottomRight = Color.lerp(
            const Color(0xFFE7E0D4),
            const Color(0xFF0F162C),
            t,
          )!;

          final reliefTint = Color.lerp(
            const Color(0xFFE9E2D6),
            const Color(0xFF1A2442),
            t,
          )!;
          final reliefOpacity = lerpDouble(0.36, 0.24, t)!;

          final featherColor = Color.lerp(
            _AuthColors.sandBg,
            _AuthColors.obsidianNavy,
            t,
          )!;
          final vignetteEdge = Color.lerp(
            const Color(0xFFEBE4D8),
            const Color(0xFF050814),
            t,
          )!;
          final spotlightColor = Color.lerp(
            const Color(0xFFFFFFFF),
            _AuthColors.warmSand,
            t,
          )!;

          return Stack(
            fit: StackFit.expand,
            children: [
              // ── Layer 1: Multi-stop Tonal Base Canvas ──
              DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    stops: const [0.0, 0.5, 1.0],
                    colors: [baseTopLeft, baseMid, baseBottomRight],
                  ),
                ),
              ),

              // ── Layer 2: Full-Bleed Sculptural Bas-Relief Artwork ──
              Positioned.fill(
                child: IgnorePointer(
                  child: Opacity(
                    opacity: reliefOpacity,
                    child: ColorFiltered(
                      colorFilter: ColorFilter.mode(
                        reliefTint,
                        BlendMode.color,
                      ),
                      child: Image.asset(
                        'assets/auth_relief_bg.jpg',
                        fit: BoxFit.cover,
                        alignment: const Alignment(-0.28, 0.0),
                        filterQuality: FilterQuality.medium,
                        errorBuilder: (_, _, _) => const SizedBox.shrink(),
                      ),
                    ),
                  ),
                ),
              ),

              // ── Layer 3: Horizontal Editorial Feather Veil ──
              // Keeps the bas-relief sculptural on the left and dissolves smoothly
              // into clean solid obsidian / warm sand behind the right auth card.
              Positioned.fill(
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.centerLeft,
                        end: Alignment.centerRight,
                        stops: const [0.0, 0.36, 0.62, 1.0],
                        colors: [
                          featherColor.withValues(
                              alpha: lerpDouble(0.24, 0.44, t)!),
                          featherColor.withValues(
                              alpha: lerpDouble(0.42, 0.62, t)!),
                          featherColor.withValues(
                              alpha: lerpDouble(0.88, 0.94, t)!),
                          featherColor.withValues(
                              alpha: lerpDouble(0.97, 0.99, t)!),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // ── Layer 4: Top & Bottom Cinematic Framing Vignette ──
              Positioned.fill(
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        stops: const [0.0, 0.22, 0.78, 1.0],
                        colors: [
                          vignetteEdge.withValues(
                              alpha: lerpDouble(0.55, 0.72, t)!),
                          vignetteEdge.withValues(alpha: 0.0),
                          vignetteEdge.withValues(alpha: 0.0),
                          vignetteEdge.withValues(
                              alpha: lerpDouble(0.58, 0.80, t)!),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // ── Layer 5: Subtle Ambient Gallery Spotlight Behind Hero Lockup ──
              Positioned.fill(
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: RadialGradient(
                        center: const Alignment(-0.46, 0.0),
                        radius: 0.72,
                        stops: const [0.0, 0.52, 1.0],
                        colors: [
                          spotlightColor.withValues(
                              alpha: lerpDouble(0.45, 0.07, t)!),
                          spotlightColor.withValues(
                              alpha: lerpDouble(0.14, 0.02, t)!),
                          spotlightColor.withValues(alpha: 0.0),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // ── Layer 6: Foreground Window Chrome & Split Layout ──
              Column(
                children: [
                  WindowTitleBar(
                    transparent: true,
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
                  Expanded(
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        final isWide = constraints.maxWidth >= 920;
                        if (!isWide) {
                          return Center(
                            child: _buildAuthCardShell(
                              isDark: isDark,
                              isCardLight: isCardLight,
                              palette: palette,
                              t: t,
                            ),
                          );
                        }

                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // Left Editorial Brand Showcase over Bas-Relief
                            Expanded(
                              flex: 11,
                              child: FadeTransition(
                                opacity: _entranceFade,
                                child: SlideTransition(
                                  position: _heroSlide,
                                  child: _buildLeftHeroShowcase(
                                    isDark: isDark,
                                    t: t,
                                  ),
                                ),
                              ),
                            ),

                            // Right Opposite-Shade Auth Card Panel
                            Expanded(
                              flex: 10,
                              child: Center(
                                child: FadeTransition(
                                  opacity: _entranceFade,
                                  child: SlideTransition(
                                    position: _cardSlide,
                                    child: _buildAuthCardShell(
                                      isDark: isDark,
                                      isCardLight: isCardLight,
                                      palette: palette,
                                      t: t,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                ],
              ),

              // ── Layer 7: Floating Auto-Vanishing Server Notification / Toast HUD ──
              Positioned(
                top: 44,
                left: 0,
                right: 0,
                child: Center(
                  child: _buildFloatingServerToast(isDark, palette),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildLeftHeroShowcase({
    required bool isDark,
    required double t,
  }) {
    // Unified opposite-shade / exact logo brand tone:
    // Dark mode (#0A0F20 bg) -> Warm Sand (#CBC1B4) matching the light elephant logo
    // Light mode (#F2EFE9 bg) -> Obsidian Navy (#0A0F20) matching the dark elephant logo
    final brandColor = Color.lerp(
      _AuthColors.obsidianNavy,
      _AuthColors.warmSand,
      t,
    )!;
    final subColor = Color.lerp(
      const Color(0xFF3A393D),
      _AuthColors.warmSand.withValues(alpha: 0.76),
      t,
    )!;
    final mutedColor = Color.lerp(
      _AuthColors.mutedDark,
      _AuthColors.warmSand.withValues(alpha: 0.62),
      t,
    )!;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isLarge = constraints.maxWidth >= 600;
        // Account for transparent padding inside logo PNG so the visible mark
        // stands clearly larger than the wordmark and frames the full lockup.
        final logoMarkSize = isLarge ? 136.0 : 114.0;
        final wordmarkSize = isLarge ? 72.0 : 60.0;
        final taglineSize = isLarge ? 20.5 : 17.5;

        return Padding(
          padding: EdgeInsets.fromLTRB(
            isLarge ? 60 : 44,
            34,
            32,
            42,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // ── Top Spacer (keeps brand lockup vertically centered) ──
              const SizedBox(height: 1),

              // ── Centerpiece Free-Standing Logo & Aligned Wordmark Lockup ──
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    UnotuskLogo(size: logoMarkSize, onDark: isDark),
                    const SizedBox(width: 6),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Unotusk',
                          style: GoogleFonts.youngSerif(
                            color: brandColor,
                            fontSize: wordmarkSize,
                            letterSpacing: -1.3,
                            height: 0.98,
                            shadows: [
                              Shadow(
                                color: (isDark
                                        ? const Color(0xFF040712)
                                        : _AuthColors.sandBg)
                                    .withValues(alpha: 0.55),
                                blurRadius: 18,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Padding(
                          padding: const EdgeInsets.only(left: 3),
                          child: Text(
                            'Project Intelligence Layer',
                            maxLines: 1,
                            style: GoogleFonts.cormorantGaramond(
                              color: subColor,
                              fontSize: taglineSize,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 1.8,
                              height: 1.2,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // ── Bottom Studio Capability Strip ──
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 0,
                runSpacing: 8,
                children: [
                  _buildHeroPillar(
                    LucideIcons.gitBranch,
                    'AST-Grounded',
                    mutedColor,
                  ),
                  _buildHeroPillarDivider(brandColor),
                  _buildHeroPillar(
                    LucideIcons.shieldCheck,
                    'Zero Hallucination',
                    mutedColor,
                  ),
                  _buildHeroPillarDivider(brandColor),
                  _buildHeroPillar(
                    LucideIcons.cpu,
                    'Local-First',
                    mutedColor,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHeroPillar(IconData icon, String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(width: 6),
        Text(
          label,
          style: GoogleFonts.inter(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w500,
            letterSpacing: 0.2,
          ),
        ),
      ],
    );
  }

  Widget _buildHeroPillarDivider(Color color) {
    return Container(
      width: 1,
      height: 12,
      margin: const EdgeInsets.symmetric(horizontal: 14),
      color: color.withValues(alpha: 0.24),
    );
  }

  Widget _buildAuthCardShell({
    required bool isDark,
    required bool isCardLight,
    required UnoPalette palette,
    required double t,
  }) {
    final cardTop = Color.lerp(
      const Color(0xFF13192F),
      const Color(0xFFFAF8F3),
      t,
    )!;
    final cardMid = Color.lerp(
      _AuthColors.obsidianNavy,
      _AuthColors.sandCream,
      t,
    )!;
    final cardBottom = Color.lerp(
      const Color(0xFF070B18),
      const Color(0xFFEDE7DC),
      t,
    )!;
    final cardBorder = Color.lerp(
      _AuthColors.darkBorderHover,
      _AuthColors.warmSand,
      t,
    )!;

    return FittedBox(
      fit: BoxFit.scaleDown,
      alignment: Alignment.center,
      child: Container(
        key: const ValueKey('auth-card-shell'),
        width: 440,
        margin: const EdgeInsets.symmetric(horizontal: 28, vertical: 20),
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            stops: const [0.0, 0.55, 1.0],
            colors: [cardTop, cardMid, cardBottom],
          ),
          border: Border.all(
            color: cardBorder,
            width: 1.25,
          ),
          borderRadius: BorderRadius.circular(22),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: lerpDouble(0.24, 0.62, t)!),
              blurRadius: lerpDouble(36, 52, t)!,
              offset: const Offset(0, 18),
            ),
            BoxShadow(
              color: _AuthColors.warmSand.withValues(
                alpha: lerpDouble(0.06, 0.08, t)!,
              ),
              blurRadius: 1,
              spreadRadius: 0,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: _activeMode == 2
            ? _buildServerList(isCardLight, palette)
            : _buildAuthCard(isCardLight, palette),
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

        // ── Heading & Subtitle (Fixed height prevents any vertical jump between tabs) ──
        Text(
          _activeMode == 0 ? 'Sign in to Unotusk' : 'Sign up to Unotusk',
          style: GoogleFonts.youngSerif(
            color: isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite,
            fontSize: 24,
          ),
        ),
        const SizedBox(height: 5),
        SizedBox(
          height: 38,
          child: Align(
            alignment: Alignment.topLeft,
            child: Text(
              _activeMode == 0
                  ? 'Enter your work email and password to access your workspace.'
                  : 'Create your account to join your project intelligence workspace.',
              style: GoogleFonts.inter(
                color: isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),

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
                    _signUpStep = 0;
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
                    _signUpStep = 0;
                    _errorMessage = null;
                  }),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),

        _buildErrorBanner(isCardLight),

        // ── Mode-specific form locked to identical height across Sign In & Sign Up ──
        SizedBox(
          height: 244,
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            switchInCurve: Curves.easeOutCubic,
            switchOutCurve: Curves.easeInCubic,
            transitionBuilder: (child, animation) {
              return FadeTransition(
                opacity: animation,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0.03, 0),
                    end: Offset.zero,
                  ).animate(animation),
                  child: child,
                ),
              );
            },
            child: _activeMode == 0
                ? KeyedSubtree(
                    key: const ValueKey('mode-signin'),
                    child: _buildSignInForm(isCardLight, palette),
                  )
                : KeyedSubtree(
                    key: ValueKey('mode-signup-$_signUpStep'),
                    child: _buildCreateWorkspaceForm(isCardLight, palette),
                  ),
          ),
        ),

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
        const SizedBox(height: 16),

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
        const Spacer(),

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

  void _advanceSignUpStep() {
    if (_signUpStep == 0) {
      if (_nameController.text.trim().isEmpty) {
        setState(() => _errorMessage = 'Please enter your full name.');
        return;
      }
      if (_orgController.text.trim().isEmpty) {
        setState(() => _errorMessage = 'Please enter your organisation name.');
        return;
      }
      setState(() {
        _errorMessage = null;
        _signUpStep = 1;
      });
    } else if (_signUpStep == 1) {
      final email = _emailController.text.trim().toLowerCase();
      if (!_validateAcmeEmail(email)) return;
      if (_passwordController.text.length < 8) {
        setState(() =>
            _errorMessage = 'Password must be at least 8 characters long.');
        return;
      }
      setState(() {
        _errorMessage = null;
        _signUpStep = 2;
      });
    } else {
      _handleCreateWorkspace();
    }
  }

  // ─────────────────────────────────────────────────────────────
  //  Create Workspace / Sign Up Form (Clean 3-Section Flow, Exact Sign-In Size)
  // ─────────────────────────────────────────────────────────────
  Widget _buildCreateWorkspaceForm(bool isCardLight, UnoPalette palette) {
    final labelColor =
        isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand;
    final mutedColor =
        isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate;
    final btnBg = isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand;
    final btnFg = isCardLight ? _AuthColors.pureWhite : _AuthColors.obsidianNavy;

    const stepTitles = ['Workspace', 'Credentials', 'Role'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── Minimal Section Progress Header ──
        SizedBox(
          height: 20,
          child: Row(
            children: [
              if (_signUpStep > 0) ...[
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () => setState(() {
                      _errorMessage = null;
                      _signUpStep--;
                    }),
                    behavior: HitTestBehavior.opaque,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          LucideIcons.arrowLeft,
                          size: 13,
                          color: labelColor,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          'Back',
                          style: GoogleFonts.inter(
                            color: labelColor,
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Text(
                    '·',
                    style: GoogleFonts.inter(
                      color: mutedColor.withValues(alpha: 0.6),
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
              Expanded(
                child: Text(
                  'Step ${_signUpStep + 1} of 3 · ${stepTitles[_signUpStep]}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(
                    color: mutedColor,
                    fontSize: 11.5,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // Interactive clickable progress dashes
              Row(
                mainAxisSize: MainAxisSize.min,
                children: List.generate(3, (i) {
                  final active = i == _signUpStep;
                  final completed = i < _signUpStep;
                  return MouseRegion(
                    cursor: completed
                        ? SystemMouseCursors.click
                        : SystemMouseCursors.basic,
                    child: GestureDetector(
                      onTap: completed
                          ? () => setState(() {
                                _errorMessage = null;
                                _signUpStep = i;
                              })
                          : null,
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        curve: Curves.easeOutCubic,
                        margin: EdgeInsets.only(left: i == 0 ? 0 : 5),
                        width: active ? 22 : 12,
                        height: 3.5,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(2),
                          color: (active || completed)
                              ? btnBg
                              : (isCardLight
                                  ? _AuthColors.warmSand.withValues(alpha: 0.55)
                                  : _AuthColors.darkBorderHover),
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // ── Section Content ──
        if (_signUpStep == 0) ...[
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
            onSubmitted: _advanceSignUpStep,
          ),
          const SizedBox(height: 12),
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
            onSubmitted: _advanceSignUpStep,
          ),
        ] else if (_signUpStep == 1) ...[
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
            onSubmitted: _advanceSignUpStep,
          ),
          const SizedBox(height: 12),
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
            onSubmitted: _advanceSignUpStep,
            suffix: MouseRegion(
              cursor: SystemMouseCursors.click,
              child: GestureDetector(
                onTap: () =>
                    setState(() => _obscurePassword = !_obscurePassword),
                child: Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: Icon(
                    _obscurePassword ? LucideIcons.eye : LucideIcons.eyeOff,
                    size: 16.5,
                    color: mutedColor,
                  ),
                ),
              ),
            ),
          ),
        ] else ...[
          Text(
            'Select Role',
            style: GoogleFonts.inter(
              color: labelColor,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.2,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildRoleOptionCard(
                  value: 'Member (Dev)',
                  title: 'Member',
                  subtitle: 'Developer access',
                  icon: LucideIcons.code,
                  isCardLight: isCardLight,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildRoleOptionCard(
                  value: 'Manager',
                  title: 'Manager',
                  subtitle: 'Workspace lead',
                  icon: LucideIcons.shieldCheck,
                  isCardLight: isCardLight,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              SizedBox(
                width: 20,
                height: 20,
                child: Checkbox(
                  value: _termsAgreed,
                  activeColor: btnBg,
                  checkColor: btnFg,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(4),
                  ),
                  side: BorderSide(
                    color: isCardLight
                        ? _AuthColors.sandTint
                        : _AuthColors.coolSlate,
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
                    onTap: () => setState(() => _termsAgreed = !_termsAgreed),
                    child: Text(
                      'I agree to the terms of service',
                      style: GoogleFonts.inter(
                        color: mutedColor,
                        fontSize: 12.5,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],

        const Spacer(),

        // ── Primary Section Action / Submit Button ──
        SizedBox(
          height: 44,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _advanceSignUpStep,
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
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _signUpStep < 2 ? 'Continue' : 'Sign Up',
                        style: GoogleFonts.inter(
                          color: btnFg,
                          fontSize: 14.5,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.1,
                        ),
                      ),
                      if (_signUpStep < 2) ...[
                        const SizedBox(width: 6),
                        Icon(
                          LucideIcons.arrowRight,
                          size: 15,
                          color: btnFg,
                        ),
                      ],
                    ],
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildRoleOptionCard({
    required String value,
    required String title,
    required String subtitle,
    required IconData icon,
    required bool isCardLight,
  }) {
    final isSelected = _selectedRole == value;
    final bg = isSelected
        ? (isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand)
        : (isCardLight ? _AuthColors.pureWhite : _AuthColors.slateNavy);
    final border = isSelected
        ? (isCardLight ? _AuthColors.obsidianNavy : _AuthColors.warmSand)
        : (isCardLight ? _AuthColors.warmSand : _AuthColors.darkBorderHover);
    final fg = isSelected
        ? (isCardLight ? _AuthColors.pureWhite : _AuthColors.obsidianNavy)
        : (isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite);
    final subFg = isSelected
        ? fg.withValues(alpha: 0.72)
        : (isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: () => setState(() => _selectedRole = value),
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 170),
          curve: Curves.easeOutCubic,
          height: 66,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: border, width: 1.2),
          ),
          child: Row(
            children: [
              Icon(icon, size: 16, color: fg),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: fg,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 1),
                    Text(
                      subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: subFg,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
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
  //  Server Status Footer (Studio-Grade Tactile Connection Pill)
  // ─────────────────────────────────────────────────────────────
  Widget _buildServerFooter(bool isCardLight, UnoPalette palette) {
    return Column(
      children: [
        const SizedBox(height: 18),
        _TactileServerPill(
          isOnline: _isServerConnected || ApiService.isConnected,
          isScanning: _isScanning,
          serverUrl: ApiService.baseUrl,
          isCardLight: isCardLight,
          onTap: _showServerSwitchDialog,
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────
//  Tactile Server Connection Pill Widget
// ─────────────────────────────────────────────────────────────
class _TactileServerPill extends StatefulWidget {
  final bool isOnline;
  final bool isScanning;
  final String serverUrl;
  final bool isCardLight;
  final VoidCallback onTap;

  const _TactileServerPill({
    required this.isOnline,
    required this.isScanning,
    required this.serverUrl,
    required this.isCardLight,
    required this.onTap,
  });

  @override
  State<_TactileServerPill> createState() => _TactileServerPillState();
}

class _TactileServerPillState extends State<_TactileServerPill> {
  bool _isHovered = false;
  bool _isPressed = false;

  String get _cleanEndpoint {
    final raw = widget.serverUrl.trim();
    final stripped = raw
        .replaceFirst(RegExp(r'^https?:\/\/'), '')
        .replaceFirst(RegExp(r'\/+$'), '');
    return stripped.isEmpty ? '127.0.0.1:28000' : stripped;
  }

  @override
  Widget build(BuildContext context) {
    final isOnline = widget.isOnline;
    final isScanning = widget.isScanning;
    final isCardLight = widget.isCardLight;

    final dotColor = isScanning
        ? const Color(0xFFF59E0B)
        : (isOnline ? const Color(0xFF22C55E) : const Color(0xFFEF4444));

    final textPrimary =
        isCardLight ? _AuthColors.obsidianNavy : _AuthColors.pureWhite;
    final textMuted =
        isCardLight ? _AuthColors.mutedDark : _AuthColors.coolSlate;

    final bg = isCardLight
        ? (_isHovered
            ? _AuthColors.pureWhite
            : _AuthColors.sandCreamBorder.withValues(alpha: 0.65))
        : (_isHovered
            ? _AuthColors.slateNavy
            : _AuthColors.obsidianNavy.withValues(alpha: 0.75));

    final borderColor = isCardLight
        ? (_isHovered
            ? _AuthColors.sandTint
            : _AuthColors.warmSand.withValues(alpha: 0.65))
        : (_isHovered
            ? _AuthColors.warmSand.withValues(alpha: 0.35)
            : _AuthColors.darkBorderHover);

    final tooltipMsg = isScanning
        ? 'Scanning local network for active servers...'
        : (isOnline
            ? 'Connected to Control Plane • Click to configure IP or switch server'
            : 'Control Plane offline • Click to configure IP or re-scan');

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: Tooltip(
        message: tooltipMsg,
        preferBelow: true,
        verticalOffset: 16,
        child: GestureDetector(
          onTapDown: (_) => setState(() => _isPressed = true),
          onTapUp: (_) => setState(() => _isPressed = false),
          onTapCancel: () => setState(() => _isPressed = false),
          onTap: widget.onTap,
          child: AnimatedScale(
            scale: _isPressed ? 0.98 : 1.0,
            duration: const Duration(milliseconds: 120),
            curve: Curves.easeOutCubic,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOutCubic,
              height: 30,
              constraints: const BoxConstraints(maxWidth: 320),
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
              decoration: BoxDecoration(
                color: bg,
                borderRadius: BorderRadius.circular(15),
                border: Border.all(color: borderColor, width: 0.85),
                boxShadow: [
                  BoxShadow(
                    color: isCardLight
                        ? _AuthColors.obsidianNavy
                            .withValues(alpha: _isHovered ? 0.08 : 0.03)
                        : Colors.black
                            .withValues(alpha: _isHovered ? 0.35 : 0.18),
                    blurRadius: _isHovered ? 8 : 4,
                    offset: const Offset(0, 1),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  if (isScanning)
                    SizedBox(
                      width: 10,
                      height: 10,
                      child: CircularProgressIndicator(
                        strokeWidth: 1.75,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          isCardLight
                              ? _AuthColors.obsidianNavy
                              : _AuthColors.warmSand,
                        ),
                      ),
                    )
                  else
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      width: 6.5,
                      height: 6.5,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: dotColor,
                        boxShadow: [
                          BoxShadow(
                            color: dotColor.withValues(alpha: 0.45),
                            blurRadius: 4,
                            spreadRadius: 0.5,
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(width: 7.5),
                  Text(
                    isScanning
                        ? 'Scanning...'
                        : (isOnline ? 'Control Plane' : 'Offline'),
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.15,
                      color: isScanning
                          ? textMuted
                          : (isOnline
                              ? textPrimary
                              : const Color(0xFFE05A5A)),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 5),
                    child: Text(
                      '·',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: textMuted.withValues(alpha: 0.5),
                      ),
                    ),
                  ),
                  Flexible(
                    child: Text(
                      _cleanEndpoint,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.ibmPlexMono(
                        fontSize: 10.5,
                        fontWeight: FontWeight.w500,
                        color: textMuted,
                      ),
                    ),
                  ),
                  const SizedBox(width: 7),
                  Icon(
                    LucideIcons.slidersHorizontal,
                    size: 11,
                    color: _isHovered
                        ? textPrimary
                        : textMuted.withValues(alpha: 0.75),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────
//  Floating Auto-Vanishing Server Notification Toast HUD
// ─────────────────────────────────────────────────────────────
class _ServerToastHUD extends StatelessWidget {
  final String title;
  final String description;
  final bool isDark;

  const _ServerToastHUD({
    super.key,
    required this.title,
    required this.description,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    // Luxurious solid tonal palette (no BackdropFilter / no margin clipping artifacts)
    final bgColors = isDark
        ? const [Color(0xFF161B28), Color(0xFF0F1320)]
        : const [Color(0xFFFFFFFF), Color(0xFFF7F4EE)];

    // Hairline warm terracotta stroke
    final borderColor = isDark
        ? const Color(0xFFD4725A).withValues(alpha: 0.35)
        : const Color(0xFFD4725A).withValues(alpha: 0.45);

    final textPrimary =
        isDark ? const Color(0xFFF4F1EC) : const Color(0xFF0B1020);
    final textMuted =
        isDark ? const Color(0xFF8E94A4) : const Color(0xFF6B686A);

    return Material(
      color: Colors.transparent,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: bgColors,
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderColor, width: 0.85),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.40 : 0.10),
              blurRadius: 20,
              offset: const Offset(0, 6),
            ),
            BoxShadow(
              color: const Color(0xFFD4725A).withValues(alpha: 0.06),
              blurRadius: 10,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Glowing Icon Badge
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: const Color(0xFFD4725A).withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: const Color(0xFFD4725A).withValues(alpha: 0.25),
                  width: 0.75,
                ),
              ),
              alignment: Alignment.center,
              child: const Icon(
                LucideIcons.cloudOff,
                size: 14,
                color: Color(0xFFE87A64),
              ),
            ),
            const SizedBox(width: 12),

            // Text Stack (Title + Clean Context)
            Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(
                    color: textPrimary,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.1,
                  ),
                ),
                if (description.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    description,
                    style: GoogleFonts.inter(
                      color: textMuted,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
