import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/presentation/config_controller.dart';
import '../../target/presentation/target_controller.dart';
import '../../manager/data/server_registry.dart';
import '../../manager/domain/server_instance.dart';
import '../data/deployment_engine.dart';

final deploymentEngineProvider = Provider<DeploymentEngine>((ref) {
  return DeploymentEngine();
});

class DeployState {
  final DeployStage currentStage;
  final bool isRunning;
  final bool isSuccess;
  final String? errorMessage;
  final String? technicalLogs;

  const DeployState({
    this.currentStage = DeployStage.idle,
    this.isRunning = false,
    this.isSuccess = false,
    this.errorMessage,
    this.technicalLogs,
  });

  DeployState copyWith({
    DeployStage? currentStage,
    bool? isRunning,
    bool? isSuccess,
    String? errorMessage,
    String? technicalLogs,
    bool clearErrors = false,
  }) {
    return DeployState(
      currentStage: currentStage ?? this.currentStage,
      isRunning: isRunning ?? this.isRunning,
      isSuccess: isSuccess ?? this.isSuccess,
      errorMessage: clearErrors ? null : (errorMessage ?? this.errorMessage),
      technicalLogs: clearErrors ? null : (technicalLogs ?? this.technicalLogs),
    );
  }
}

class DeployController extends StateNotifier<DeployState> {
  final DeploymentEngine deploymentEngine;
  final Ref ref;

  DeployController({
    required this.deploymentEngine,
    required this.ref,
  }) : super(const DeployState()) {
    startDeployment();
  }

  Future<void> startDeployment() async {
    final target = ref.read(targetControllerProvider).config;
    final config = ref.read(configControllerProvider).config;
    final serverRegistry = ServerRegistry();
    final deployDir = '${Platform.environment['HOME'] ?? ''}/.unotusk/servers/${config.serverName}';

    state = state.copyWith(
      isRunning: true,
      isSuccess: false,
      clearErrors: true,
      currentStage: DeployStage.preparing,
    );

    final result = await deploymentEngine.deploy(
      target: target,
      config: config,
      customDeploymentDir: deployDir,
      onStageChanged: (stage) {
        state = state.copyWith(currentStage: stage);
      },
    );

    if (result.isSuccess) {
      // Save metadata
      final instance = ServerInstance(
        id: config.serverName,
        name: config.serverName,
        composeProject: config.serverName,
        deploymentDir: deployDir,
        apiPort: config.serverPort,
        lanIp: config.lanIp,
        createdAt: DateTime.now(),
        lastKnownState: ServerState.running,
      );
      await serverRegistry.saveServer(instance);

      state = state.copyWith(
        isRunning: false,
        isSuccess: true,
        currentStage: DeployStage.completed,
      );
    } else {
      state = state.copyWith(
        isRunning: false,
        isSuccess: false,
        currentStage: DeployStage.failed,
        errorMessage: result.errorMessage,
        technicalLogs: result.technicalLogs,
      );
    }
  }
}

final deployControllerProvider =
    StateNotifierProvider.autoDispose<DeployController, DeployState>((ref) {
  final engine = ref.watch(deploymentEngineProvider);
  return DeployController(
    deploymentEngine: engine,
    ref: ref,
  );
});
