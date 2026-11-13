import 'dart:io';
import 'package:flutter/foundation.dart';

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
    'vethernet',
  ];

  static const List<String> physicalInterfacePrefixes = [
    'wl',
    'en',
    'eth',
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
    return physicalInterfacePrefixes.any((prefix) => lower.contains(prefix));
  }

  bool isPrivateIpv4(String ip) {
    final parts = ip.split('.');
    if (parts.length != 4) return false;

    final octets = parts.map(int.tryParse).toList();
    if (octets.any((o) => o == null || o < 0 || o > 255)) return false;

    final first = octets[0]!;
    final second = octets[1]!;

    if (first == 10) return true;
    if (first == 172 && second >= 16 && second <= 31) return true;
    if (first == 192 && second == 168) return true;

    return false;
  }

  Future<List<LanAddressInfo>> getAvailableLanAddresses() async {
    if (kIsWeb) return [];
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

  Future<String?> getPrimaryLanIp() async {
    final addresses = await getAvailableLanAddresses();
    if (addresses.isNotEmpty) {
      return addresses.first.ip;
    }
    return null;
  }
}
