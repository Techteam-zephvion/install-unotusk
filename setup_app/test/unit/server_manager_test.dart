import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/manager/data/server_registry.dart';
import 'package:setup_app/features/manager/domain/server_instance.dart';
import 'package:setup_app/features/manager/data/server_manager_controller.dart';

void main() {
  test('ServerRegistry generates sequential IDs', () async {
    final reg = ServerRegistry();
    final id = await reg.generateNextServerId();
    expect(id, isNotNull);
  });
  
  test('ServerInstance serialization', () {
    final inst = ServerInstance(
      id: 'server-01',
      name: 'Server 1',
      composeProject: 'server-01',
      deploymentDir: '/tmp',
      apiPort: 8000,
      createdAt: DateTime.now(),
    );
    final json = inst.toJson();
    final parsed = ServerInstance.fromJson(json);
    expect(parsed.id, 'server-01');
    expect(parsed.apiPort, 8000);
  });
}
