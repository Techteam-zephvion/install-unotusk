class AppConfig {
  static const String appName = 'Unotusk';
  static const String appVersion = '0.1.0';
  static const String defaultServerUrl = 'http://localhost:8000';
  
  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 15);
  
  // Storage keys
  static const String keyServerUrl = 'unotusk_server_url';
  static const String keyAuthToken = 'unotusk_auth_token';
  static const String keyUserData = 'unotusk_user_data';
}
