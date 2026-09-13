import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/target/domain/target_config.dart';
import 'package:setup_app/features/target/presentation/target_controller.dart';

void main() {
  group('TargetController Tests', () {
    test('Default configuration is local machine', () {
      final controller = TargetController();
      expect(controller.state.config.type, TargetType.local);
      expect(controller.state.config.isLocal, true);
      expect(controller.validate(), true);
    });

    test('Remote target requires host and credentials', () {
      final controller = TargetController();
      controller.setTargetType(TargetType.remote);
      expect(controller.validate(), false);
      expect(controller.state.validationError, isNotNull);

      // Supply valid remote settings
      controller.updateRemoteConfig(
        host: '192.168.1.50',
        username: 'ubuntu',
        privateKeyPath: '~/.ssh/id_rsa',
      );
      expect(controller.validate(), true);
      expect(controller.state.validationError, isNull);
    });
  });
}
