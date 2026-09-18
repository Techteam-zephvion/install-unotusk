import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/lan_detector.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
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
    final serverConfig = ref.watch(configControllerProvider).config;
    final serverUrl = serverConfig.serverUrl;
    final isLanDetected = serverConfig.lanIp != null &&
        serverConfig.lanIp!.isNotEmpty &&
        serverConfig.lanIp != 'localhost' &&
        serverConfig.lanIp != '127.0.0.1';

    final availableAddressesAsync = ref.watch(availableLanAddressesProvider);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 540),
        child: AppCard(
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 36),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.successBg,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.successBorder),
                ),
                child: const Center(
                  child: Icon(Icons.check, color: AppColors.success, size: 20),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'Unotusk is ready.',
                style: AppTextStyles.h1.copyWith(fontSize: 22),
              ),
              const SizedBox(height: 6),
              Text(
                'Your Unotusk Server is operational and ready to accept employee connections over your Local Area Network (LAN).',
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      isLanDetected ? 'LAN Server URL (Employee Clients)' : 'Server URL',
                      style: AppTextStyles.label,
                    ),
                  ),
                  if (isLanDetected)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'LAN REACHABLE',
                        style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w600,
                          fontSize: 10,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: AppColors.slate50,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.slate200),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: SelectableText(
                        serverUrl,
                        style: AppTextStyles.code.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    AppButton(
                      label: _copied ? 'Copied' : 'Copy',
                      variant: AppButtonVariant.secondary,
                      icon: _copied ? Icons.check : Icons.copy,
                      onPressed: () => _copyUrl(serverUrl),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Text(
                isLanDetected
                    ? 'Share this LAN URL with Windows and macOS laptops connected to the same Wi-Fi / network.'
                    : 'Configure the Employee App to connect to this server address.',
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
              ),
              if (isLanDetected) ...[
                const SizedBox(height: 12),
                Row(
                  children: [
                    Text(
                      'Local host address: ',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate600),
                    ),
                    Expanded(
                      child: SelectableText(
                        serverConfig.localUrl,
                        style: AppTextStyles.code.copyWith(fontSize: 12, color: AppColors.slate700),
                      ),
                    ),
                    InkWell(
                      onTap: () => _copyUrl(serverConfig.localUrl, isLocal: true),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                        child: Text(
                          _copiedLocal ? 'Copied' : 'Copy Local',
                          style: AppTextStyles.bodySmall.copyWith(
                            color: AppColors.primary,
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
                      padding: const EdgeInsets.only(top: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Available Interfaces:', style: AppTextStyles.label.copyWith(fontSize: 11)),
                          const SizedBox(height: 6),
                          Wrap(
                            spacing: 8,
                            runSpacing: 4,
                            children: addresses.map((addr) {
                              final isSelected = serverConfig.lanIp == addr.ip;
                              return ChoiceChip(
                                label: Text('${addr.ip} (${addr.interfaceName})'),
                                selected: isSelected,
                                onSelected: (selected) {
                                  if (selected) {
                                    ref.read(configControllerProvider.notifier).updateLanIp(addr.ip);
                                  }
                                },
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
              Row(
                children: [
                  Expanded(
                    child: AppButton(
                      label: 'Open Employee App',
                      icon: Icons.launch,
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
    );
  }
}
