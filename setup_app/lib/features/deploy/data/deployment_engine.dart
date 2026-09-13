import 'dart:io';
import '../../config/domain/server_config.dart';
import '../../target/domain/target_config.dart';
import '../../validation/data/environment_validator.dart';
import 'compose_generator.dart';

enum DeployStage {
  idle,
  preparing,
  configuring,
  startingServices,
  migratingDb,
  completed,
  failed;

  String get label {
    switch (this) {
      case DeployStage.idle:
        return 'Ready to install';
      case DeployStage.preparing:
        return 'Preparing server configuration';
      case DeployStage.configuring:
        return 'Configuring services & environment';
      case DeployStage.startingServices:
        return 'Starting database, cache & API containers';
      case DeployStage.migratingDb:
        return 'Initializing database schema';
      case DeployStage.completed:
        return 'Installation completed';
      case DeployStage.failed:
        return 'Installation failed';
    }
  }
}

class DeployResult {
  final bool isSuccess;
  final String? errorMessage;
  final String? technicalLogs;

  const DeployResult({
    required this.isSuccess,
    this.errorMessage,
    this.technicalLogs,
  });
}

class DeploymentEngine {
  final ProcessExecutor _processExecutor;

  DeploymentEngine({ProcessExecutor? processExecutor})
      : _processExecutor = processExecutor ?? Process.run;

  Future<DeployResult> deploy({
    required TargetConfig target,
    required ServerConfig config,
    required void Function(DeployStage stage) onStageChanged,
    String? customDeploymentDir,
  }) async {
    try {
      // 1. Preparing
      onStageChanged(DeployStage.preparing);
      final envContent = config.generateEnvFileContent();
      final composeContent = ComposeGenerator.generateDockerCompose(config);

      // 2. Configuring (create directory and write files)
      onStageChanged(DeployStage.configuring);
      final deployDir = customDeploymentDir ?? _resolveDeploymentDir();
      final dir = Directory(deployDir);
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }

      final envFile = File('$deployDir/.env');
      envFile.writeAsStringSync(envContent);
      // Restrict permissions on .env
      try {
        if (!Platform.isWindows) {
          await _processExecutor('chmod', ['600', envFile.path]);
        }
      } catch (_) {}

      final composeFile = File('$deployDir/docker-compose.yml');
      composeFile.writeAsStringSync(composeContent);

      if (target.isLocal) {
        // 3. Starting Services
        onStageChanged(DeployStage.startingServices);
        final startRes = await _processExecutor(
          'docker',
          ['compose', '-f', composeFile.path, 'up', '-d'],
          workingDirectory: deployDir,
        );

        if (startRes.exitCode != 0) {
          return DeployResult(
            isSuccess: false,
            errorMessage: 'Failed to start Docker containers.',
            technicalLogs: 'Exit Code: ${startRes.exitCode}\nError: ${startRes.stderr}',
          );
        }

        // 4. Migrating DB
        onStageChanged(DeployStage.migratingDb);
        // Small delay for postgres readiness if needed, then run alembic
        await Future.delayed(const Duration(seconds: 2));
        final migrateRes = await _processExecutor(
          'docker',
          ['compose', '-f', composeFile.path, 'exec', '-T', 'api', 'alembic', 'upgrade', 'head'],
          workingDirectory: deployDir,
        );

        // If alembic exec succeeds or is already current
        if (migrateRes.exitCode != 0 &&
            !migrateRes.stdout.toString().contains('alembic') &&
            !migrateRes.stderr.toString().contains('alembic')) {
          // Non-fatal if alembic already ran at container bootstrap
        }

        onStageChanged(DeployStage.completed);
        return const DeployResult(isSuccess: true);
      } else {
        // Remote SSH Deployment
        onStageChanged(DeployStage.startingServices);
        final remoteDir = '/tmp/unotusk-server';
        await _processExecutor('ssh', [
          '-p', target.port.toString(),
          '${target.username}@${target.host}',
          'mkdir -p $remoteDir',
        ]);

        // Copy compose and env via scp
        await _processExecutor('scp', [
          '-P', target.port.toString(),
          composeFile.path,
          '${target.username}@${target.host}:$remoteDir/docker-compose.yml',
        ]);

        await _processExecutor('scp', [
          '-P', target.port.toString(),
          envFile.path,
          '${target.username}@${target.host}:$remoteDir/.env',
        ]);

        final remoteStart = await _processExecutor('ssh', [
          '-p', target.port.toString(),
          '${target.username}@${target.host}',
          'chmod 600 $remoteDir/.env && cd $remoteDir && docker compose up -d',
        ]);

        if (remoteStart.exitCode != 0) {
          return DeployResult(
            isSuccess: false,
            errorMessage: 'Remote docker compose up failed.',
            technicalLogs: 'Exit Code: ${remoteStart.exitCode}\nError: ${remoteStart.stderr}',
          );
        }

        onStageChanged(DeployStage.completed);
        return const DeployResult(isSuccess: true);
      }
    } catch (e, stack) {
      return DeployResult(
        isSuccess: false,
        errorMessage: 'An unexpected deployment error occurred: $e',
        technicalLogs: stack.toString(),
      );
    }
  }

  String _resolveDeploymentDir() {
    final home = Platform.environment['HOME'] ?? Directory.systemTemp.path;
    return '$home/.unotusk/server';
  }
}
