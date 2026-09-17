import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/config/domain/server_config.dart';
import 'package:setup_app/features/deploy/data/deployment_engine.dart';
import 'package:setup_app/features/target/domain/target_config.dart';

void main() {
  group('DeploymentEngine Unit Tests', () {
    test('Local deployment generates files and runs compose up', () async {
      final executedCommands = <String>[];
      final tempDir = Directory.systemTemp.createTempSync('unotusk_test_deploy');
      addTearDown(() => tempDir.deleteSync(recursive: true));

      final engine = DeploymentEngine(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          executedCommands.add('$exec ${args.join(' ')}');
          return ProcessResult(1234, 0, 'ok', '');
        },
      );

      final stages = <DeployStage>[];
      final result = await engine.deploy(
        target: const TargetConfig(type: TargetType.local),
        config: ServerConfig(
          serverName: 'Test Server',
          adminEmail: 'admin@test.local',
          adminPassword: 'password123',
          llmApiKey: 'gsk_test_123',
        ),
        customDeploymentDir: tempDir.path,
        onStageChanged: stages.add,
      );

      expect(result.isSuccess, true);
      expect(stages, contains(DeployStage.preparing));
      expect(stages, contains(DeployStage.configuring));
      expect(stages, contains(DeployStage.startingServices));
      expect(stages, contains(DeployStage.completed));

      expect(File('${tempDir.path}/.env').existsSync(), true);
      expect(File('${tempDir.path}/docker-compose.yml').existsSync(), true);
      expect(executedCommands.any((c) => c.contains('docker compose') && c.contains('up -d')), true);
    });

    test('Local deployment captures and reports failure on non-zero exit', () async {
      final tempDir = Directory.systemTemp.createTempSync('unotusk_test_deploy_fail');
      addTearDown(() => tempDir.deleteSync(recursive: true));

      final engine = DeploymentEngine(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          if (args.contains('up')) {
            return ProcessResult(1234, 1, '', 'Bind for 0.0.0.0:8000 failed: port is already allocated');
          }
          return ProcessResult(1234, 0, 'ok', '');
        },
      );

      final result = await engine.deploy(
        target: const TargetConfig(type: TargetType.local),
        config: ServerConfig(llmApiKey: 'gsk_123'),
        customDeploymentDir: tempDir.path,
        onStageChanged: (_) {},
      );

      expect(result.isSuccess, false);
      expect(result.errorMessage, contains('Port 8000 is already in use.'));
      expect(result.technicalLogs, contains('port is already allocated'));
    });

    test('DeploymentEngine reports port conflict error when docker compose up fails with port already allocated', () async {
      final tempDir = Directory.systemTemp.createTempSync('unotusk_test_port_fail');
      addTearDown(() => tempDir.deleteSync(recursive: true));

      final engine = DeploymentEngine(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          if (args.contains('up')) {
            return ProcessResult(1234, 1, '', 'Bind for 0.0.0.0:8000 failed: port is already allocated');
          }
          return ProcessResult(1234, 0, 'ok', '');
        },
      );

      final stages = <DeployStage>[];
      final result = await engine.deploy(
        target: const TargetConfig(type: TargetType.local),
        config: ServerConfig(serverPort: 8000, llmApiKey: 'gsk_123'),
        customDeploymentDir: tempDir.path,
        onStageChanged: stages.add,
      );

      expect(result.isSuccess, false);
      expect(result.errorMessage, 'Port 8000 is already in use.');
      expect(stages.last, DeployStage.failed);
    });

    test('Deployment succeeds when conflict is resolved on an alternate free port', () async {
      final tempDir = Directory.systemTemp.createTempSync('unotusk_test_alt_port');
      addTearDown(() => tempDir.deleteSync(recursive: true));

      final engine = DeploymentEngine(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          return ProcessResult(1234, 0, 'ok', '');
        },
      );

      final stages = <DeployStage>[];
      final result = await engine.deploy(
        target: const TargetConfig(type: TargetType.local),
        config: ServerConfig(serverPort: 8085, llmApiKey: 'gsk_123'),
        customDeploymentDir: tempDir.path,
        onStageChanged: stages.add,
      );

      expect(result.isSuccess, true);
      expect(stages, contains(DeployStage.completed));
      final composeContent = File('${tempDir.path}/docker-compose.yml').readAsStringSync();
      expect(composeContent, contains('"8085:8000"'));
    });

    test('Deployment preserves existing POSTGRES_PASSWORD and AUTH_SECRET from existing .env', () async {
      final tempDir = Directory.systemTemp.createTempSync('unotusk_test_preserve_secrets');
      addTearDown(() => tempDir.deleteSync(recursive: true));

      final existingEnv = File('${tempDir.path}/.env');
      existingEnv.writeAsStringSync('POSTGRES_PASSWORD=original_pg_pass_123\nAUTH_SECRET=original_auth_secret_456\n');

      final engine = DeploymentEngine(
        processExecutor: (exec, args, {workingDirectory, environment}) async {
          return ProcessResult(1234, 0, 'ok', '');
        },
      );

      final result = await engine.deploy(
        target: const TargetConfig(type: TargetType.local),
        config: ServerConfig(serverPort: 8000, llmApiKey: 'gsk_new_key'),
        customDeploymentDir: tempDir.path,
        onStageChanged: (_) {},
      );

      expect(result.isSuccess, true);
      final updatedEnv = File('${tempDir.path}/.env').readAsStringSync();
      expect(updatedEnv, contains('POSTGRES_PASSWORD=original_pg_pass_123'));
      expect(updatedEnv, contains('AUTH_SECRET=original_auth_secret_456'));
      expect(updatedEnv, contains('GROQ_API_KEY=gsk_new_key'));
    });
  });
}
