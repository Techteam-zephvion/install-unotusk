import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/lan_detector.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/status_badge.dart';
import '../../config/presentation/config_controller.dart';
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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final config = ref.read(configControllerProvider).config;
      if (config.lanIp == null || config.lanIp!.isEmpty) {
        final detector = ref.read(lanDetectorProvider);
        final primaryIp = await detector.getPrimaryLanIp();
        if (mounted && primaryIp != 'localhost') {
          ref.read(configControllerProvider.notifier).updateLanIp(primaryIp);
        }
      }
    });
  }

  Future<void> _copyUrl(String url, {bool isLocal = false}) async {
    setState(() {
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
    setState(() => _launching = true);
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
                  'Unotusk is ready.',
                  style: UnoTypography.brandSerif(
                    palette: palette,
                    fontSize: 22,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Your Unotusk Server is operational and ready to accept employee connections over your Local Area Network (LAN).',
                  style: AppTextStyles.bodyMediumOf(context).copyWith(
                    color: palette.textSec,
                    fontSize: 13.5,
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        isLanDetected ? 'LAN Server URL (Employee Clients)' : 'Server URL',
                        style: AppTextStyles.labelOf(context).copyWith(
                          color: palette.text,
                          fontWeight: FontWeight.w600,
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
                          style: UnoTypography.mono(
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
                      ? 'Share this LAN URL with Windows and macOS laptops connected to the same Wi-Fi / network.'
                      : 'Configure the Employee App to connect to this server address.',
                  style: AppTextStyles.bodySmallOf(context).copyWith(
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
                        style: AppTextStyles.bodySmallOf(context).copyWith(color: palette.textSec),
                      ),
                      Expanded(
                        child: SelectableText(
                          serverConfig.localUrl,
                          style: UnoTypography.mono(
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
                            style: AppTextStyles.bodySmallOf(context).copyWith(
                              color: palette.accent,
                              fontWeight: FontWeight.w600,
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
                              style: AppTextStyles.labelOf(context).copyWith(fontSize: 11.5),
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
                                      style: UnoTypography.mono(
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
                const SizedBox(height: 28),
                Divider(color: palette.div),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: AppButton(
                        label: 'Open Employee App',
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
