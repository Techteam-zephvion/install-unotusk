import 'package:dio/dio.dart';

class RepositoryClient {
  final String baseUrl;
  late final Dio _dio;
  String? _token;
  String? _orgId;

  RepositoryClient(this.baseUrl) {
    _dio = Dio(BaseOptions(
      baseUrl: '$baseUrl/api/v1',
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 10),
    ));
    
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_token != null) {
          options.headers['Authorization'] = 'Bearer $_token';
        }
        return handler.next(options);
      },
    ));
  }

  Future<void> loginAdmin() async {
    try {
      await _dio.post('/auth/signup', data: {
        'email': 'admin@unotusk.local',
        'password': 'admin_password123',
        'name': 'Admin User'
      });
    } catch (e) {
      if (e is DioException && e.response?.statusCode == 400) {
        // already registered
      } else {
        rethrow;
      }
    }

    final res2 = await _dio.post('/auth/login', data: {
      'email': 'admin@unotusk.local',
      'password': 'admin_password123'
    });
    
    _token = res2.data['access_token'];
    _orgId = res2.data['default_organization_id'];
  }

  Future<List<dynamic>> getProjects() async {
    final res = await _dio.get('/projects');
    return res.data;
  }

  Future<void> connectRepository(String projectName, String repoUrl, String token, String owner, String repoName) async {
    // 1. Create project
    final resProj = await _dio.post('/projects', data: {
      'organization_id': _orgId,
      'name': projectName,
      'description': 'Provisioned by Server Manager'
    });
    final projectId = resProj.data['id'];

    // 2. Connect Github Token if provided
    if (token.isNotEmpty) {
      await _dio.post('/projects/$projectId/github/connect', data: {
        'github_token': token
      });
    }

    // 3. Select repository
    final resRepo = await _dio.post('/projects/$projectId/repositories/select', data: {
      'external_id': '${owner}_$repoName',
      'owner': owner,
      'name': repoName,
      'full_name': '$owner/$repoName',
      'default_branch': 'main',
      'url': repoUrl,
      'is_private': token.isNotEmpty
    });
    final repoId = resRepo.data['id'];

    // 4. Trigger Ingestion
    await _dio.post('/projects/$projectId/repositories/$repoId/ingest');
  }
}
