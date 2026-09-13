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
            return ProcessResult(1234, 1, '', 'Port 8000 already in use');
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
      expect(result.errorMessage, contains('Failed to start Docker containers'));
      expect(result.technicalLogs, contains('Port 8000 already in use'));
    });
  });
}
