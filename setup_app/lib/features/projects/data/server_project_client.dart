import 'package:dio/dio.dart';

class ServerProjectClient {
  final Dio _dio;

  ServerProjectClient({Dio? dio})
      : _dio = dio ??
            Dio(
              BaseOptions(
                connectTimeout: const Duration(seconds: 10),
                receiveTimeout: const Duration(seconds: 15),
              ),
            );

  Future<({String token, String orgId})?> authenticateAdmin({
    required String serverUrl,
    required String email,
    required String password,
    String? adminName,
  }) async {
    final cleanUrl = serverUrl.replaceAll(RegExp(r'/+$'), '');
    final cleanEmail = email.trim().toLowerCase();

    // 1. Try login
    try {
      final res = await _dio.post(
        '$cleanUrl/api/v1/auth/login',
        data: {'email': cleanEmail, 'password': password},
      );
      if (res.statusCode == 200 && res.data != null) {
        final token = res.data['access_token'] as String;
        final orgId = await _fetchPrimaryOrgId(cleanUrl, token);
        return (token: token, orgId: orgId);
      }
    } catch (_) {
      // Login failed, try signup if fresh instance
    }

    // 2. Try signup if fresh instance
    try {
      final res = await _dio.post(
        '$cleanUrl/api/v1/auth/signup',
        data: {
          'email': cleanEmail,
          'password': password,
          'name': adminName ?? 'Server Admin',
          'organization_name': 'Engineering Org',
        },
      );
      if (res.statusCode == 201 && res.data != null) {
        final token = res.data['access_token'] as String;
        final orgId = await _fetchPrimaryOrgId(cleanUrl, token);
        return (token: token, orgId: orgId);
      }
    } catch (_) {}

    return null;
  }

  Future<String> _fetchPrimaryOrgId(String baseUrl, String token) async {
    try {
      final res = await _dio.get(
        '$baseUrl/api/v1/auth/me',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      if (res.statusCode == 200 && res.data != null) {
        final orgs = res.data['organizations'] as List?;
        if (orgs != null && orgs.isNotEmpty) {
          return orgs[0]['id'].toString();
        }
      }
    } catch (_) {}
    return '';
  }

  Future<List<Map<String, dynamic>>> listProjects({
    required String serverUrl,
    required String token,
  }) async {
    final cleanUrl = serverUrl.replaceAll(RegExp(r'/+$'), '');
    try {
      final res = await _dio.get(
        '$cleanUrl/api/v1/projects',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      if (res.statusCode == 200 && res.data is List) {
        return List<Map<String, dynamic>>.from(res.data as List);
      }
    } catch (_) {}
    return [];
  }

  Future<Map<String, dynamic>?> createProject({
    required String serverUrl,
    required String token,
    required String name,
    required String orgId,
    String? repoUrl,
    String? description,
    int? port,
  }) async {
    final cleanUrl = serverUrl.replaceAll(RegExp(r'/+$'), '');
    try {
      final res = await _dio.post(
        '$cleanUrl/api/v1/projects',
        data: {
          'name': name.trim(),
          'organization_id': orgId,
          if (description != null && description.isNotEmpty)
            'description': description.trim(),
          'port': ?port,
        },
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );

      if (res.statusCode == 201 && res.data != null) {
        final project = res.data as Map<String, dynamic>;
        final projectId = project['id']?.toString();

        // Connect repository if repoUrl provided
        if (repoUrl != null && repoUrl.trim().isNotEmpty && projectId != null) {
          try {
            var cleanRepo = repoUrl.trim();
            if (cleanRepo.endsWith('.git')) {
              cleanRepo = cleanRepo.substring(0, cleanRepo.length - 4);
            }
            final uri = Uri.tryParse(cleanRepo);
            String owner = 'default';
            String repoName = name.toLowerCase().replaceAll(' ', '-');
            if (uri != null && uri.pathSegments.length >= 2) {
              owner = uri.pathSegments[uri.pathSegments.length - 2];
              repoName = uri.pathSegments.last;
            }

            final repoRes = await _dio.post(
              '$cleanUrl/api/v1/projects/$projectId/repositories/select',
              data: {
                'external_id': '${owner}_$repoName',
                'owner': owner,
                'name': repoName,
                'full_name': '$owner/$repoName',
                'clone_url': repoUrl.trim(),
                'default_branch': 'main',
              },
              options: Options(headers: {'Authorization': 'Bearer $token'}),
            );

            if (repoRes.statusCode == 200 && repoRes.data != null) {
              final repoId = repoRes.data['id']?.toString();
              if (repoId != null) {
                await _dio.post(
                  '$cleanUrl/api/v1/projects/$projectId/repositories/$repoId/ingest',
                  options: Options(headers: {'Authorization': 'Bearer $token'}),
                );
              }
            }
          } catch (_) {}
        }

        return project;
      }
    } catch (e) {
      rethrow;
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> listMembers({
    required String serverUrl,
    required String token,
    required String projectId,
  }) async {
    final cleanUrl = serverUrl.replaceAll(RegExp(r'/+$'), '');
    try {
      final res = await _dio.get(
        '$cleanUrl/api/v1/projects/$projectId/members',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      if (res.statusCode == 200 && res.data is List) {
        return List<Map<String, dynamic>>.from(res.data as List);
      }
    } catch (_) {}
    return [];
  }

  Future<bool> addMember({
    required String serverUrl,
    required String token,
    required String projectId,
    required String email,
    String role = 'MEMBER',
  }) async {
    final cleanUrl = serverUrl.replaceAll(RegExp(r'/+$'), '');
    try {
      final res = await _dio.post(
        '$cleanUrl/api/v1/projects/$projectId/members',
        data: {'email': email.trim().toLowerCase(), 'role': role},
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      return res.statusCode == 200 || res.statusCode == 201;
    } catch (e) {
      rethrow;
    }
  }

  Future<bool> removeMember({
    required String serverUrl,
    required String token,
    required String projectId,
    required String userId,
  }) async {
    final cleanUrl = serverUrl.replaceAll(RegExp(r'/+$'), '');
    try {
      final res = await _dio.delete(
        '$cleanUrl/api/v1/projects/$projectId/members/$userId',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
