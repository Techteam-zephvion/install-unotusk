enum TargetType {
  local,
  remote;

  String get label {
    switch (this) {
      case TargetType.local:
        return 'This computer';
      case TargetType.remote:
        return 'Remote Linux server';
    }
  }

  String get description {
    switch (this) {
      case TargetType.local:
        return 'Run Unotusk Server directly on this local machine using Docker.';
      case TargetType.remote:
        return 'Deploy Unotusk Server to an existing Linux server over SSH.';
    }
  }
}

class TargetConfig {
  final TargetType type;
  final String host;
  final int port;
  final String username;
  final String? privateKeyPath;
  final String? password;

  const TargetConfig({
    this.type = TargetType.local,
    this.host = 'localhost',
    this.port = 22,
    this.username = 'root',
    this.privateKeyPath,
    this.password,
  });

  bool get isLocal => type == TargetType.local;

  TargetConfig copyWith({
    TargetType? type,
    String? host,
    int? port,
    String? username,
    String? privateKeyPath,
    String? password,
  }) {
    return TargetConfig(
      type: type ?? this.type,
      host: host ?? this.host,
      port: port ?? this.port,
      username: username ?? this.username,
      privateKeyPath: privateKeyPath ?? this.privateKeyPath,
      password: password ?? this.password,
    );
  }
}
