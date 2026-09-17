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

    test('checkPortsAvailable detects free port and passes', () async {
      final validator = EnvironmentValidator(
        socketTester: (host, port) async => true,
      );

      final res = await validator.checkPortsAvailable(const TargetConfig(type: TargetType.local));
      expect(res.status.isPassed, true);
      expect(res.description, contains('Port 8000 is open and available'));
    });

    test('checkPortsAvailable detects occupied port and returns failed status with clear message', () async {
      final validator = EnvironmentValidator(
        socketTester: (host, port) async => false,
        httpHealthChecker: (host, port) async => false,
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          return ProcessResult(1234, 1, '', '');
        },
      );

      final res = await validator.checkPortsAvailable(const TargetConfig(type: TargetType.local), apiPort: 8000);
      expect(res.status.isFailed, true);
      expect(res.failureMessage, 'Port 8000 is already in use.');
      expect(res.description, contains('Port 8000 is already in use by an unknown process.'));
    });

    test('checkPortsAvailable detects Docker container occupying port', () async {
      final validator = EnvironmentValidator(
        socketTester: (host, port) async => false,
        httpHealthChecker: (host, port) async => false,
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          if (exec == 'docker' && args.contains('ps')) {
            return ProcessResult(1234, 0, 'legacy-web-app\t0.0.0.0:8000->80/tcp\n', '');
          }
          return ProcessResult(1234, 1, '', '');
        },
      );

      final res = await validator.checkPortsAvailable(const TargetConfig(type: TargetType.local), apiPort: 8000);
      expect(res.status.isFailed, true);
      expect(res.failureMessage, 'Port 8000 is already in use.');
      expect(res.description, contains('Port 8000 is already in use by Docker container (legacy-web-app).'));
      expect(res.technicalDetails, 'legacy-web-app');
    });

    test('checkPortsAvailable detects local process occupying port', () async {
      final validator = EnvironmentValidator(
        socketTester: (host, port) async => false,
        httpHealthChecker: (host, port) async => false,
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          if (exec == 'lsof') {
            return ProcessResult(1234, 0, 'COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME\npython3 98765 devils    3u  IPv4 123456      0t0  TCP *:8000 (LISTEN)\n', '');
          }
          return ProcessResult(1234, 1, '', '');
        },
      );

      final res = await validator.checkPortsAvailable(const TargetConfig(type: TargetType.local), apiPort: 8000);
      expect(res.status.isFailed, true);
      expect(res.failureMessage, 'Port 8000 is already in use.');
      expect(res.description, contains('Port 8000 is already in use by local process (python3 (PID 98765)).'));
    });

    test('checkPortsAvailable detects existing active Unotusk deployment', () async {
      final validator = EnvironmentValidator(
        socketTester: (host, port) async => false,
        httpHealthChecker: (host, port) async => true,
      );

      final res = await validator.checkPortsAvailable(const TargetConfig(type: TargetType.local), apiPort: 8000);
      expect(res.status.isFailed, true);
      expect(res.failureMessage, 'Port 8000 is already in use.');
      expect(res.description, contains('Port 8000 is already in use by an existing Unotusk deployment'));
      expect(res.remediationHint, contains('An existing Unotusk deployment is active on port 8000'));
    });
  });
}
