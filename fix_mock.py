import os
import re

for test_file in ['app/test/widget/navigation_test.dart', 'app/test/widget_test.dart']:
    if not os.path.exists(test_file): continue
    with open(test_file, 'r') as f:
        content = f.read()
        
    # Replace MockApiClient definition
    content = re.sub(
        r'class MockApiClient extends ApiClient \{.*?\n\}',
        '''class MockApiClient extends ApiClient {
  MockApiClient() : super(baseUrl: 'http://localhost', onUnauthorized: () {});
  
  @override
  Future<Response<T>> get<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
    void Function(int, int)? onReceiveProgress,
  }) async {
    dynamic responseData;
    if (path.contains('/repository')) {
      responseData = {
        'project_id': 'proj-1',
        'organization_id': 'org-1',
        'repository': {
           'id': 'repo-1',
           'full_name': 'psf/requests'
        }
      };
    } else if (path.contains('/conversations')) {
      responseData = [];
    } else {
      responseData = {};
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: responseData as T,
      statusCode: 200,
    );
  }
}''',
        content,
        flags=re.DOTALL
    )
    
    # Add Dio import if not present
    if "import 'package:dio/dio.dart';" not in content:
        content = content.replace("import 'package:flutter_test/flutter_test.dart';", "import 'package:flutter_test/flutter_test.dart';\nimport 'package:dio/dio.dart';")
        
    with open(test_file, 'w') as f:
        f.write(content)

