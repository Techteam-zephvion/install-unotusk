
enum ServerState {
  stopped,
  starting,
  running,
  degraded,
  failed,
  unknown
}

class ServerInstance {
  final String id;
  final String name;
  final String composeProject;
  final String deploymentDir;
  final int apiPort;
  final String? lanIp;
  final DateTime createdAt;
  ServerState lastKnownState;

  ServerInstance({
    required this.id,
    required this.name,
    required this.composeProject,
    required this.deploymentDir,
    required this.apiPort,
    this.lanIp,
    required this.createdAt,
    this.lastKnownState = ServerState.unknown,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'composeProject': composeProject,
      'deploymentDir': deploymentDir,
      'apiPort': apiPort,
      'lanIp': lanIp,
      'createdAt': createdAt.toIso8601String(),
      'lastKnownState': lastKnownState.name,
    };
  }

  factory ServerInstance.fromJson(Map<String, dynamic> json) {
    return ServerInstance(
      id: json['id'] as String,
      name: json['name'] as String,
      composeProject: json['composeProject'] as String,
      deploymentDir: json['deploymentDir'] as String,
      apiPort: json['apiPort'] as int,
      lanIp: json['lanIp'] as String?,
      createdAt: DateTime.parse(json['createdAt'] as String),
      lastKnownState: ServerState.values.firstWhere(
        (e) => e.name == json['lastKnownState'],
        orElse: () => ServerState.unknown,
      ),
    );
  }

  String get lanUrl => (lanIp != null && lanIp!.isNotEmpty && lanIp != '127.0.0.1' && lanIp != 'localhost')
      ? 'http://$lanIp:$apiPort'
      : 'http://localhost:$apiPort';
      
  ServerInstance copyWith({
    String? id,
    String? name,
    String? composeProject,
    String? deploymentDir,
    int? apiPort,
    String? lanIp,
    DateTime? createdAt,
    ServerState? lastKnownState,
  }) {
    return ServerInstance(
      id: id ?? this.id,
      name: name ?? this.name,
      composeProject: composeProject ?? this.composeProject,
      deploymentDir: deploymentDir ?? this.deploymentDir,
      apiPort: apiPort ?? this.apiPort,
      lanIp: lanIp ?? this.lanIp,
      createdAt: createdAt ?? this.createdAt,
      lastKnownState: lastKnownState ?? this.lastKnownState,
    );
  }
}
