import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/presentation/config_controller.dart';
import '../../network/presentation/network_check_controller.dart';
import '../data/health_verifier.dart';

final healthVerifierProvider = Provider<HealthVerifier>((ref) {
  return HealthVerifier();
});

class VerifyState {
  final bool isVerifying;
  final bool isSuccess;
  final HealthStatus? healthStatus;
  final int attemptCount;
  final String? errorMessage;

  final String? lanServerUrl;
  final bool isLocalHealthy;
  final bool isLanHealthy;

  const VerifyState({
    this.isVerifying = false,
    this.isSuccess = false,
    this.healthStatus,
    this.attemptCount = 0,
    this.errorMessage,
    this.lanServerUrl,
    this.isLocalHealthy = false,
    this.isLanHealthy = false,
  });

  VerifyState copyWith({
    bool? isVerifying,
    bool? isSuccess,
    HealthStatus? healthStatus,
    int? attemptCount,
    String? errorMessage,
    bool clearErrors = false,
    String? lanServerUrl,
    bool? isLocalHealthy,
    bool? isLanHealthy,
  }) {
    return VerifyState(
      isVerifying: isVerifying ?? this.isVerifying,
      isSuccess: isSuccess ?? this.isSuccess,
      healthStatus: healthStatus ?? this.healthStatus,
      attemptCount: attemptCount ?? this.attemptCount,
      errorMessage: clearErrors ? null : (errorMessage ?? this.errorMessage),
      lanServerUrl: lanServerUrl ?? this.lanServerUrl,
      isLocalHealthy: isLocalHealthy ?? this.isLocalHealthy,
      isLanHealthy: isLanHealthy ?? this.isLanHealthy,
    );
  }
}

class VerifyController extends StateNotifier<VerifyState> {
  final HealthVerifier healthVerifier;
  final Ref ref;

  VerifyController({
    required this.healthVerifier,
    required this.ref,
  }) : super(const VerifyState()) {
    verifyServer();
  }

  Future<void> verifyServer() async {
    final serverUrl = ref.read(configControllerProvider).config.serverUrl;
    
    // Import dynamically or pass IP via provider
    final networkState = ref.read(networkCheckControllerProvider);
    String? lanUrl;
    if (networkState.detectedIp != null && networkState.detectedIp!.isNotEmpty) {
      final port = ref.read(configControllerProvider).config.serverPort;
      lanUrl = 'http://${networkState.detectedIp}:$port';
    }

    state = state.copyWith(
      isVerifying: true,
      isSuccess: false,
      clearErrors: true,
      attemptCount: 0,
      lanServerUrl: lanUrl,
      isLocalHealthy: false,
      isLanHealthy: false,
    );

    HealthStatus? lastStatus;
    bool localOk = false;
    bool lanOk = false;
    
    for (int attempt = 1; attempt <= 30; attempt++) {
      if (!localOk) {
        final localStatus = await healthVerifier.checkHealth(serverUrl);
        localOk = localStatus.isReady;
        lastStatus = localStatus;
      }
      
      if (lanUrl != null && !lanOk) {
        final lanStatus = await healthVerifier.checkHealth(lanUrl);
        lanOk = lanStatus.isReady;
      } else if (lanUrl == null) {
        lanOk = true; // Skip if no LAN IP detected
      }
      
      state = state.copyWith(
        attemptCount: attempt,
        healthStatus: lastStatus,
        isLocalHealthy: localOk,
        isLanHealthy: lanOk,
      );
      
      if (localOk && lanOk) {
        break;
      }
      await Future.delayed(const Duration(seconds: 1));
    }

    if (localOk && lanOk) {
      state = state.copyWith(
        isVerifying: false,
        isSuccess: true,
        healthStatus: lastStatus,
      );
    } else {
      state = state.copyWith(
        isVerifying: false,
        isSuccess: false,
        healthStatus: lastStatus,
        errorMessage: lastStatus?.errorMessage ?? 'Server startup timed out or LAN blocked.',
      );
    }
  }
}

final verifyControllerProvider =
    StateNotifierProvider.autoDispose<VerifyController, VerifyState>((ref) {
  final verifier = ref.watch(healthVerifierProvider);
  return VerifyController(
    healthVerifier: verifier,
    ref: ref,
  );
});
