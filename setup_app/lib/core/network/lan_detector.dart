import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class LanAddressInfo {
  final String ip;
  final String interfaceName;
  final bool isPreferred;

  const LanAddressInfo({
    required this.ip,
    required this.interfaceName,
    this.isPreferred = false,
  });

  @override
  String toString() => '$ip ($interfaceName)';
}

typedef NetworkInterfaceLister = Future<List<NetworkInterface>> Function({
  bool includeLoopback,
  bool includeLinkLocal,
  InternetAddressType type,
});

class LanDetector {
  final NetworkInterfaceLister _interfaceLister;

  LanDetector({NetworkInterfaceLister? interfaceLister})
      : _interfaceLister = interfaceLister ?? NetworkInterface.list;

  /// Prefixes commonly used for virtual/container/bridge network interfaces
  /// that should NOT be advertised as the physical LAN address.
  static const List<String> virtualInterfacePrefixes = [
    'docker',
    'br-',
    'virbr',
    'lxcbr',
    'vboxnet',
    'vmnet',
    'tun',
    'tap',
    'wg',
    'tailscale',
  ];

  /// Prefixes commonly associated with physical Ethernet or Wi-Fi interfaces.
  static const List<String> physicalInterfacePrefixes = [
    'wl', // wlo1, wlan0, wlp2s0
    'en', // enp3s0, eno1, en0
    'eth', // eth0, eth1
    'wi-fi',
    'ethernet',
    'wlan',
  ];

  bool isVirtualInterface(String name) {
    final lower = name.toLowerCase();
    return virtualInterfacePrefixes.any((prefix) => lower.startsWith(prefix));
  }

  bool isPreferredPhysicalInterface(String name) {
    final lower = name.toLowerCase();
    return physicalInterfacePrefixes.any((prefix) => lower.startsWith(prefix));
  }

  bool isPrivateIpv4(String ip) {
    final parts = ip.split('.');
    if (parts.length != 4) return false;

    final octets = parts.map(int.tryParse).toList();
    if (octets.any((o) => o == null || o < 0 || o > 255)) return false;

    final first = octets[0]!;
    final second = octets[1]!;

    // 10.0.0.0/8 (10.x.x.x)
    if (first == 10) return true;

    // 172.16.0.0/12 (172.16.x.x - 172.31.x.x)
    if (first == 172 && second >= 16 && second <= 31) return true;

    // 192.168.0.0/16 (192.168.x.x)
    if (first == 192 && second == 168) return true;

    return false;
  }

  Future<List<LanAddressInfo>> getAvailableLanAddresses() async {
    try {
      final interfaces = await _interfaceLister(
        includeLoopback: false,
        includeLinkLocal: false,
        type: InternetAddressType.IPv4,
      );

      final List<LanAddressInfo> preferred = [];
      final List<LanAddressInfo> secondary = [];

      for (final iface in interfaces) {
        if (isVirtualInterface(iface.name)) continue;

        for (final addr in iface.addresses) {
          if (addr.type != InternetAddressType.IPv4) continue;
          final ip = addr.address;
          if (ip.startsWith('127.') || ip.startsWith('169.254.')) continue;
          if (!isPrivateIpv4(ip)) continue;

          final isPhys = isPreferredPhysicalInterface(iface.name);
          final info = LanAddressInfo(
            ip: ip,
            interfaceName: iface.name,
            isPreferred: isPhys,
          );

          if (isPhys) {
            preferred.add(info);
          } else {
            secondary.add(info);
          }
        }
      }

      return [...preferred, ...secondary];
    } catch (_) {
      return [];
    }
  }

  Future<String> getPrimaryLanIp() async {
    final addresses = await getAvailableLanAddresses();
    if (addresses.isNotEmpty) {
      return addresses.first.ip;
    }
    return 'localhost';
  }

  Future<String> resolveServerUrl(int port) async {
    final ip = await getPrimaryLanIp();
    return 'http://$ip:$port';
  }
}

final lanDetectorProvider = Provider<LanDetector>((ref) {
  return LanDetector();
});

final primaryLanIpProvider = FutureProvider<String>((ref) async {
  final detector = ref.watch(lanDetectorProvider);
  return detector.getPrimaryLanIp();
});

final availableLanAddressesProvider = FutureProvider<List<LanAddressInfo>>((ref) async {
  final detector = ref.watch(lanDetectorProvider);
  return detector.getAvailableLanAddresses();
});
