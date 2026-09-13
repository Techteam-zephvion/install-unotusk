import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/target/domain/target_config.dart';
import 'package:setup_app/features/validation/data/environment_validator.dart';

void main() {
  group('EnvironmentValidator Unit Tests', () {
    test('checkReachability succeeds for local target', () async {
      final validator = EnvironmentValidator();
      final res = await validator.checkReachability(const TargetConfig(type: TargetType.local));
      expect(res.status.isPassed, true);
    });

    test('checkDockerRuntime passes when docker returns 0 exitCode', () async {
      final validator = EnvironmentValidator(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          return ProcessResult(1234, 0, 'Docker version 27.0.0', '');
        },
      );

      final res = await validator.checkDockerRuntime(const TargetConfig(type: TargetType.local));
      expect(res.status.isPassed, true);
    });

    test('checkDockerRuntime fails with remediation hint when docker returns error', () async {
      final validator = EnvironmentValidator(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          return ProcessResult(1234, 1, '', 'Cannot connect to Docker daemon');
        },
      );

      final res = await validator.checkDockerRuntime(const TargetConfig(type: TargetType.local));
      expect(res.status.isFailed, true);
      expect(res.failureMessage, contains('Docker is not running'));
      expect(res.remediationHint, contains('Docker Engine / Docker Desktop'));
    });

    test('checkDockerCompose passes when compose version returns 0', () async {
      final validator = EnvironmentValidator(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          return ProcessResult(1234, 0, 'Docker Compose version v2.28.1', '');
        },
      );

      final res = await validator.checkDockerCompose(const TargetConfig(type: TargetType.local));
      expect(res.status.isPassed, true);
    });

    test('checkPortsAvailable detects free port', () async {
      final validator = EnvironmentValidator(
        socketTester: (host, port) async => true,
      );

      final res = await validator.checkPortsAvailable(const TargetConfig(type: TargetType.local));
      expect(res.status.isPassed, true);
    });
  });
}
