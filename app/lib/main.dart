import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'app/app.dart';
import 'core/logging/app_logger.dart';
import 'core/storage/storage_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final logger = AppLogger();
  logger.info(
    AppLogEvent.applicationStart,
    metadata: {
      'version': AppLogger.currentVersion,
      'os': logger.osName,
    },
  );

  // Capture Flutter framework errors
  FlutterError.onError = (details) {
    logger.error(
      AppLogEvent.unexpectedError,
      message: details.exceptionAsString(),
      metadata: {'context': details.context?.toString()},
    );
    FlutterError.presentError(details);
  };

  // Capture uncaught asynchronous errors
  PlatformDispatcher.instance.onError = (error, stack) {
    logger.error(
      AppLogEvent.unexpectedError,
      message: error.toString(),
    );
    return true;
  };

  // Initialize local persistence
  final sharedPreferences = await SharedPreferences.getInstance();

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(sharedPreferences),
        appLoggerProvider.overrideWithValue(logger),
      ],
      child: const UnotuskApp(),
    ),
  );
}
