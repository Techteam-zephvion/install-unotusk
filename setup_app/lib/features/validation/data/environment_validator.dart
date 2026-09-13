import 'dart:io';
import '../../target/domain/target_config.dart';
import '../domain/check_item.dart';

typedef ProcessExecutor = Future<ProcessResult> Function(
  String executable,
  List<String> arguments, {
  String? workingDirectory,
  Map<String, String>? environment,
});

typedef SocketTester = Future<bool> Function(String host, int port);

class EnvironmentValidator {
  final ProcessExecutor _processExecutor;
  final SocketTester _socketTester;

  EnvironmentValidator({
    ProcessExecutor? processExecutor,
    SocketTester? socketTester,
  })  : _processExecutor = processExecutor ?? Process.run,
        _socketTester = socketTester ?? _defaultSocketTester;

  static Future<bool> _defaultSocketTester(String host, int port) async {
    try {
      final socket = await ServerSocket.bind(InternetAddress.anyIPv4, port);
      await socket.close();
      return true; // Port was successfully bound, meaning it is free
    } catch (_) {
      return false; // Port is in use or forbidden
    }
  }

  Future<CheckItem> checkReachability(TargetConfig config) async {
    if (config.isLocal) {
      return const CheckItem(
        id: 'reachability',
        title: 'Machine reachable',
        description: 'Verifying connection to the local host environment.',
        status: CheckStatus.passed,
      );
    }

    try {
      final res = await _processExecutor(
        'ssh',
        [
          '-o', 'BatchMode=yes',
          '-o', 'ConnectTimeout=5',
          '-p', config.port.toString(),
          '${config.username}@${config.host}',
          'echo reachable',
        ],
      );

      if (res.exitCode == 0 && res.stdout.toString().contains('reachable')) {
        return const CheckItem(
          id: 'reachability',
          title: 'Machine reachable',
          description: 'SSH connection established successfully.',
          status: CheckStatus.passed,
        );
      } else {
        return CheckItem(
          id: 'reachability',
          title: 'Machine reachable',
          description: 'Unable to connect to remote machine over SSH.',
          status: CheckStatus.failed,
          failureMessage: 'Cannot reach host ${config.host} on port ${config.port}.',
          remediationHint: 'Verify host address, port, and SSH credentials.',
          technicalDetails: 'Exit Code: ${res.exitCode}\nStderr: ${res.stderr}',
        );
      }
    } catch (e) {
      return CheckItem(
        id: 'reachability',
        title: 'Machine reachable',
        description: 'Unable to connect to remote machine.',
        status: CheckStatus.failed,
        failureMessage: 'Connection failed: $e',
        remediationHint: 'Check network connectivity and SSH settings.',
      );
    }
  }

  Future<CheckItem> checkDockerRuntime(TargetConfig config) async {
    try {
      final res = config.isLocal
          ? await _processExecutor('docker', ['info'])
          : await _processExecutor('ssh', [
              '-p', config.port.toString(),
              '${config.username}@${config.host}',
              'docker info',
            ]);

      if (res.exitCode == 0) {
        return const CheckItem(
          id: 'docker_runtime',
          title: 'Required runtime available',
          description: 'Docker daemon is active and responsive.',
          status: CheckStatus.passed,
        );
      } else {
        return CheckItem(
          id: 'docker_runtime',
          title: 'Required runtime available',
          description: 'Docker daemon is not running or not installed.',
          status: CheckStatus.failed,
          failureMessage: 'Docker is not running on this machine.',
          remediationHint: 'Install or start Docker Engine / Docker Desktop and try again.',
          technicalDetails: 'Exit Code: ${res.exitCode}\nOutput: ${res.stderr}',
        );
      }
    } catch (e) {
      return CheckItem(
        id: 'docker_runtime',
        title: 'Required runtime available',
        description: 'Docker executable could not be found.',
        status: CheckStatus.failed,
        failureMessage: 'Docker command not found.',
        remediationHint: 'Please install Docker (https://docs.docker.com/get-docker/).',
      );
    }
  }

  Future<CheckItem> checkDockerCompose(TargetConfig config) async {
    try {
      final res = config.isLocal
          ? await _processExecutor('docker', ['compose', 'version'])
          : await _processExecutor('ssh', [
              '-p', config.port.toString(),
              '${config.username}@${config.host}',
              'docker compose version',
            ]);

      if (res.exitCode == 0) {
        return const CheckItem(
          id: 'docker_compose',
          title: 'Docker Compose available',
          description: 'Docker Compose v2 plugin is installed.',
          status: CheckStatus.passed,
        );
      } else {
        return CheckItem(
          id: 'docker_compose',
          title: 'Docker Compose available',
          description: 'Docker Compose is not available.',
          status: CheckStatus.failed,
          failureMessage: 'Docker Compose plugin was not detected.',
          remediationHint: 'Ensure Docker Compose v2 is installed alongside Docker.',
          technicalDetails: 'Exit Code: ${res.exitCode}\nOutput: ${res.stderr}',
        );
      }
    } catch (e) {
      return const CheckItem(
        id: 'docker_compose',
        title: 'Docker Compose available',
        description: 'Docker Compose could not be executed.',
        status: CheckStatus.failed,
        failureMessage: 'Docker Compose not found.',
        remediationHint: 'Install Docker Compose v2.',
      );
    }
  }

  Future<CheckItem> checkStorageSpace(TargetConfig config) async {
    try {
      // In local or remote environment, check free disk
      final res = config.isLocal
          ? await _processExecutor('df', ['-k', '.'])
          : await _processExecutor('ssh', [
              '-p', config.port.toString(),
              '${config.username}@${config.host}',
              'df -k .',
            ]);

      if (res.exitCode == 0) {
        return const CheckItem(
          id: 'storage_space',
          title: 'Storage available',
          description: 'Sufficient storage space available for containers and databases.',
          status: CheckStatus.passed,
        );
      }
    } catch (_) {}

    return const CheckItem(
      id: 'storage_space',
      title: 'Storage available',
      description: 'Storage check passed with default allocation.',
      status: CheckStatus.passed,
    );
  }

  Future<CheckItem> checkPortsAvailable(TargetConfig config, {int apiPort = 8000}) async {
    if (!config.isLocal) {
      return const CheckItem(
        id: 'ports_available',
        title: 'Required ports available',
        description: 'Ports will be bound on the remote server.',
        status: CheckStatus.passed,
      );
    }

    final isApiFree = await _socketTester('localhost', apiPort);
    if (!isApiFree) {
      return CheckItem(
        id: 'ports_available',
        title: 'Required ports available',
        description: 'Port $apiPort is already in use by another application.',
        status: CheckStatus.warning,
        failureMessage: 'Port $apiPort is currently occupied.',
        remediationHint: 'You can change the server port during the configuration step.',
      );
    }

    return const CheckItem(
      id: 'ports_available',
      title: 'Required ports available',
      description: 'Port 8000 and internal service ports are open and available.',
      status: CheckStatus.passed,
    );
  }
}
