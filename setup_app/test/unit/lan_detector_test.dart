import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/core/network/lan_detector.dart';

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
  group('LanDetector Unit Tests', () {
    late LanDetector detector;

    setUp(() {
      detector = LanDetector();
    });

    test('isVirtualInterface correctly flags container and bridge interfaces', () {
      expect(detector.isVirtualInterface('docker0'), true);
      expect(detector.isVirtualInterface('br-cdd9b1502844'), true);
      expect(detector.isVirtualInterface('virbr0'), true);
      expect(detector.isVirtualInterface('lxcbr0'), true);
      expect(detector.isVirtualInterface('vboxnet0'), true);
      expect(detector.isVirtualInterface('tailscale0'), true);
      expect(detector.isVirtualInterface('tun0'), true);

      // Physical interfaces should NOT be virtual
      expect(detector.isVirtualInterface('wlo1'), false);
      expect(detector.isVirtualInterface('eth0'), false);
      expect(detector.isVirtualInterface('enp3s0'), false);
      expect(detector.isVirtualInterface('en0'), false);
    });

    test('isPreferredPhysicalInterface identifies physical Wi-Fi and Ethernet adapters', () {
      expect(detector.isPreferredPhysicalInterface('wlo1'), true);
      expect(detector.isPreferredPhysicalInterface('wlan0'), true);
      expect(detector.isPreferredPhysicalInterface('eth0'), true);
      expect(detector.isPreferredPhysicalInterface('enp3s0'), true);
      expect(detector.isPreferredPhysicalInterface('en0'), true);

      expect(detector.isPreferredPhysicalInterface('lo'), false);
      expect(detector.isPreferredPhysicalInterface('virbr0'), false);
    });

    test('isPrivateIpv4 validates RFC 1918 private IPv4 ranges', () {
      // 10.0.0.0/8
      expect(detector.isPrivateIpv4('10.0.0.59'), true);
      expect(detector.isPrivateIpv4('10.1.2.3'), true);

      // 172.16.0.0/12
      expect(detector.isPrivateIpv4('172.16.0.1'), true);
      expect(detector.isPrivateIpv4('172.20.0.1'), true);
      expect(detector.isPrivateIpv4('172.31.255.254'), true);
      expect(detector.isPrivateIpv4('172.32.0.1'), false); // Out of range

      // 192.168.0.0/16
      expect(detector.isPrivateIpv4('192.168.1.100'), true);
      expect(detector.isPrivateIpv4('192.168.0.1'), true);

      // Public and invalid addresses
      expect(detector.isPrivateIpv4('8.8.8.8'), false);
      expect(detector.isPrivateIpv4('1.1.1.1'), false);
      expect(detector.isPrivateIpv4('127.0.0.1'), false); // Loopback
      expect(detector.isPrivateIpv4('invalid'), false);
    });

    test('getAvailableLanAddresses filters out virtual bridges and prioritizes physical', () async {
      Future<List<NetworkInterface>> mockLister({
        bool includeLoopback = false,
        bool includeLinkLocal = false,
        InternetAddressType type = InternetAddressType.IPv4,
      }) async {
        return <NetworkInterface>[
          MockNetworkInterface(
            name: 'docker0',
            addresses: [MockInterfaceAddress(address: '172.17.0.1')],
          ),
          MockNetworkInterface(
            name: 'br-cdd9b1502844',
            addresses: [MockInterfaceAddress(address: '172.21.0.1')],
          ),
          MockNetworkInterface(
            name: 'virbr0',
            addresses: [MockInterfaceAddress(address: '192.168.122.1')],
          ),
          MockNetworkInterface(
            name: 'wlo1',
            addresses: [MockInterfaceAddress(address: '10.0.0.59')],
          ),
          MockNetworkInterface(
            name: 'eth0',
            addresses: [MockInterfaceAddress(address: '192.168.1.50')],
          ),
        ];
      }

      final customDetector = LanDetector(interfaceLister: mockLister);
      final addresses = await customDetector.getAvailableLanAddresses();

      expect(addresses.length, 2);
      expect(addresses[0].ip, '10.0.0.59');
      expect(addresses[0].interfaceName, 'wlo1');
      expect(addresses[0].isPreferred, true);

      expect(addresses[1].ip, '192.168.1.50');
      expect(addresses[1].interfaceName, 'eth0');
      expect(addresses[1].isPreferred, true);

      final primary = await customDetector.getPrimaryLanIp();
      expect(primary, '10.0.0.59');

      final serverUrl = await customDetector.resolveServerUrl(8000);
      expect(serverUrl, 'http://10.0.0.59:8000');
    });

    test('getPrimaryLanIp falls back to localhost when no valid interfaces found', () async {
      Future<List<NetworkInterface>> mockLister({
        bool includeLoopback = false,
        bool includeLinkLocal = false,
        InternetAddressType type = InternetAddressType.IPv4,
      }) async {
        return <NetworkInterface>[];
      }

      final emptyDetector = LanDetector(interfaceLister: mockLister);
      final primary = await emptyDetector.getPrimaryLanIp();
      expect(primary, 'localhost');

      final serverUrl = await emptyDetector.resolveServerUrl(8000);
      expect(serverUrl, 'http://localhost:8000');
    });
  });
}
