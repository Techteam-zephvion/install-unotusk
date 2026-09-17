import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/unotusk_mark.dart';
import '../../connection/presentation/connection_controller.dart';
import 'auth_controller.dart';

enum _AuthScreen { entry, checking, existingOrg, newOrg, oidcConsent, oidcTokenExchange, authenticating, denied }

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> with SingleTickerProviderStateMixin {
  _AuthScreen _screen = _AuthScreen.entry;
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _orgCtrl = TextEditingController();
  bool _showPasswordField = false;
  bool _obscurePassword = true;
  String _role = 'Engineer';
  bool _agreed = false;
  String _orgName = '';
  String _orgProvider = 'Google OIDC';
  String _deniedReason = '';
  int _dotCount = 0;
  Timer? _dotTimer;
  late AnimationController _dotsCtrl;

  @override
  void initState() {
    super.initState();
    _dotsCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
  }

  @override
  void dispose() {
    _emailCtrl.dispose(); _passwordCtrl.dispose(); _nameCtrl.dispose(); _orgCtrl.dispose();
    _dotsCtrl.dispose(); _dotTimer?.cancel();
    super.dispose();
  }

  bool get _isValidEmail => RegExp(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$").hasMatch(_emailCtrl.text.trim());

  void _startDots() {
    _dotTimer?.cancel();
    _dotsCtrl.repeat();
    _dotTimer = Timer.periodic(const Duration(milliseconds: 400), (_) { if (mounted) setState(() => _dotCount = (_dotCount + 1) % 4); });
  }
  void _stopDots() {
    _dotTimer?.cancel();
    _dotsCtrl.stop();
  }

  Future<void> _handleContinue() async {
    if (!_isValidEmail) return;
    final email = _emailCtrl.text.trim();
    setState(() => _screen = _AuthScreen.checking);
    _startDots();
    await Future.delayed(const Duration(milliseconds: 1500));
    _stopDots();
    if (!mounted) return;
    final domain = email.split('@').last.toLowerCase();
    final knownOrgs = { 'acme-corp.com': ('Acme Corporation', 'Microsoft Entra OIDC'), 'globex.io': ('Globex Systems', 'Google OIDC'), 'example.com': ('Example Corp', 'Google OIDC'), 'company.com': ('Company Inc.', 'Google OIDC') };
    if (knownOrgs.containsKey(domain)) {
      final entry = knownOrgs[domain]!;
      setState(() { _orgName = entry.$1; _orgProvider = entry.$2; _screen = _AuthScreen.existingOrg; });
    } else {
      setState(() { _showPasswordField = true; _screen = _AuthScreen.entry; });
    }
  }

  Future<void> _handleExistingOrgContinue() async {
    setState(() => _screen = _AuthScreen.oidcConsent);
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    setState(() => _screen = _AuthScreen.oidcTokenExchange);
    await Future.delayed(const Duration(milliseconds: 1200));
    if (!mounted) return;
    await _doAuthenticate();
  }

  Future<void> _handleProviderButton(String provider) async {
    setState(() { _orgProvider = provider; _screen = _AuthScreen.oidcConsent; });
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    setState(() => _screen = _AuthScreen.oidcTokenExchange);
    await Future.delayed(const Duration(milliseconds: 1200));
    if (!mounted) return;
    await _doAuthenticate();
  }

  Future<void> _handlePasswordSignIn() async {
    if (!_isValidEmail || _passwordCtrl.text.isEmpty) return;
    setState(() => _screen = _AuthScreen.authenticating);
    final success = await ref.read(authControllerProvider.notifier).login(email: _emailCtrl.text.trim(), password: _passwordCtrl.text);
    if (!mounted) return;
    if (success) { context.go('/projects'); }
    else { setState(() { _deniedReason = ref.read(authControllerProvider).errorMessage ?? 'Authentication failed.'; _screen = _AuthScreen.denied; }); }
  }

  Future<void> _handleNewOrgRegister() async {
    if (_nameCtrl.text.trim().isEmpty || _orgCtrl.text.trim().isEmpty || !_agreed) return;
    setState(() => _screen = _AuthScreen.authenticating);
    final success = await ref.read(authControllerProvider.notifier).signup(name: _nameCtrl.text.trim(), email: _emailCtrl.text.trim(), password: _passwordCtrl.text.isNotEmpty ? _passwordCtrl.text : 'oidc_placeholder');
    if (!mounted) return;
    if (success) { context.go('/projects'); }
    else { setState(() { _deniedReason = ref.read(authControllerProvider).errorMessage ?? 'Registration failed.'; _screen = _AuthScreen.denied; }); }
  }

  Future<void> _doAuthenticate() async {
    setState(() => _screen = _AuthScreen.authenticating);
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    final success = await ref.read(authControllerProvider.notifier).login(email: _emailCtrl.text.trim(), password: _passwordCtrl.text.isNotEmpty ? _passwordCtrl.text : 'demo');
    if (!mounted) return;
    if (success) { context.go('/projects'); }
    else { setState(() => _screen = _AuthScreen.newOrg); }
  }

  @override
  Widget build(BuildContext context) {
    final connectionState = ref.watch(connectionControllerProvider);
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      body: Stack(children: [
        if (_screen == _AuthScreen.authenticating)
          Container(color: const Color(0xFF0D0A08), child: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
            const _PulsingDot(color: AppColors.live),
            const SizedBox(height: 14),
            Text('Establishing OIDC Session...', style: AppTextStyles.mono(fontSize: 13, color: const Color(0xFFA89070), letterSpacing: 1.04)),
          ])))
        else ...[
          Positioned(top: 24, left: 28, child: Row(children: [
            const UnotuskMark(size: 22),
            const SizedBox(width: 9),
            Text('Unotusk', style: AppTextStyles.logoWordmark),
            const SizedBox(width: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: AppColors.accentMuted, border: Border.all(color: AppColors.accent.withValues(alpha: 0.25)), borderRadius: BorderRadius.circular(12)),
              child: Text('OIDC 1.0 SSO', style: AppTextStyles.mono(fontSize: 10, fontWeight: FontWeight.w600, color: AppColors.accent)),
            ),
          ])),
          Center(child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 80, 24, 48),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              transitionBuilder: (child, anim) => FadeTransition(opacity: anim, child: SlideTransition(position: Tween(begin: const Offset(0, 0.04), end: Offset.zero).animate(anim), child: child)),
              child: _buildCard(connectionState, key: ValueKey(_screen)),
            ),
          )),
        ],
      ]),
    );
  }

  Widget _buildCard(dynamic connectionState, {required Key key}) {
    switch (_screen) {
      case _AuthScreen.entry: return _EntryCard(key: key, emailCtrl: _emailCtrl, passwordCtrl: _passwordCtrl, showPasswordField: _showPasswordField, obscurePassword: _obscurePassword, onObscureToggle: () => setState(() => _obscurePassword = !_obscurePassword), isValidEmail: _isValidEmail, onContinue: _handleContinue, onPasswordSignIn: _handlePasswordSignIn, onGoogleProvider: () => _handleProviderButton('Google OIDC'), onMicrosoftProvider: () => _handleProviderButton('Microsoft Entra OIDC'), onCustomIssuer: () => setState(() => _screen = _AuthScreen.newOrg), connectionState: connectionState);
      case _AuthScreen.checking: return _CheckingCard(key: key, dotCount: _dotCount, email: _emailCtrl.text.trim());
      case _AuthScreen.existingOrg: return _ExistingOrgCard(key: key, orgName: _orgName, provider: _orgProvider, email: _emailCtrl.text.trim(), onContinue: _handleExistingOrgContinue, onBack: () => setState(() { _showPasswordField = false; _screen = _AuthScreen.entry; }));
      case _AuthScreen.newOrg: return _NewOrgCard(key: key, nameCtrl: _nameCtrl, orgCtrl: _orgCtrl, passwordCtrl: _passwordCtrl, email: _emailCtrl.text.trim(), role: _role, agreed: _agreed, onRoleChange: (v) => setState(() => _role = v), onAgreedChange: (v) => setState(() => _agreed = v), onRegister: _handleNewOrgRegister, onBack: () => setState(() => _screen = _AuthScreen.entry));
      case _AuthScreen.oidcConsent: return _OidcConsentCard(key: key, provider: _orgProvider, orgName: _orgName);
      case _AuthScreen.oidcTokenExchange: return _OidcTokenExchangeCard(key: key, provider: _orgProvider, dotCount: _dotCount);
      case _AuthScreen.denied: return _DeniedCard(key: key, reason: _deniedReason, onRetry: () => setState(() { _screen = _AuthScreen.entry; _showPasswordField = false; }));
      default: return const SizedBox.shrink();
    }
  }
}

class _AuthCard extends StatelessWidget {
  final Widget child;
  final double maxWidth;
  const _AuthCard({required this.child, this.maxWidth = 420});
  @override
  Widget build(BuildContext context) => Center(child: Container(
    width: double.infinity, constraints: BoxConstraints(maxWidth: maxWidth), padding: const EdgeInsets.all(32),
    decoration: BoxDecoration(color: AppColors.bgElevated, border: Border.all(color: AppColors.divider), borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Color(0x3D000000), blurRadius: 56, offset: Offset(0, 24))]),
    child: child,
  ));
}

class _PulsingDot extends StatefulWidget {
  final Color color;
  final double size;
  const _PulsingDot({required this.color, this.size = 8});
  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;
  @override
  void initState() { super.initState(); _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 850))..repeat(reverse: true); _anim = Tween(begin: 0.2, end: 1.0).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut)); }
  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => AnimatedBuilder(animation: _anim, builder: (_, __) => Opacity(opacity: _anim.value, child: Container(width: widget.size, height: widget.size, decoration: BoxDecoration(shape: BoxShape.circle, color: widget.color))));
}

class _EntryCard extends StatelessWidget {
  final TextEditingController emailCtrl, passwordCtrl;
  final bool showPasswordField, obscurePassword, isValidEmail;
  final VoidCallback onObscureToggle, onContinue, onPasswordSignIn, onGoogleProvider, onMicrosoftProvider, onCustomIssuer;
  final dynamic connectionState;
  const _EntryCard({super.key, required this.emailCtrl, required this.passwordCtrl, required this.showPasswordField, required this.obscurePassword, required this.onObscureToggle, required this.isValidEmail, required this.onContinue, required this.onPasswordSignIn, required this.onGoogleProvider, required this.onMicrosoftProvider, required this.onCustomIssuer, required this.connectionState});
  @override
  Widget build(BuildContext context) => _AuthCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Align(alignment: Alignment.centerLeft, child: Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4), decoration: BoxDecoration(color: AppColors.accentMuted, border: Border.all(color: AppColors.accent.withValues(alpha: 0.2)), borderRadius: BorderRadius.circular(14)), child: Row(mainAxisSize: MainAxisSize.min, children: [const Icon(Icons.shield_outlined, size: 12, color: AppColors.accent), const SizedBox(width: 6), Text('OIDC Authentication', style: AppTextStyles.mono(fontSize: 11, fontWeight: FontWeight.w500, color: AppColors.textPrimary))]))),
    const SizedBox(height: 14),
    Text('Sign in to Unotusk', style: AppTextStyles.authHeading),
    const SizedBox(height: 8),
    Text('Authenticating via OpenID Connect (OIDC) identity provider for single sign-on security.', style: AppTextStyles.body.copyWith(color: AppColors.textSecondary, height: 1.55)),
    const SizedBox(height: 20),
    Text('Work Email Address', style: AppTextStyles.label),
    const SizedBox(height: 5),
    _OidcTextField(controller: emailCtrl, hint: 'you@company.com', keyboardType: TextInputType.emailAddress),
    if (showPasswordField) ...[
      const SizedBox(height: 12),
      Text('Password', style: AppTextStyles.label),
      const SizedBox(height: 5),
      _OidcTextField(controller: passwordCtrl, hint: '••••••••', obscureText: obscurePassword, suffixIcon: GestureDetector(onTap: onObscureToggle, child: Icon(obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined, size: 16, color: AppColors.textSecondary))),
    ],
    const SizedBox(height: 12),
    _OidcButton(label: showPasswordField ? 'Sign in' : 'Continue with OIDC Discovery', enabled: isValidEmail, filled: true, onPressed: showPasswordField ? onPasswordSignIn : onContinue),
    if (!showPasswordField) ...[
      Padding(padding: const EdgeInsets.symmetric(vertical: 20), child: Row(children: [const Expanded(child: Divider(color: AppColors.divider)), Padding(padding: const EdgeInsets.symmetric(horizontal: 10), child: Text('or sign in via OIDC provider', style: AppTextStyles.sectionLabel)), const Expanded(child: Divider(color: AppColors.divider))])),
      _ProviderButton(label: 'Sign in with Google OIDC', icon: Icons.g_mobiledata_rounded, onPressed: onGoogleProvider),
      const SizedBox(height: 9),
      _ProviderButton(label: 'Sign in with Microsoft Entra OIDC', icon: Icons.window_rounded, onPressed: onMicrosoftProvider),
      const SizedBox(height: 9),
      _ProviderButton(label: 'Configure custom OIDC issuer', icon: Icons.settings_ethernet_rounded, onPressed: onCustomIssuer),
    ],
    const SizedBox(height: 20),
    const Divider(color: AppColors.divider),
    const SizedBox(height: 12),
    GestureDetector(
      onTap: () => GoRouter.of(context).go('/connection'),
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Container(width: 7, height: 7, decoration: BoxDecoration(shape: BoxShape.circle, color: (connectionState?.isConnected ?? false) ? AppColors.live : AppColors.warning)),
        const SizedBox(width: 6),
        Flexible(child: Text((connectionState?.isConnected ?? false) ? 'Server: ${connectionState?.serverUrl}' : 'Server: Offline — Tap to configure', style: AppTextStyles.caption.copyWith(fontSize: 11), overflow: TextOverflow.ellipsis)),
      ]),
    ),
  ]));
}

class _CheckingCard extends StatelessWidget {
  final int dotCount; final String email;
  const _CheckingCard({super.key, required this.dotCount, required this.email});
  @override
  Widget build(BuildContext context) => _AuthCard(child: Column(children: [
    const SizedBox(height: 12), const _PulsingDot(color: AppColors.neutral, size: 10), const SizedBox(height: 20),
    Text('Checking organisation membership${".".padRight(dotCount + 1, ".").substring(1)}', style: AppTextStyles.body.copyWith(color: AppColors.textSecondary)),
    const SizedBox(height: 8),
    Text(email, style: AppTextStyles.mono(fontSize: 12, color: AppColors.accent)),
    const SizedBox(height: 12),
  ]));
}

class _ExistingOrgCard extends StatelessWidget {
  final String orgName, provider, email; final VoidCallback onContinue, onBack;
  const _ExistingOrgCard({super.key, required this.orgName, required this.provider, required this.email, required this.onContinue, required this.onBack});
  @override
  Widget build(BuildContext context) => _AuthCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Row(children: [Container(width: 36, height: 36, decoration: BoxDecoration(color: AppColors.neutral.withValues(alpha: 0.15), shape: BoxShape.circle), child: const Icon(Icons.business_outlined, size: 18, color: AppColors.neutral)), const SizedBox(width: 12), Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(orgName, style: AppTextStyles.h2), Text(provider, style: AppTextStyles.caption)])]),
    const SizedBox(height: 16),
    Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.bgSurface, border: Border.all(color: AppColors.divider), borderRadius: BorderRadius.circular(8)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('ORGANISATION FOUND', style: AppTextStyles.monoBadge.copyWith(color: AppColors.live)), const SizedBox(height: 4), Text(email, style: AppTextStyles.body)])),
    const SizedBox(height: 20),
    Text('Continue with $provider?', style: AppTextStyles.authHeading.copyWith(fontSize: 20)),
    const SizedBox(height: 6),
    Text('You will be redirected to your organisation identity provider to complete authentication.', style: AppTextStyles.body.copyWith(color: AppColors.textSecondary, height: 1.55)),
    const SizedBox(height: 20),
    _OidcButton(label: 'Continue with $provider', enabled: true, filled: true, onPressed: onContinue),
    const SizedBox(height: 10),
    _OidcButton(label: 'Use a different account', enabled: true, filled: false, onPressed: onBack),
  ]));
}

class _NewOrgCard extends StatelessWidget {
  final TextEditingController nameCtrl, orgCtrl, passwordCtrl; final String email, role; final bool agreed;
  final ValueChanged<String> onRoleChange; final ValueChanged<bool> onAgreedChange; final VoidCallback onRegister, onBack;
  const _NewOrgCard({super.key, required this.nameCtrl, required this.orgCtrl, required this.passwordCtrl, required this.email, required this.role, required this.agreed, required this.onRoleChange, required this.onAgreedChange, required this.onRegister, required this.onBack});
  @override
  Widget build(BuildContext context) => _AuthCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Text('Create your organisation', style: AppTextStyles.authHeading),
    const SizedBox(height: 6),
    Text('No organisation found for $email. Set up your workspace.', style: AppTextStyles.body.copyWith(color: AppColors.textSecondary, height: 1.5)),
    const SizedBox(height: 20),
    Text('Full name', style: AppTextStyles.label), const SizedBox(height: 5), _OidcTextField(controller: nameCtrl, hint: 'Alex Morgan'),
    const SizedBox(height: 12),
    Text('Organisation name', style: AppTextStyles.label), const SizedBox(height: 5), _OidcTextField(controller: orgCtrl, hint: 'Acme Corporation'),
    const SizedBox(height: 12),
    Text('Password', style: AppTextStyles.label), const SizedBox(height: 5), _OidcTextField(controller: passwordCtrl, hint: '••••••••', obscureText: true),
    const SizedBox(height: 12),
    Text('Role', style: AppTextStyles.label), const SizedBox(height: 5),
    Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2), decoration: BoxDecoration(color: AppColors.bgSurface, border: Border.all(color: AppColors.divider), borderRadius: BorderRadius.circular(8)), child: DropdownButtonHideUnderline(child: DropdownButton<String>(value: role, isExpanded: true, dropdownColor: AppColors.bgElevated, style: AppTextStyles.body, items: ['Engineer', 'Product Manager', 'Designer', 'Leadership', 'Other'].map((r) => DropdownMenuItem(value: r, child: Text(r, style: AppTextStyles.body))).toList(), onChanged: (v) { if (v != null) onRoleChange(v); }))),
    const SizedBox(height: 16),
    GestureDetector(onTap: () => onAgreedChange(!agreed), child: Row(children: [Container(width: 18, height: 18, decoration: BoxDecoration(color: agreed ? AppColors.accent : Colors.transparent, border: Border.all(color: agreed ? AppColors.accent : AppColors.divider), borderRadius: BorderRadius.circular(4)), child: agreed ? const Icon(Icons.check, size: 12, color: Color(0xFF0D0A08)) : null), const SizedBox(width: 10), Flexible(child: Text('I agree to the Unotusk terms of service', style: AppTextStyles.caption))])),
    const SizedBox(height: 20),
    _OidcButton(label: 'Create workspace', enabled: agreed, filled: true, onPressed: onRegister),
    const SizedBox(height: 10),
    _OidcButton(label: 'Back', enabled: true, filled: false, onPressed: onBack),
  ]));
}

class _OidcConsentCard extends StatelessWidget {
  final String provider, orgName;
  const _OidcConsentCard({super.key, required this.provider, required this.orgName});
  @override
  Widget build(BuildContext context) => _AuthCard(child: Column(children: [
    const SizedBox(height: 8),
    Container(width: 48, height: 48, decoration: const BoxDecoration(color: AppColors.accentMuted, shape: BoxShape.circle), child: const Icon(Icons.shield_outlined, color: AppColors.accent, size: 24)),
    const SizedBox(height: 16),
    Text('Redirecting to $provider', style: AppTextStyles.h2, textAlign: TextAlign.center),
    const SizedBox(height: 8),
    Text('Requesting consent from your identity provider...', style: AppTextStyles.caption, textAlign: TextAlign.center),
    const SizedBox(height: 20),
    const SizedBox(width: 28, height: 28, child: CircularProgressIndicator(color: AppColors.accent, strokeWidth: 2)),
    const SizedBox(height: 8),
  ]));
}

class _OidcTokenExchangeCard extends StatelessWidget {
  final String provider; final int dotCount;
  const _OidcTokenExchangeCard({super.key, required this.provider, required this.dotCount});
  @override
  Widget build(BuildContext context) => _AuthCard(maxWidth: 480, child: Column(children: [
    const SizedBox(height: 8), const _PulsingDot(color: AppColors.live, size: 10), const SizedBox(height: 16),
    Text('Exchanging tokens...', style: AppTextStyles.body.copyWith(color: AppColors.textSecondary)),
    const SizedBox(height: 6),
    Text('Verifying claims from $provider', style: AppTextStyles.mono(fontSize: 11, color: AppColors.textSecondary)),
    const SizedBox(height: 8),
  ]));
}

class _DeniedCard extends StatelessWidget {
  final String reason; final VoidCallback onRetry;
  const _DeniedCard({super.key, required this.reason, required this.onRetry});
  @override
  Widget build(BuildContext context) => _AuthCard(child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Row(children: [Container(width: 36, height: 36, decoration: const BoxDecoration(color: AppColors.errorBg, shape: BoxShape.circle), child: const Icon(Icons.block_outlined, size: 18, color: AppColors.error)), const SizedBox(width: 12), Text('Access denied', style: AppTextStyles.h2.copyWith(color: AppColors.error))]),
    const SizedBox(height: 16),
    Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: AppColors.errorBg, border: Border.all(color: AppColors.errorBorder), borderRadius: BorderRadius.circular(8)), child: Text(reason, style: AppTextStyles.body.copyWith(color: AppColors.error, height: 1.5))),
    const SizedBox(height: 20),
    _OidcButton(label: 'Try a different account', enabled: true, filled: true, onPressed: onRetry),
  ]));
}

class _OidcTextField extends StatelessWidget {
  final TextEditingController controller;
  final String hint;
  final TextInputType? keyboardType;
  final bool obscureText;
  final Widget? suffixIcon;
  const _OidcTextField({required this.controller, required this.hint, this.keyboardType, this.obscureText = false, this.suffixIcon});
  @override
  Widget build(BuildContext context) => TextField(
    controller: controller, keyboardType: keyboardType, obscureText: obscureText,
    style: AppTextStyles.bodyMd, cursorColor: AppColors.accent,
    decoration: InputDecoration(hintText: hint, hintStyle: AppTextStyles.bodyMd.copyWith(color: AppColors.textMuted), filled: true, fillColor: AppColors.bgSurface, suffixIcon: suffixIcon,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppColors.divider)),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppColors.divider)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: AppColors.accent)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10)),
  );
}

class _OidcButton extends StatelessWidget {
  final String label; final bool enabled, filled; final VoidCallback onPressed;
  const _OidcButton({required this.label, required this.enabled, required this.filled, required this.onPressed});
  @override
  Widget build(BuildContext context) => GestureDetector(onTap: enabled ? onPressed : null, child: AnimatedContainer(
    duration: const Duration(milliseconds: 150), height: 40,
    decoration: BoxDecoration(color: filled ? (enabled ? AppColors.accent : AppColors.accent.withValues(alpha: 0.25)) : Colors.transparent, border: filled ? null : Border.all(color: AppColors.divider), borderRadius: BorderRadius.circular(9)),
    alignment: Alignment.center,
    child: Text(label, style: AppTextStyles.inter(fontSize: 14, fontWeight: FontWeight.w600, color: filled ? (enabled ? const Color(0xFF0D0A08) : AppColors.textSecondary) : AppColors.textPrimary)),
  ));
}

class _ProviderButton extends StatelessWidget {
  final String label; final IconData icon; final VoidCallback onPressed;
  const _ProviderButton({required this.label, required this.icon, required this.onPressed});
  @override
  Widget build(BuildContext context) => GestureDetector(onTap: onPressed, child: Container(
    height: 40,
    padding: const EdgeInsets.symmetric(horizontal: 12),
    decoration: BoxDecoration(color: AppColors.bgSurface, border: Border.all(color: AppColors.divider), borderRadius: BorderRadius.circular(9)),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(icon, size: 17, color: AppColors.textSecondary),
        const SizedBox(width: 9),
        Flexible(
          child: Text(
            label,
            style: AppTextStyles.inter(fontSize: 13, fontWeight: FontWeight.w500, color: AppColors.textPrimary),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    ),
  ));
}
