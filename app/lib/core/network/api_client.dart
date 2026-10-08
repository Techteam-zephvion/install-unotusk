import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../app/config/app_config.dart';
import '../storage/storage_service.dart';
import 'api_exception.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  final storage = ref.watch(storageServiceProvider);
  return ApiClient(storage);
});

class ApiClient {
  final StorageService _storage;
  late final Dio _dio;
  void Function()? onUnauthorized;
  final Map<String, int> _projectPortMap = {};
  String? _activeProjectId;

  ApiClient(this._storage) {
    _dio = Dio(
      BaseOptions(
        baseUrl: _storage.getServerUrl(),
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final baseServerUrl = _storage.getServerUrl();
          options.baseUrl = baseServerUrl;

          // Automatic port switching: check if path targets a specific project workspace
          int? targetPort;
          final match = RegExp(r'^/projects/([a-zA-Z0-9-]+)').firstMatch(options.path);
          if (match != null) {
            final pid = match.group(1);
            if (pid != null && _projectPortMap.containsKey(pid)) {
              targetPort = _projectPortMap[pid];
            }
          } else if (_activeProjectId != null && _projectPortMap.containsKey(_activeProjectId)) {
            targetPort = _projectPortMap[_activeProjectId];
          }

          if (targetPort != null) {
            final uri = Uri.tryParse(baseServerUrl);
            if (uri != null && uri.hasPort && uri.port != targetPort) {
              options.baseUrl = uri.replace(port: targetPort).toString().replaceAll(RegExp(r'/+$'), '');
            }
          }

          final token = _storage.getAuthToken();
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException error, handler) async {
          if (error.response?.statusCode == 401) {
            final path = error.requestOptions.path;
            if (!path.contains('/auth/login') && !path.contains('/auth/signup')) {
              onUnauthorized?.call();
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  void registerProjectPort(String projectId, int port) {
    _projectPortMap[projectId] = port;
  }

  void registerProjectPorts(Map<String, int> ports) {
    _projectPortMap.addAll(ports);
  }

  void setActiveProjectId(String? projectId) {
    _activeProjectId = projectId;
  }

  void updateBaseUrl(String newUrl) {
    _dio.options.baseUrl = newUrl;
  }

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.get<T>(
        path,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    } catch (e) {
      throw ApiException(message: e.toString());
    }
  }

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.post<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    } catch (e) {
      throw ApiException(message: e.toString());
    }
  }

  Future<Response<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.put<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    } catch (e) {
      throw ApiException(message: e.toString());
    }
  }

  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.patch<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    } catch (e) {
      throw ApiException(message: e.toString());
    }
  }

  Future<Response<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) async {
    try {
      return await _dio.delete<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: options,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    } catch (e) {
      throw ApiException(message: e.toString());
    }
  }
}
