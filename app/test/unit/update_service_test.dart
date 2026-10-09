import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:app/core/update/update_service.dart';

void main() {
  group('UpdateService semver comparison tests', () {
    test('detects newer patch release', () {
      expect(UpdateService.isVersionNewer('1.0.2', '1.0.1'), isTrue);
    });

    test('detects newer minor release', () {
      expect(UpdateService.isVersionNewer('1.1.0', '1.0.9'), isTrue);
    });

    test('detects newer major release', () {
      expect(UpdateService.isVersionNewer('2.0.0', '1.9.9'), isTrue);
    });

    test('returns false for identical versions', () {
      expect(UpdateService.isVersionNewer('1.0.1', '1.0.1'), isFalse);
    });

    test('returns false for older version', () {
      expect(UpdateService.isVersionNewer('1.0.0', '1.0.1'), isFalse);
    });

    test('handles leading v and release codename suffixes', () {
      expect(UpdateService.isVersionNewer('v1.0.2-rudra', '1.0.1'), isTrue);
      expect(UpdateService.isVersionNewer('v1.0.1-rudra', '1.0.1'), isFalse);
    });

    test('handles build numbers with +', () {
      expect(UpdateService.isVersionNewer('1.0.2+4', '1.0.1'), isTrue);
      expect(UpdateService.isVersionNewer('1.0.1+5', '1.0.1'), isFalse);
    });
  });

  group('AppReleaseInfo JSON parsing', () {
    const manifestJson = {
      'version': '1.0.2',
      'codename': 'Rudra',
      'tag': 'v1.0.2-rudra',
      'releaseDate': '2026-10-07',
      'channel': 'stable',
      'downloads': {
        'employeeWindows': {
          'filename': 'unotusk-employee-windows-x64.msi',
          'url': 'https://github.com/Techteam-zephvion/install-unotusk/releases/download/v1.0.2-rudra/unotusk-employee-windows-x64.msi',
        },
        'employeeMacos': {
          'filename': 'unotusk-employee-macos.dmg',
          'url': 'https://github.com/Techteam-zephvion/install-unotusk/releases/download/v1.0.2-rudra/unotusk-employee-macos.dmg',
        },
        'employeeLinux': {
          'filename': 'unotusk-employee-linux-x64.tar.gz',
          'url': 'https://github.com/Techteam-zephvion/install-unotusk/releases/download/v1.0.2-rudra/unotusk-employee-linux-x64.tar.gz',
        },
      },
    };

    test('parses manifest and detects update when current is 1.0.1', () {
      final info = AppReleaseInfo.fromJson(
        json: manifestJson,
        currentVersion: '1.0.1',
      );

      expect(info.latestVersion, equals('1.0.2'));
      expect(info.codename, equals('Rudra'));
      expect(info.tag, equals('v1.0.2-rudra'));
      expect(info.releaseDate, equals('2026-10-07'));
      expect(info.hasUpdate, isTrue);
      expect(info.downloadUrl, isNotNull);
    });

    test('parses manifest and detects up-to-date when current is 1.0.2', () {
      final info = AppReleaseInfo.fromJson(
        json: manifestJson,
        currentVersion: '1.0.2',
      );

      expect(info.hasUpdate, isFalse);
    });
  });

  group('UpdateService network fetching', () {
    test('fetches and returns AppReleaseInfo on 200 response', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'version': '1.0.2',
            'codename': 'Rudra',
            'tag': 'v1.0.2-rudra',
            'releaseDate': '2026-10-07',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = UpdateService(client: mockClient);
      final info = await service.checkForUpdates(currentVersionOverride: '1.0.1');

      expect(info, isNotNull);
      expect(info!.latestVersion, equals('1.0.2'));
      expect(info.hasUpdate, isTrue);
    });

    test('returns null gracefully on network failure without throwing', () async {
      final mockClient = MockClient((request) async {
        throw http.ClientException('Network unreachable');
      });

      final service = UpdateService(client: mockClient);
      final info = await service.checkForUpdates();

      expect(info, isNull);
    });
  });
}

