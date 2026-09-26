import 'dart:io';
import '../../target/domain/target_config.dart';
import '../../validation/domain/check_item.dart';
import '../../validation/data/environment_validator.dart';

class NetworkValidator {
  final ProcessExecutor _processExecutor;

  NetworkValidator({ProcessExecutor? processExecutor})
      : _processExecutor = processExecutor ?? Process.run;

  Future<CheckItem> checkLanIp(TargetConfig config) async {
    try {
      final script = '''
#!/bin/sh
IP_ADDR=""
# Try to get the IP used for default route first
IP_ADDR=\$(ip -4 route get 8.8.8.8 2>/dev/null | grep -oP 'src \\K\\S+')
if [ -z "\$IP_ADDR" ]; then
  IP_ADDR=\$(ip -4 addr show | grep inet | awk '{print \$2}' | cut -d/ -f1 | grep -E '^(10\\.|172\\.(1[6-9]|2[0-9]|3[0-1])\\.|192\\.168\\.)' | head -n 1)
fi
echo \$IP_ADDR
''';
      
      final res = config.isLocal
          ? await _processExecutor('sh', ['-c', script])
          : await _processExecutor('ssh', [
              '-p', config.port.toString(),
              '${config.username}@${config.host}',
              script
            ]);

      final ip = res.stdout.toString().trim();
      
      if (ip.isNotEmpty && _isPrivateIp(ip)) {
        return CheckItem(
          id: 'lan_ip',
          title: 'LAN IP Address',
          description: 'Detected LAN IP: $ip',
          status: CheckStatus.passed,
          technicalDetails: ip,
        );
      } else {
         return CheckItem(
          id: 'lan_ip',
          title: 'LAN IP Address',
          description: 'Could not detect a valid private LAN IP.',
          status: CheckStatus.failed,
          failureMessage: 'No valid LAN interface found.',
          remediationHint: 'Ensure the server is connected to a local network.',
        );
      }
    } catch (e) {
      return CheckItem(
        id: 'lan_ip',
        title: 'LAN IP Address',
        description: 'Failed to detect network interfaces.',
        status: CheckStatus.failed,
        failureMessage: e.toString(),
      );
    }
  }

  bool _isPrivateIp(String ip) {
    if (ip.startsWith('10.')) return true;
    if (ip.startsWith('192.168.')) return true;
    if (ip.startsWith('172.')) {
      final parts = ip.split('.');
      if (parts.length > 1) {
        final second = int.tryParse(parts[1]);
        if (second != null && second >= 16 && second <= 31) return true;
      }
    }
    return false;
  }

  Future<CheckItem> checkFirewall(TargetConfig config, {int apiPort = 8000}) async {
    try {
      final script = '''
#!/bin/sh
if command -v ufw >/dev/null 2>&1; then
  STATUS=\$(sudo ufw status | grep -w "$apiPort.*ALLOW")
  if [ -n "\$STATUS" ]; then
    echo "OK: UFW allows $apiPort"
    exit 0
  fi
  ACTIVE=\$(sudo ufw status | grep "Status: active")
  if [ -n "\$ACTIVE" ]; then
    echo "BLOCK: UFW is active but $apiPort is not allowed."
    echo "CMD: sudo ufw allow $apiPort/tcp"
    exit 1
  fi
  echo "OK: UFW inactive"
  exit 0
elif command -v firewall-cmd >/dev/null 2>&1; then
  ACTIVE=\$(sudo firewall-cmd --state 2>/dev/null)
  if [ "\$ACTIVE" = "running" ]; then
    HAS_PORT=\$(sudo firewall-cmd --list-ports | grep "$apiPort")
    if [ -z "\$HAS_PORT" ]; then
      echo "BLOCK: firewalld is active but $apiPort is not allowed."
      echo "CMD: sudo firewall-cmd --add-port=$apiPort/tcp --permanent && sudo firewall-cmd --reload"
      exit 1
    fi
  fi
  echo "OK: firewalld OK"
  exit 0
fi
echo "OK: No common firewall blocking detected"
exit 0
''';

      final res = config.isLocal
          ? await _processExecutor('sh', ['-c', script])
          : await _processExecutor('ssh', [
              '-p', config.port.toString(),
              '${config.username}@${config.host}',
              script
            ]);
            
      final output = res.stdout.toString().trim();
      if (res.exitCode == 1 || output.startsWith('BLOCK:')) {
        final lines = output.split('\\n');
        String remediation = 'Configure firewall to allow TCP port $apiPort.';
        for (var line in lines) {
          if (line.startsWith('CMD: ')) {
            remediation = line.substring(5).trim();
          }
        }
        return CheckItem(
          id: 'firewall',
          title: 'Firewall Configuration',
          description: 'Firewall may block LAN access to port $apiPort.',
          status: CheckStatus.failed,
          failureMessage: 'Firewall appears to be blocking port $apiPort.',
          remediationHint: 'Administrator action required:\\n\\n$remediation',
        );
      }
      
      return CheckItem(
        id: 'firewall',
        title: 'Firewall Configuration',
        description: 'No firewall blocks detected on port $apiPort.',
        status: CheckStatus.passed,
      );

    } catch (e) {
      return CheckItem(
        id: 'firewall',
        title: 'Firewall Configuration',
        description: 'Failed to inspect firewall status.',
        status: CheckStatus.warning,
        remediationHint: 'Ensure TCP port $apiPort is accessible on the LAN.',
      );
    }
  }
}
