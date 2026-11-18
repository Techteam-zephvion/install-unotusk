import 'package:flutter_test/flutter_test.dart';
import 'package:app/services/api_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ApiService Control Plane Scoping', () {
    test('isControlPlane returns true for port 28000 and default baseUrl', () {
      ApiService.baseUrl = 'http://10.0.0.43:28000';
      expect(ApiService.isControlPlane, isTrue);
    });

    test('isControlPlane returns false for data plane ports', () {
      ApiService.baseUrl = 'http://10.0.0.43:28200';
      expect(ApiService.isControlPlane, isFalse);
    });

    test('isControlPlane returns false for custom high ports', () {
      ApiService.baseUrl = 'http://10.0.0.43:28150';
      expect(ApiService.isControlPlane, isFalse);
    });
  });
}
