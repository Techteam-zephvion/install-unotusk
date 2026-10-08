with open('app/lib/core/network/api_client.dart', 'r') as f:
    content = f.read()

old_code = """        onError: (DioException error, handler) async {
          if (error.response?.statusCode == 401) {
            onUnauthorized?.call();
          }
          return handler.next(error);
        },"""

new_code = """        onError: (DioException error, handler) async {
          if (error.response?.statusCode == 401) {
            final path = error.requestOptions.path;
            if (!path.contains('/auth/login') && !path.contains('/auth/signup')) {
              onUnauthorized?.call();
            }
          }
          return handler.next(error);
        },"""

content = content.replace(old_code, new_code)

with open('app/lib/core/network/api_client.dart', 'w') as f:
    f.write(content)
