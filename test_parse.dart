import 'dart:convert';
import 'dart:io';

void main() async {
  final res = await Process.run(
    'docker',
    ['compose', '-p', 'server-01', 'ps', '--all', '--format', 'json'],
    workingDirectory: '/home/devils/.unotusk/servers/server-01',
  );
  
  bool hasRunning = false;
  bool hasExited = false;
  
  final lines = res.stdout.toString().trim().split('\n');
  for (var line in lines) {
    if (line.trim().isEmpty) continue;
    try {
      final json = jsonDecode(line);
      final state = json['State']?.toString().toLowerCase();
      final exitCode = json['ExitCode'];
      final serviceName = json['Service']?.toString() ?? '';
      
      print('Service: ' + serviceName + ', State: ' + state.toString() + ', ExitCode: ' + exitCode.toString());
      if (state == 'running') {
        hasRunning = true;
      } else if (serviceName == 'migration' && exitCode == 0) {
        continue;
      } else {
        hasExited = true;
      }
    } catch (e) {
      print('Error: ' + e.toString());
    }
  }
  print('hasRunning: ' + hasRunning.toString() + ', hasExited: ' + hasExited.toString());
}
