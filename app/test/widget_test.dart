import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/app/app.dart';
import 'package:app/core/network/api_client.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/connection/data/connection_repository.dart';
import 'package:app/features/connection/domain/connection_state.dart';
import 'package:app/features/connection/presentation/connection_controller.dart';

class MockConnectionRepository extends ConnectionRepository {
  MockConnectionRepository(super.apiClient, super.storage);

  @override
  Future<Map<String, dynamic>> testConnection([String? customUrl]) async {
    return {'status': 'ok', 'version': '0.1.0'};
  }
}

void main() {
  testWidgets('App starts and displays login screen when unauthenticated', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          connectionRepositoryProvider.overrideWith(
            (ref) => MockConnectionRepository(
              ref.watch(apiClientProvider),
              ref.watch(storageServiceProvider),
            ),
          ),
          connectionControllerProvider.overrideWith(
            (ref) => ConnectionController(
              ref.watch(connectionRepositoryProvider),
            )..state = const ServerConnectionState(
                serverUrl: 'http://localhost:8000',
                status: ConnectionStatus.connected,
              ),
          ),
        ],
        child: const UnotuskApp(),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Figma AuthFlow entry screen
    expect(find.text('Unotusk'), findsWidgets);
    expect(find.text('Sign in to Unotusk'), findsOneWidget);
    expect(find.text('Continue with OIDC Discovery'), findsOneWidget);
  });
}
