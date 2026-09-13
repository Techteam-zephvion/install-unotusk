enum ConnectionStatus {
  initial,
  checking,
  connected,
  disconnected,
  error,
}

class ServerConnectionState {
  final String serverUrl;
  final ConnectionStatus status;
  final String? errorMessage;
  final String? serverVersion;

  const ServerConnectionState({
    required this.serverUrl,
    this.status = ConnectionStatus.initial,
    this.errorMessage,
    this.serverVersion,
  });

  bool get isConnected => status == ConnectionStatus.connected;
  bool get isChecking => status == ConnectionStatus.checking;

  ServerConnectionState copyWith({
    String? serverUrl,
    ConnectionStatus? status,
    String? errorMessage,
    String? serverVersion,
  }) {
    return ServerConnectionState(
      serverUrl: serverUrl ?? this.serverUrl,
      status: status ?? this.status,
      errorMessage: errorMessage,
      serverVersion: serverVersion ?? this.serverVersion,
    );
  }
}
