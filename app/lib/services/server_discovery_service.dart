import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../core/network/lan_detector.dart';

class ServerDiscoveryResult {
  final bool isSuccess;
  final String? serverUrl;
  final String fallbackUrl;
  final String? scannedSubnet;
  final int totalScanned;
  final List<String> logs;
  final String? errorMessage;
  final DateTime timestamp;

  ServerDiscoveryResult({
    required this.isSuccess,
    this.serverUrl,
    required this.fallbackUrl,
    this.scannedSubnet,
    this.totalScanned = 0,
    required this.logs,
    this.errorMessage,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  String get formattedLog => logs.join('\n');
}

class ServerDiscoveryService {
  static const String prefKeyServerUrl = 'unotusk_server_url';
  static const int defaultControlPlanePort = 28000;

  static ServerDiscoveryResult? lastResult;

  final LanDetector _lanDetector;
  final http.Client _client;

  ServerDiscoveryService({LanDetector? lanDetector, http.Client? client})
      : _lanDetector = lanDetector ?? LanDetector(),
        _client = client ?? http.Client();

  /// Legacy helper returning URL directly
  Future<String> discoverServerUrl({bool forceRescan = false}) async {
    final result = await discoverWithDetails(forceRescan: forceRescan);
    return result.serverUrl ?? result.fallbackUrl;
  }

  /// Automatically discovers active Unotusk Control Plane with detailed progress logs
  Future<ServerDiscoveryResult> discoverWithDetails({
    bool forceRescan = false,
    void Function(String line)? onLog,
  }) async {
    final logs = <String>[];
    String time() {
      final now = DateTime.now();
      final h = now.hour.toString().padLeft(2, '0');
      final m = now.minute.toString().padLeft(2, '0');
      final s = now.second.toString().padLeft(2, '0');
      return '$h:$m:$s';
    }

    void addLog(String message) {
      final line = '[${time()}] $message';
      logs.add(line);
      debugPrint('[ServerDiscovery] $line');
      onLog?.call(line);
    }

    addLog('Starting server discovery...');

    String? savedUrl;
    if (!forceRescan) {
      try {
        final prefs = await SharedPreferences.getInstance();
        savedUrl = prefs.getString(prefKeyServerUrl);
      } catch (_) {}
    }

    final localCandidates = <String>[];

    // Priority 1: User's saved server URL
    if (savedUrl != null && savedUrl.trim().isNotEmpty) {
      localCandidates.add(savedUrl.trim());
      addLog('Checking previously saved server: ${savedUrl.trim()}');
    }

    // Priority 2: Local loopback
    localCandidates.add('http://127.0.0.1:$defaultControlPlanePort');
    localCandidates.add('http://localhost:$defaultControlPlanePort');

    // Priority 3: Primary physical LAN IP of this machine (e.g. http://10.0.0.35:28000)
    final myLanIp = await _lanDetector.getPrimaryLanIp();
    if (myLanIp != null && myLanIp.isNotEmpty) {
      localCandidates.add('http://$myLanIp:$defaultControlPlanePort');
    }

    // Known Linux server peer IP
    localCandidates.add('http://10.0.0.59:$defaultControlPlanePort');

    final uniqueLocal = localCandidates.toSet().toList();
    addLog('Probing local endpoints: ${uniqueLocal.join(', ')}');

    // Probe local candidates concurrently with 800ms timeout
    final probeFutures = uniqueLocal.map((url) => _probeCandidate(url, timeoutMs: 800));
    final probeResults = await Future.wait(probeFutures);

    for (int i = 0; i < probeResults.length; i++) {
      if (probeResults[i]) {
        final discovered = uniqueLocal[i];
        addLog('Connected to server at $discovered (HTTP 200 OK)');
        await _saveServerUrl(discovered);
        final res = ServerDiscoveryResult(
          isSuccess: true,
          serverUrl: discovered,
          fallbackUrl: discovered,
          logs: logs,
        );
        lastResult = res;
        return res;
      }
    }

    addLog('No local servers responding.');

    final fallback = (myLanIp != null && myLanIp.isNotEmpty)
        ? 'http://$myLanIp:$defaultControlPlanePort'
        : 'http://127.0.0.1:$defaultControlPlanePort';

    // If local machine is NOT running the server, scan the Wi-Fi subnet (.1 to .254)
    if (myLanIp != null && myLanIp.isNotEmpty) {
      final parts = myLanIp.split('.');
      if (parts.length == 4) {
        final prefix = '${parts[0]}.${parts[1]}.${parts[2]}';
        final subnetLabel = '$prefix.1 – $prefix.254';

        addLog('Active adapter $myLanIp detected on subnet $prefix.0/24');
        addLog('Searching local network ($subnetLabel) on port $defaultControlPlanePort...');

        final remoteServerUrl = await _scanSubnetForServer(myLanIp, onBatchScanned: (count) {
          addLog('Scanned $count / 254 IP addresses...');
        });

        if (remoteServerUrl != null) {
          addLog('Found live server on LAN at $remoteServerUrl (HTTP 200 OK)');
          await _saveServerUrl(remoteServerUrl);
          final res = ServerDiscoveryResult(
            isSuccess: true,
            serverUrl: remoteServerUrl,
            fallbackUrl: remoteServerUrl,
            scannedSubnet: subnetLabel,
            totalScanned: 254,
            logs: logs,
          );
          lastResult = res;
          return res;
        }

        addLog('Search complete: 254 of 254 IPs scanned across $subnetLabel.');
        addLog('[ERROR] No servers are available on the network.');
        final res = ServerDiscoveryResult(
          isSuccess: false,
          serverUrl: null,
          fallbackUrl: fallback,
          scannedSubnet: subnetLabel,
          totalScanned: 254,
          logs: logs,
          errorMessage: 'No servers are available. Scanned $subnetLabel on port $defaultControlPlanePort with 0 responses.',
        );
        lastResult = res;
        return res;
      }
    }

    addLog('[ERROR] No network interface detected. No servers available.');
    final res = ServerDiscoveryResult(
      isSuccess: false,
      serverUrl: null,
      fallbackUrl: fallback,
      logs: logs,
      errorMessage: 'No servers are available. Unable to identify active LAN adapter.',
    );
    lastResult = res;
    return res;
  }

  /// Scans the local Wi-Fi /24 subnet for any machine listening on port 28000 with a healthy API
  Future<String?> _scanSubnetForServer(
    String myIp, {
    void Function(int count)? onBatchScanned,
  }) async {
    final parts = myIp.split('.');
    if (parts.length != 4) return null;
    final prefix = '${parts[0]}.${parts[1]}.${parts[2]}';
    final myLastOctet = int.tryParse(parts[3]) ?? 0;

    // Prioritize known peers and common DHCP ranges
    final targetIps = <String>[];
    if (prefix == '10.0.0') {
      targetIps.add('10.0.0.59'); // Known Linux server IP
    }

    for (int i = 1; i <= 254; i++) {
      if (i == myLastOctet) continue;
      final ip = '$prefix.$i';
      if (!targetIps.contains(ip)) {
        targetIps.add(ip);
      }
    }

    int totalProbed = 0;
    // Batch probe sockets (batches of 30 concurrently, 350ms each)
    for (int start = 0; start < targetIps.length; start += 30) {
      final batch = targetIps.skip(start).take(30);
      final socketProbes = batch.map((ip) => _probeSocket(ip, defaultControlPlanePort));
      final openIps = (await Future.wait(socketProbes)).whereType<String>().toList();
      totalProbed += batch.length;
      onBatchScanned?.call(totalProbed);

      for (final openIp in openIps) {
        final url = 'http://$openIp:$defaultControlPlanePort';
        if (await _probeCandidate(url, timeoutMs: 1000)) {
          return url;
        }
      }
    }

    return null;
  }

  Future<String?> _probeSocket(String host, int port) async {
    if (kIsWeb) return null;
    try {
      final socket = await Socket.connect(host, port, timeout: const Duration(milliseconds: 350));
      socket.destroy();
      return host;
    } catch (_) {
      return null;
    }
  }

  Future<bool> _probeCandidate(String baseUrl, {int timeoutMs = 1000}) async {
    final cleaned = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    try {
      final uri = Uri.parse('$cleaned/health');
      final res = await _client.get(uri).timeout(Duration(milliseconds: timeoutMs));
      if (res.statusCode == 200) {
        final body = res.body.toLowerCase();
        if (body.contains('"status"') && (body.contains('"ok"') || body.contains('ok'))) {
          return true;
        }
      }
    } catch (_) {}
    return false;
  }

  Future<void> _saveServerUrl(String url) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(prefKeyServerUrl, url.trim());
    } catch (_) {}
  }
}
