import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/network/lan_detector.dart';
import '../../../core/theme/app_fonts.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/status_badge.dart';
import '../../config/presentation/config_controller.dart';
import '../../manager/data/server_manager_controller.dart';
import '../data/app_launcher.dart';

final appLauncherProvider = Provider<AppLauncher>((ref) {
  return AppLauncher();
});

class ReadyScreen extends ConsumerStatefulWidget {
  const ReadyScreen({super.key});

  @override
  ConsumerState<ReadyScreen> createState() => _ReadyScreenState();
}

class _ReadyScreenState extends ConsumerState<ReadyScreen> {
  bool _copied = false;
  bool _copiedLocal = false;
  bool _launching = false;
  bool _isReturning = false;
  bool _isRedirectPaused = false;
  int _countdown = 4;
  Timer? _countdownTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      // Refresh server fleet immediately in background
      try {
        ref.read(serverManagerProvider.notifier).loadServers();
      } catch (_) {}

      final config = ref.read(configControllerProvider).config;
      if (config.lanIp == null || config.lanIp!.isEmpty) {
        final detector = ref.read(lanDetectorProvider);
        final primaryIp = await detector.getPrimaryLanIp();
        if (mounted && primaryIp != 'localhost') {
          ref.read(configControllerProvider.notifier).updateLanIp(primaryIp);
        }
      }

      _startAutoRedirectTimer();
    });
  }

  void _startAutoRedirectTimer() {
    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_isRedirectPaused || _isReturning) return;

      setState(() {
        if (_countdown > 1) {
          _countdown--;
        } else {
          _countdown = 0;
          timer.cancel();
          _returnToDashboard();
        }
      });
    });
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    super.dispose();
  }

  Future<void> _returnToDashboard() async {
    if (_isReturning) return;
    setState(() => _isReturning = true);
    _countdownTimer?.cancel();

    // Reload servers to ensure all data planes are visible
    try {
      await ref.read(serverManagerProvider.notifier).loadServers();
    } catch (_) {}

    if (!mounted) return;
    if (Navigator.of(context).canPop()) {
      Navigator.of(context).popUntil((route) => route.isFirst);
    } else {
      context.go('/');
    }
  }

  Future<void> _copyUrl(String url, {bool isLocal = false}) async {
    // Pause auto redirect so user has time to use the copied URL
    setState(() {
      _isRedirectPaused = true;
      if (isLocal) {
        _copiedLocal = true;
      } else {
        _copied = true;
      }
    });
    try {
      await Clipboard.setData(ClipboardData(text: url));
    } catch (_) {}
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        setState(() {
          if (isLocal) {
            _copiedLocal = false;
          } else {
            _copied = false;
          }
        });
      }
    });
  }

  Future<void> _launchApp(String serverUrl) async {
    setState(() {
      _launching = true;
      _isRedirectPaused = true;
    });
    final launcher = ref.read(appLauncherProvider);
    await launcher.launchEmployeeApp(serverUrl: serverUrl);
    if (mounted) setState(() => _launching = false);
  }

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);
    final serverConfig = ref.watch(configControllerProvider).config;
    final serverUrl = serverConfig.serverUrl;
    final isLanDetected = serverConfig.lanIp != null &&
        serverConfig.lanIp!.isNotEmpty &&
        serverConfig.lanIp != 'localhost' &&
        serverConfig.lanIp != '127.0.0.1';

    final availableAddressesAsync = ref.watch(availableLanAddressesProvider);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: AppCard(
            borderRadius: BorderRadius.circular(20),
            padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 40),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: palette.live.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: palette.live.withValues(alpha: 0.4)),
                      ),
                      child: Center(
                        child: Icon(Icons.check_rounded, color: palette.live, size: 24),
                      ),
                    ),
                    const StatusBadge.pill(
                      label: 'Online & Serving',
                      icon: Icons.check_circle_rounded,
                      type: StatusType.success,
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Text(
                  'Unotusk Data Plane Ready',
                  style: AppFonts.display(
                    fontSize: 32,
                    color: palette.text,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Your isolated project server is running and ready to accept employee client connections.',
                  style: AppFonts.body(
                    color: palette.textSec,
                    fontSize: 13.5,
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        isLanDetected ? 'LAN Endpoint (Employee Client Connect)' : 'Server Endpoint',
                        style: AppFonts.body(
                          color: palette.text,
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                    if (isLanDetected)
                      StatusBadge(
                        label: 'LAN REACHABLE',
                        type: StatusType.accent,
                        icon: Icons.wifi_rounded,
                      ),
                  ],
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                    color: palette.bgElevated,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: palette.div),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.link_rounded, size: 18, color: palette.accent),
                      const SizedBox(width: 10),
                      Expanded(
                        child: SelectableText(
                          serverUrl,
                          style: AppFonts.mono(
                            color: palette.accent,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      AppButton(
                        label: _copied ? 'Copied' : 'Copy',
                        variant: AppButtonVariant.secondary,
                        icon: _copied ? Icons.check_rounded : Icons.copy_rounded,
                        onPressed: () => _copyUrl(serverUrl),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  isLanDetected
                      ? 'Share this LAN URL with colleagues to connect from their laptops.'
                      : 'Configure the Employee App to connect to this server address.',
                  style: AppFonts.body(
                    color: palette.textSec,
                    fontSize: 12,
                  ),
                ),
                if (isLanDetected) ...[
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Text(
                        'Local host address: ',
                        style: AppFonts.body(color: palette.textSec, fontSize: 12),
                      ),
                      Expanded(
                        child: SelectableText(
                          serverConfig.localUrl,
                          style: AppFonts.mono(
                            color: palette.text,
                            fontSize: 12,
                          ),
                        ),
                      ),
                      InkWell(
                        onTap: () => _copyUrl(serverConfig.localUrl, isLocal: true),
                        borderRadius: BorderRadius.circular(6),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          child: Text(
                            _copiedLocal ? 'Copied' : 'Copy Local',
                            style: AppFonts.body(
                              color: palette.accent,
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
                availableAddressesAsync.when(
                  data: (addresses) {
                    if (addresses.length > 1) {
                      return Padding(
                        padding: const EdgeInsets.only(top: 16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Available Network Interfaces:',
                              style: AppFonts.body(fontSize: 11.5, color: palette.textSec),
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: addresses.map((addr) {
                                final isSelected = serverConfig.lanIp == addr.ip;
                                return InkWell(
                                  onTap: () {
                                    ref.read(configControllerProvider.notifier).updateLanIp(addr.ip);
                                  },
                                  borderRadius: BorderRadius.circular(8),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                                    decoration: BoxDecoration(
                                      color: isSelected
                                          ? palette.accent.withValues(alpha: 0.15)
                                          : palette.bgElevated,
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: isSelected ? palette.accent : palette.div,
                                      ),
                                    ),
                                    child: Text(
                                      '${addr.ip} (${addr.interfaceName})',
                                      style: AppFonts.mono(
                                        color: isSelected ? palette.accent : palette.textSec,
                                        fontSize: 11,
                                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                                      ),
                                    ),
                                  ),
                                );
                              }).toList(),
                            ),
                          ],
                        ),
                      );
                    }
                    return const SizedBox.shrink();
                  },
                  loading: () => const SizedBox.shrink(),
                  error: (_, _) => const SizedBox.shrink(),
                ),
                const SizedBox(height: 24),
                // Auto-redirect status banner
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: palette.live.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: palette.live.withValues(alpha: 0.35)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle_rounded, color: palette.live, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _isRedirectPaused
                              ? 'Auto-redirect paused. Return whenever you are ready.'
                              : 'Deployment verified! Returning to Server Fleet in ${_countdown}s...',
                          style: AppFonts.body(
                            color: palette.text,
                            fontSize: 12.5,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      InkWell(
                        onTap: () {
                          setState(() {
                            if (_isRedirectPaused) {
                              _isRedirectPaused = false;
                              _countdown = 4;
                              _startAutoRedirectTimer();
                            } else {
                              _isRedirectPaused = true;
                            }
                          });
                        },
                        borderRadius: BorderRadius.circular(6),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          child: Text(
                            _isRedirectPaused ? 'Resume' : 'Pause',
                            style: AppFonts.body(
                              color: palette.accent,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                Divider(color: palette.div),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: AppButton(
                        label: 'Return to Server Dashboard',
                        icon: Icons.dashboard_rounded,
                        isLoading: _isReturning,
                        onPressed: _returnToDashboard,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 2,
                      child: AppButton(
                        label: 'Launch Client',
                        variant: AppButtonVariant.secondary,
                        icon: Icons.launch_rounded,
                        isLoading: _launching,
                        onPressed: () => _launchApp(serverUrl),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
