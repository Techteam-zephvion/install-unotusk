import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/core/network/lan_detector.dart';
import 'package:app/services/server_discovery_service.dart';

class MockInterfaceAddress implements InterfaceAddress {
  @override
  final String address;
  @override
  final InternetAddressType type;
  final int networkPrefixLength;

  MockInterfaceAddress({
    required this.address,
    this.type = InternetAddressType.IPv4,
    this.networkPrefixLength = 24,
  });

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class MockNetworkInterface implements NetworkInterface {
  @override
  final String name;
  @override
  final int index;
  @override
  final List<InterfaceAddress> addresses;

  MockNetworkInterface({
    required this.name,
    this.index = 1,
    required this.addresses,
  });

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('LanDetector', () {
    test('identifies virtual interfaces accurately', () {
      final detector = LanDetector();
      expect(detector.isVirtualInterface('docker0'), isTrue);
      expect(detector.isVirtualInterface('br-12345'), isTrue);
      expect(detector.isVirtualInterface('vboxnet0'), isTrue);
      expect(detector.isVirtualInterface('tailscale0'), isTrue);
      expect(detector.isVirtualInterface('vEthernet (WSL)'), isTrue);
      expect(detector.isVirtualInterface('Wi-Fi'), isFalse);
      expect(detector.isVirtualInterface('Ethernet'), isFalse);
    });

    test('validates private IPv4 ranges', () {
      final detector = LanDetector();
      expect(detector.isPrivateIpv4('10.0.0.35'), isTrue);
      expect(detector.isPrivateIpv4('192.168.1.100'), isTrue);
      expect(detector.isPrivateIpv4('172.20.0.5'), isTrue);
      expect(detector.isPrivateIpv4('8.8.8.8'), isFalse);
      expect(detector.isPrivateIpv4('127.0.0.1'), isFalse);
      expect(detector.isPrivateIpv4('invalid.ip'), isFalse);
    });

    test('extracts preferred physical LAN address', () async {
      final detector = LanDetector(
        interfaceLister: ({bool includeLoopback = false, bool includeLinkLocal = false, InternetAddressType type = InternetAddressType.IPv4}) async {
          return [
            MockNetworkInterface(
              name: 'docker0',
              addresses: [MockInterfaceAddress(address: '172.17.0.1')],
            ),
            MockNetworkInterface(
              name: 'Wi-Fi',
              addresses: [MockInterfaceAddress(address: '10.0.0.35')],
            ),
          ];
        },
      );

      final ip = await detector.getPrimaryLanIp();
      expect(ip, '10.0.0.35');
    });
  });

  group('ServerDiscoveryService', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('discovers server when candidate responds with 200 ok', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/health' && request.url.host == '10.0.0.35') {
          return http.Response(jsonEncode({'status': 'ok', 'version': '0.1.0'}), 200);
        }
        return http.Response('Not Found', 404);
      });

      final mockLanDetector = LanDetector(
        interfaceLister: ({bool includeLoopback = false, bool includeLinkLocal = false, InternetAddressType type = InternetAddressType.IPv4}) async {
          return [
            MockNetworkInterface(
              name: 'Wi-Fi',
              addresses: [MockInterfaceAddress(address: '10.0.0.35')],
            ),
          ];
        },
      );

      final discovery = ServerDiscoveryService(
        lanDetector: mockLanDetector,
        client: mockClient,
      );

      final url = await discovery.discoverServerUrl();
      expect(url, 'http://10.0.0.35:28000');

      // Verify URL was persisted in SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString(ServerDiscoveryService.prefKeyServerUrl), 'http://10.0.0.35:28000');
    });

    test('prioritizes valid saved URL from preferences', () async {
      SharedPreferences.setMockInitialValues({
        ServerDiscoveryService.prefKeyServerUrl: 'http://custom-server.lan:28000',
      });

      final mockClient = MockClient((request) async {
        if (request.url.host == 'custom-server.lan') {
          return http.Response(jsonEncode({'status': 'ok'}), 200);
        }
        return http.Response('Error', 500);
      });

      final discovery = ServerDiscoveryService(
        client: mockClient,
      );

      final url = await discovery.discoverServerUrl();
      expect(url, 'http://custom-server.lan:28000');
    });

    test('returns fallback when no server is alive', () async {
      final mockClient = MockClient((request) async {
        throw Exception('Connection refused');
      });

      final mockLanDetector = LanDetector(
        interfaceLister: ({bool includeLoopback = false, bool includeLinkLocal = false, InternetAddressType type = InternetAddressType.IPv4}) async {
          return [
            MockNetworkInterface(
              name: 'Wi-Fi',
              addresses: [MockInterfaceAddress(address: '10.0.0.35')],
            ),
          ];
        },
      );

      final discovery = ServerDiscoveryService(
        lanDetector: mockLanDetector,
        client: mockClient,
      );

      final url = await discovery.discoverServerUrl();
      expect(url, 'http://10.0.0.35:28000');
    });

    test('discoverWithDetails returns detailed error log when no server is available', () async {
      final mockClient = MockClient((request) async {
        throw Exception('Connection refused');
      });

      final mockLanDetector = LanDetector(
        interfaceLister: ({bool includeLoopback = false, bool includeLinkLocal = false, InternetAddressType type = InternetAddressType.IPv4}) async {
          return [
            MockNetworkInterface(
              name: 'Wi-Fi',
              addresses: [MockInterfaceAddress(address: '10.0.0.35')],
            ),
          ];
        },
      );

      final discovery = ServerDiscoveryService(
        lanDetector: mockLanDetector,
        client: mockClient,
      );

      final result = await discovery.discoverWithDetails(forceRescan: true);
      expect(result.isSuccess, isFalse);
      expect(result.totalScanned, 254);
      expect(result.scannedSubnet, '10.0.0.1 – 10.0.0.254');
      expect(result.errorMessage, contains('No servers are available'));
      expect(result.logs.any((l) => l.contains('254 of 254 IPs scanned')), isTrue);
      expect(result.logs.any((l) => l.contains('[ERROR] No servers are available on the network')), isTrue);
    });
  });
}
