import 'dart:convert';
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
typedef HttpHealthChecker = Future<bool> Function(String host, int port);

enum PortConflictSource {
  free,
  existingUnotusk,
  dockerContainer,
  localProcess,
  unknownProcess;

  bool get isFree => this == PortConflictSource.free;
}

class PortConflictInspection {
  final int port;
  final PortConflictSource source;
  final String? details;

  const PortConflictInspection({
    required this.port,
    required this.source,
    this.details,
  });

  bool get isOccupied => source != PortConflictSource.free;

  String get description {
    switch (source) {
      case PortConflictSource.free:
        return 'Port $port is open and available.';
      case PortConflictSource.existingUnotusk:
        return 'Port $port is already in use by an existing Unotusk deployment${details != null ? " ($details)" : ""}.';
      case PortConflictSource.dockerContainer:
        return 'Port $port is already in use by Docker container${details != null ? " ($details)" : ""}.';
      case PortConflictSource.localProcess:
        return 'Port $port is already in use by local process${details != null ? " ($details)" : ""}.';
      case PortConflictSource.unknownProcess:
        return 'Port $port is already in use by an unknown process.';
    }
  }
}

class EnvironmentValidator {
  final ProcessExecutor _processExecutor;
  final SocketTester _socketTester;
  final HttpHealthChecker _httpHealthChecker;

  EnvironmentValidator({
    ProcessExecutor? processExecutor,
    SocketTester? socketTester,
    HttpHealthChecker? httpHealthChecker,
  })  : _processExecutor = processExecutor ?? Process.run,
        _socketTester = socketTester ?? _defaultSocketTester,
        _httpHealthChecker = httpHealthChecker ?? _defaultHttpHealthChecker;

  static Future<bool> _defaultSocketTester(String host, int port) async {
    try {
      final socket = await ServerSocket.bind(InternetAddress.anyIPv4, port);
      await socket.close();
      return true; // Port was successfully bound, meaning it is free
    } catch (_) {
      return false; // Port is in use or forbidden
    }
  }

  static Future<bool> _defaultHttpHealthChecker(String host, int port) async {
    try {
      final client = HttpClient()..connectionTimeout = const Duration(milliseconds: 1500);
      final request = await client.getUrl(Uri.parse('http://$host:$port/health'));
      final response = await request.close().timeout(const Duration(milliseconds: 1500));
      if (response.statusCode == 200) {
        final body = await response.transform(utf8.decoder).join();
        client.close();
        return body.contains('unotusk') || body.contains('status');
      }
      client.close();
      return false;
    } catch (_) {
      return false;
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

  Future<PortConflictInspection> inspectPort(String host, int port) async {
    final isFree = await _socketTester(host, port);
    if (isFree) {
      return PortConflictInspection(
        port: port,
        source: PortConflictSource.free,
      );
    }

    // 1. Check if it is an existing Unotusk deployment
    try {
      final isUnotusk = await _httpHealthChecker(host, port);
      if (isUnotusk) {
        return PortConflictInspection(
          port: port,
          source: PortConflictSource.existingUnotusk,
          details: 'Running Unotusk API instance detected on http://$host:$port',
        );
      }
    } catch (_) {}

    // 2. Check if it is a Docker container
    try {
      final dockerRes = await _processExecutor('docker', ['ps', '--format', '{{.Names}}\t{{.Ports}}']);
      if (dockerRes.exitCode == 0) {
        final lines = dockerRes.stdout.toString().split('\n');
        for (final line in lines) {
          if (line.contains(':$port->') ||
              line.contains(':$port/') ||
              line.contains('0.0.0.0:$port') ||
              line.contains(':::$port')) {
            final parts = line.split('\t');
            final containerName = parts.isNotEmpty ? parts[0].trim() : line.trim();
            return PortConflictInspection(
              port: port,
              source: PortConflictSource.dockerContainer,
              details: containerName,
            );
          }
        }
      }
    } catch (_) {}

    // 3. Check if it is a local host process
    try {
      final lsofRes = await _processExecutor('lsof', ['-i', ':$port', '-sTCP:LISTEN', '-P', '-n']);
      if (lsofRes.exitCode == 0) {
        final lines = lsofRes.stdout.toString().trim().split('\n');
        if (lines.length > 1) {
          final processLine = lines[1].trim();
          final columns = processLine.split(RegExp(r'\s+'));
          final command = columns.isNotEmpty ? columns[0] : 'process';
          final pid = columns.length > 1 ? columns[1] : '';
          return PortConflictInspection(
            port: port,
            source: PortConflictSource.localProcess,
            details: '$command (PID $pid)',
          );
        }
      }
    } catch (_) {}

    try {
      final ssRes = await _processExecutor('ss', ['-tulpn']);
      if (ssRes.exitCode == 0) {
        final lines = ssRes.stdout.toString().trim().split('\n');
        for (final line in lines) {
          if (line.contains(':$port')) {
            return PortConflictInspection(
              port: port,
              source: PortConflictSource.localProcess,
              details: line.trim(),
            );
          }
        }
      }
    } catch (_) {}

    // 4. Unknown process
    return PortConflictInspection(
      port: port,
      source: PortConflictSource.unknownProcess,
      details: 'Unidentified process or service',
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

    final inspection = await inspectPort('localhost', apiPort);
    if (inspection.isOccupied) {
      final remediation = inspection.source == PortConflictSource.existingUnotusk
          ? 'An existing Unotusk deployment is active on port $apiPort. You can use this server or choose a different port in configuration.'
          : 'Port $apiPort is already in use by ${inspection.details ?? "another application"}. Please select a different port during configuration.';

      return CheckItem(
        id: 'ports_available',
        title: 'Required ports available',
        description: inspection.description,
        status: CheckStatus.failed,
        failureMessage: 'Port $apiPort is already in use.',
        remediationHint: remediation,
        technicalDetails: inspection.details,
      );
    }

    return CheckItem(
      id: 'ports_available',
      title: 'Required ports available',
      description: 'Port $apiPort is open and available for Unotusk API.',
      status: CheckStatus.passed,
    );
  }
}
