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
    final config = ref.read(configControllerProvider).config;
    final localUrl = 'http://localhost:${config.serverPort}';
    final detectedLanIp = config.lanIp ?? ref.read(networkCheckControllerProvider).detectedIp;
    final String? lanUrl = (detectedLanIp != null &&
            detectedLanIp.isNotEmpty &&
            detectedLanIp != '127.0.0.1' &&
            detectedLanIp != 'localhost')
        ? 'http://$detectedLanIp:${config.serverPort}'
        : null;

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

    // Up to 45 attempts (allows ample time for initial postgres initdb + alembic migrations)
    for (int attempt = 1; attempt <= 45; attempt++) {
      if (!localOk) {
        final localStatus = await healthVerifier.checkHealth(localUrl);
        localOk = localStatus.isReady;
        lastStatus = localStatus;
      }

      if (lanUrl != null && !lanOk) {
        final lanStatus = await healthVerifier.checkHealth(lanUrl);
        lanOk = lanStatus.isReady;
      } else if (lanUrl == null) {
        lanOk = true; // Skip if no LAN IP
      }

      state = state.copyWith(
        attemptCount: attempt,
        healthStatus: lastStatus,
        isLocalHealthy: localOk,
        isLanHealthy: lanOk,
      );

      // Once local health check succeeds and (LAN check succeeds OR attempted at least 15 times)
      if (localOk && (lanOk || attempt >= 15)) {
        break;
      }
      await Future.delayed(const Duration(seconds: 1));
    }

    if (localOk) {
      state = state.copyWith(
        isVerifying: false,
        isSuccess: true,
        healthStatus: lastStatus,
        errorMessage: null,
      );
    } else {
      state = state.copyWith(
        isVerifying: false,
        isSuccess: false,
        healthStatus: lastStatus,
        errorMessage: lastStatus?.errorMessage ??
            'Server startup timed out after waiting for database and API to become ready.',
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
