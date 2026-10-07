import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum AppLogLevel {
  debug,
  info,
  warning,
  error;

  String get label => name.toUpperCase();
}

enum AppLogEvent {
  applicationStart('APPLICATION_START'),
  serverUrlConfigured('SERVER_URL_CONFIGURED'),
  serverConnectionAttempt('SERVER_CONNECTION_ATTEMPT'),
  serverConnectionSuccess('SERVER_CONNECTION_SUCCESS'),
  serverConnectionFailure('SERVER_CONNECTION_FAILURE'),
  loginAttempt('LOGIN_ATTEMPT'),
  loginSuccess('LOGIN_SUCCESS'),
  loginFailure('LOGIN_FAILURE'),
  sessionRestored('SESSION_RESTORED'),
  sessionExpired('SESSION_EXPIRED'),
  projectLoadStart('PROJECT_LOAD_START'),
  projectLoadSuccess('PROJECT_LOAD_SUCCESS'),
  projectLoadFailure('PROJECT_LOAD_FAILURE'),
  ingestionStart('INGESTION_START'),
  ingestionStateChange('INGESTION_STATE_CHANGE'),
  ingestionSuccess('INGESTION_SUCCESS'),
  ingestionFailure('INGESTION_FAILURE'),
  discoveryLoad('DISCOVERY_LOAD'),
  discoveryFailure('DISCOVERY_FAILURE'),
  askStart('ASK_START'),
  askSuccess('ASK_SUCCESS'),
  askFailure('ASK_FAILURE'),
  navigationError('NAVIGATION_ERROR'),
  unexpectedError('UNEXPECTED_ERROR');

  final String eventName;
  const AppLogEvent(this.eventName);
}

class AppLogRecord {
  final DateTime timestamp;
  final String appVersion;
  final String os;
  final AppLogEvent event;
  final AppLogLevel severity;
  final String? message;
  final Map<String, dynamic>? metadata;

  AppLogRecord({
    required this.timestamp,
    required this.appVersion,
    required this.os,
    required this.event,
    required this.severity,
    this.message,
    this.metadata,
  });

  Map<String, dynamic> toJson() {
    return {
      'timestamp': timestamp.toUtc().toIso8601String(),
      'version': appVersion,
      'os': os,
      'event': event.eventName,
      'severity': severity.label,
      if (message != null) 'message': message,
      if (metadata != null && metadata!.isNotEmpty) 'metadata': metadata,
    };
  }

  String toFormattedString() {
    return jsonEncode(toJson());
  }

  @override
  String toString() => toFormattedString();
}

class AppLogger {
  static const String currentVersion = '0.1.0';
  final String osName;
  final List<AppLogRecord> _logs = [];
  final int maxBuffer;
  void Function(String)? logWriter;

  AppLogger({
    String? osName,
    this.maxBuffer = 500,
    this.logWriter,
  }) : osName = osName ?? (kIsWeb ? 'web' : Platform.operatingSystem);

  List<AppLogRecord> get logs => List.unmodifiable(_logs);


  static String sanitize(String input) {
    var sanitized = input;
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'Bearer\s+[A-Za-z0-9\-_=.]+', caseSensitive: false),
      (_) => 'Bearer [REDACTED]',
    );
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'),
      (_) => '[REDACTED-JWT]',
    );
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'((?:password|secret|token|api[_-]?key)\s*[:=]\s*["\x27]?)[^"\x27\s,]{4,}(["\x27]?)', caseSensitive: false),
      (match) => '${match.group(1)}[REDACTED]${match.group(2)}',
    );
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'(?:gsk_|sk-ant-)[A-Za-z0-9-_]{8,}', caseSensitive: false),
      (_) => '[REDACTED-KEY]',
    );
    sanitized = sanitized.replaceAllMapped(
      RegExp(r'((?:postgresql(?:\+asyncpg)?|redis)://)[^:]+:[^@]+(@\S+)', caseSensitive: false),
      (match) => '${match.group(1)}[REDACTED]${match.group(2)}',
    );
    return sanitized;
  }

  static dynamic _sanitizeValue(dynamic value) {
    if (value is String) {
      return sanitize(value);
    } else if (value is Map<String, dynamic>) {
      final sanitizedMap = <String, dynamic>{};
      for (final entry in value.entries) {
        final keyLower = entry.key.toLowerCase();
        if (keyLower.contains('password') ||
            keyLower.contains('secret') ||
            keyLower.contains('token') ||
            keyLower.contains('auth') ||
            keyLower.contains('key')) {
          sanitizedMap[entry.key] = '[REDACTED]';
        } else {
          sanitizedMap[entry.key] = _sanitizeValue(entry.value);
        }
      }
      return sanitizedMap;
    } else if (value is List) {
      return value.map(_sanitizeValue).toList();
    }
    return value;
  }

  void log({
    required AppLogEvent event,
    required AppLogLevel severity,
    String? message,
    Map<String, dynamic>? metadata,
  }) {
    final sanitizedMessage = message != null ? sanitize(message) : null;
    final sanitizedMetadata = metadata != null
        ? _sanitizeValue(metadata) as Map<String, dynamic>
        : null;

    final record = AppLogRecord(
      timestamp: DateTime.now().toUtc(),
      appVersion: currentVersion,
      os: osName,
      event: event,
      severity: severity,
      message: sanitizedMessage,
      metadata: sanitizedMetadata,
    );

    if (_logs.length >= maxBuffer) {
      _logs.removeAt(0);
    }
    _logs.add(record);

    final line = record.toFormattedString();
    if (logWriter != null) {
      logWriter!(line);
    } else if (kDebugMode) {
      debugPrint('[UNOTUSK] $line');
    }
  }

  void info(AppLogEvent event, {String? message, Map<String, dynamic>? metadata}) {
    log(event: event, severity: AppLogLevel.info, message: message, metadata: metadata);
  }

  void warning(AppLogEvent event, {String? message, Map<String, dynamic>? metadata}) {
    log(event: event, severity: AppLogLevel.warning, message: message, metadata: metadata);
  }

  void error(AppLogEvent event, {String? message, Map<String, dynamic>? metadata}) {
    log(event: event, severity: AppLogLevel.error, message: message, metadata: metadata);
  }

  void debug(AppLogEvent event, {String? message, Map<String, dynamic>? metadata}) {
    log(event: event, severity: AppLogLevel.debug, message: message, metadata: metadata);
  }

  void clear() {
    _logs.clear();
  }
}

final appLoggerProvider = Provider<AppLogger>((ref) {
  return AppLogger();
});
