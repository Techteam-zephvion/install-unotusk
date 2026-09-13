import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../target/domain/target_config.dart';
import '../../target/presentation/target_controller.dart';
import '../data/environment_validator.dart';
import '../domain/check_item.dart';

final environmentValidatorProvider = Provider<EnvironmentValidator>((ref) {
  return EnvironmentValidator();
});

class ServerCheckState {
  final List<CheckItem> items;
  final bool isRunning;
  final bool hasCriticalFailure;

  const ServerCheckState({
    this.items = const [],
    this.isRunning = false,
    this.hasCriticalFailure = false,
  });

  bool get isAllPassed =>
      items.isNotEmpty &&
      !isRunning &&
      items.every((item) => item.status == CheckStatus.passed || item.status == CheckStatus.warning);

  ServerCheckState copyWith({
    List<CheckItem>? items,
    bool? isRunning,
    bool? hasCriticalFailure,
  }) {
    return ServerCheckState(
      items: items ?? this.items,
      isRunning: isRunning ?? this.isRunning,
      hasCriticalFailure: hasCriticalFailure ?? this.hasCriticalFailure,
    );
  }
}

class ServerCheckController extends StateNotifier<ServerCheckState> {
  final EnvironmentValidator validator;
  final TargetConfig targetConfig;

  ServerCheckController({
    required this.validator,
    required this.targetConfig,
  }) : super(const ServerCheckState()) {
    runChecks();
  }

  Future<void> runChecks() async {
    state = state.copyWith(
      isRunning: true,
      hasCriticalFailure: false,
      items: [
        const CheckItem(
          id: 'reachability',
          title: 'Machine reachable',
          description: 'Testing connection to target host...',
          status: CheckStatus.checking,
        ),
        const CheckItem(
          id: 'docker_runtime',
          title: 'Required runtime available',
          description: 'Verifying Docker engine status...',
          status: CheckStatus.pending,
        ),
        const CheckItem(
          id: 'docker_compose',
          title: 'Docker Compose available',
          description: 'Verifying Docker Compose v2...',
          status: CheckStatus.pending,
        ),
        const CheckItem(
          id: 'storage_space',
          title: 'Storage available',
          description: 'Checking disk space...',
          status: CheckStatus.pending,
        ),
        const CheckItem(
          id: 'ports_available',
          title: 'Required ports available',
          description: 'Checking port availability...',
          status: CheckStatus.pending,
        ),
      ],
    );

    // 1. Reachability
    final reachability = await validator.checkReachability(targetConfig);
    _updateItem(reachability);
    if (reachability.status.isFailed) {
      state = state.copyWith(isRunning: false, hasCriticalFailure: true);
      return;
    }

    // 2. Docker Runtime
    _setItemStatus('docker_runtime', CheckStatus.checking);
    final docker = await validator.checkDockerRuntime(targetConfig);
    _updateItem(docker);
    if (docker.status.isFailed) {
      state = state.copyWith(isRunning: false, hasCriticalFailure: true);
      return;
    }

    // 3. Docker Compose
    _setItemStatus('docker_compose', CheckStatus.checking);
    final compose = await validator.checkDockerCompose(targetConfig);
    _updateItem(compose);
    if (compose.status.isFailed) {
      state = state.copyWith(isRunning: false, hasCriticalFailure: true);
      return;
    }

    // 4. Storage Space
    _setItemStatus('storage_space', CheckStatus.checking);
    final storage = await validator.checkStorageSpace(targetConfig);
    _updateItem(storage);

    // 5. Ports
    _setItemStatus('ports_available', CheckStatus.checking);
    final ports = await validator.checkPortsAvailable(targetConfig);
    _updateItem(ports);

    state = state.copyWith(
      isRunning: false,
      hasCriticalFailure: state.items.any((i) => i.status.isFailed),
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

final serverCheckControllerProvider =
    StateNotifierProvider.autoDispose<ServerCheckController, ServerCheckState>((ref) {
  final validator = ref.watch(environmentValidatorProvider);
  final targetState = ref.watch(targetControllerProvider);
  return ServerCheckController(
    validator: validator,
    targetConfig: targetState.config,
  );
});
