import 'dart:io';
import '../../validation/data/environment_validator.dart';

class AppLauncher {
  final ProcessExecutor _processExecutor;

  AppLauncher({ProcessExecutor? processExecutor})
      : _processExecutor = processExecutor ?? Process.run;

  Future<bool> launchEmployeeApp({String? serverUrl}) async {
    try {
      final currentDir = Directory.current.path;
      final rootDir = currentDir.endsWith('setup_app')
          ? Directory(currentDir).parent.path
          : currentDir;

      final linuxBinary = File('$rootDir/app/build/linux/x64/debug/bundle/app');
      if (linuxBinary.existsSync()) {
        final env = <String, String>{};
        if (serverUrl != null) {
          env['UNOTUSK_SERVER_URL'] = serverUrl;
        }
        await _processExecutor(linuxBinary.path, [], environment: env);
        return true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }
}
