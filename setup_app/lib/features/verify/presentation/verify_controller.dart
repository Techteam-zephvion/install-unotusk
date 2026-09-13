import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../config/presentation/config_controller.dart';
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

  const VerifyState({
    this.isVerifying = false,
    this.isSuccess = false,
    this.healthStatus,
    this.attemptCount = 0,
    this.errorMessage,
  });

  VerifyState copyWith({
    bool? isVerifying,
    bool? isSuccess,
    HealthStatus? healthStatus,
    int? attemptCount,
    String? errorMessage,
    bool clearErrors = false,
  }) {
    return VerifyState(
      isVerifying: isVerifying ?? this.isVerifying,
      isSuccess: isSuccess ?? this.isSuccess,
      healthStatus: healthStatus ?? this.healthStatus,
      attemptCount: attemptCount ?? this.attemptCount,
      errorMessage: clearErrors ? null : (errorMessage ?? this.errorMessage),
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

    state = state.copyWith(
      isVerifying: true,
      isSuccess: false,
      clearErrors: true,
      attemptCount: 0,
    );

    final result = await healthVerifier.pollUntilReady(
      serverUrl,
      maxAttempts: 15,
      interval: const Duration(seconds: 1),
      onPoll: (attempt, status) {
        state = state.copyWith(
          attemptCount: attempt,
          healthStatus: status,
        );
      },
    );

    if (result.isReady) {
      state = state.copyWith(
        isVerifying: false,
        isSuccess: true,
        healthStatus: result,
      );
    } else {
      state = state.copyWith(
        isVerifying: false,
        isSuccess: false,
        healthStatus: result,
        errorMessage: result.errorMessage ?? 'Server is not responding.',
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
