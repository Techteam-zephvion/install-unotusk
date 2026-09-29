import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../target/domain/target_config.dart';
import '../../target/presentation/target_controller.dart';
import '../../validation/domain/check_item.dart';
import '../data/network_validator.dart';

final networkValidatorProvider = Provider<NetworkValidator>((ref) {
  return NetworkValidator();
});

class NetworkCheckState {
  final List<CheckItem> items;
  final bool isRunning;
  final bool hasCriticalFailure;
  final String? detectedIp;
  final int? availablePort;

  const NetworkCheckState({
    this.items = const [],
    this.isRunning = false,
    this.hasCriticalFailure = false,
    this.detectedIp,
    this.availablePort,
  });

  bool get isAllPassed =>
      items.isNotEmpty &&
      !isRunning &&
      items.every((item) => item.status == CheckStatus.passed || item.status == CheckStatus.warning);

  NetworkCheckState copyWith({
    List<CheckItem>? items,
    bool? isRunning,
    bool? hasCriticalFailure,
    String? detectedIp,
    int? availablePort,
  }) {
    return NetworkCheckState(
      items: items ?? this.items,
      isRunning: isRunning ?? this.isRunning,
      hasCriticalFailure: hasCriticalFailure ?? this.hasCriticalFailure,
      detectedIp: detectedIp ?? this.detectedIp,
      availablePort: availablePort ?? this.availablePort,
    );
  }
}

class NetworkCheckController extends StateNotifier<NetworkCheckState> {
  final NetworkValidator validator;
  final TargetConfig targetConfig;

  NetworkCheckController({
    required this.validator,
    required this.targetConfig,
  }) : super(const NetworkCheckState()) {
    runChecks();
  }

  Future<void> runChecks() async {
    state = state.copyWith(
      isRunning: true,
      hasCriticalFailure: false,
      items: [
        const CheckItem(
          id: 'lan_ip',
          title: 'LAN IPv4 Address',
          description: 'Detecting LAN IP address...',
          status: CheckStatus.checking,
        ),
        const CheckItem(
          id: 'firewall',
          title: 'Firewall Configuration',
          description: 'Checking firewall rules...',
          status: CheckStatus.pending,
        ),
      ],
    );

    
    // 0. Find Available Port
    final port = await validator.findAvailablePort(targetConfig, 8000);
    
    // 1. LAN IP
    final ipCheck = await validator.checkLanIp(targetConfig);
    _updateItem(ipCheck);
    
    String? detectedIp;
    if (ipCheck.status == CheckStatus.passed) {
      detectedIp = ipCheck.technicalDetails;
    }

    if (ipCheck.status.isFailed) {
      state = state.copyWith(isRunning: false, hasCriticalFailure: true, detectedIp: detectedIp,
      availablePort: port);
      return;
    }

    // 2. Firewall
    _setItemStatus('firewall', CheckStatus.checking);
    final fwCheck = await validator.checkFirewall(targetConfig, apiPort: port);
    _updateItem(fwCheck);

    if (fwCheck.status.isFailed) {
      state = state.copyWith(isRunning: false, hasCriticalFailure: true, detectedIp: detectedIp,
      availablePort: port);
      return;
    }

    state = state.copyWith(
      isRunning: false,
      hasCriticalFailure: false,
      detectedIp: detectedIp,
      availablePort: port,
    );
  }

  void _setItemStatus(String id, CheckStatus status) {
    state = state.copyWith(
      items: state.items.map((item) {
        if (item.id == id) {
          return item.copyWith(status: status);
        }
        return item;
      }).toList(),
    );
  }

  void _updateItem(CheckItem updated) {
    state = state.copyWith(
      items: state.items.map((item) {
        if (item.id == updated.id) {
          return updated;
        }
        return item;
      }).toList(),
    );
  }
}

final networkCheckControllerProvider =
    StateNotifierProvider.autoDispose<NetworkCheckController, NetworkCheckState>((ref) {
  final validator = ref.watch(networkValidatorProvider);
  final targetState = ref.watch(targetControllerProvider);
  return NetworkCheckController(
    validator: validator,
    targetConfig: targetState.config,
  );
});
