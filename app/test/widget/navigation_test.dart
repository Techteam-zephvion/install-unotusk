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
import 'package:app/features/projects/data/project_repository.dart';
import 'package:app/features/projects/domain/project.dart';

class MockConnectionRepository extends ConnectionRepository {
  MockConnectionRepository(super.apiClient, super.storage);

  @override
  Future<Map<String, dynamic>> testConnection([String? customUrl]) async {
    return {'status': 'ok', 'version': '0.1.0'};
  }
}

class MockProjectRepository extends ProjectRepository {
  MockProjectRepository(super.apiClient);

  @override
  Future<List<Project>> getProjects() async {
    return [
      const Project(
        id: 'proj-1',
        name: 'requests',
        slug: 'requests',
        description: 'Python HTTP library',
        status: 'READY',
        repositoryName: 'psf/requests',
      ),
      const Project(
        id: 'proj-2',
        name: 'payments-service',
        slug: 'payments-service',
        description: 'Payment gateway',
        status: 'READY',
        repositoryName: 'acme/payments',
      ),
    ];
  }

  @override
  Future<Project> getProjectById(String id) async {
    return const Project(
      id: 'proj-1',
      name: 'requests',
      slug: 'requests',
      description: 'Python HTTP library',
      status: 'READY',
      repositoryName: 'psf/requests',
    );
  }
}

void main() {
  testWidgets('Authenticated user sees Projects dashboard and can navigate to Workspace and Settings', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    SharedPreferences.setMockInitialValues({
      'unotusk_auth_token': 'test-token-xyz',
      'unotusk_user_data': '{"id":"u1","email":"dev@acme.com","full_name":"Jane Dev","role":"member"}',
    });
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
          projectRepositoryProvider.overrideWith(
            (ref) => MockProjectRepository(
              ref.watch(apiClientProvider),
            ),
          ),
        ],
        child: const UnotuskApp(),
      ),
    );

    await tester.pumpAndSettle();

    // Verify Projects Screen Header and Items
    expect(find.text('Projects'), findsWidgets);
    expect(find.text('requests'), findsOneWidget);
    expect(find.text('payments-service'), findsOneWidget);
    expect(find.text('Jane Dev'), findsOneWidget);

    // Tap on the 'requests' project
    await tester.tap(find.text('requests'));
    await tester.pumpAndSettle();

    // Verify Project Workspace Shell Tabs
    expect(find.text('Overview'), findsOneWidget);
    expect(find.text('Discoveries'), findsOneWidget);
    expect(find.text('Architecture'), findsOneWidget);
    expect(find.text('Files'), findsOneWidget);
    expect(find.text('Knowledge'), findsOneWidget);
    expect(find.text('Ask'), findsOneWidget);

    // Tap on Discoveries tab
    await tester.tap(find.text('Discoveries'));
    await tester.pumpAndSettle();

    expect(find.text('Discoveries'), findsWidgets);

    // Tap on Settings navigation
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();

    expect(find.text('Server address'), findsOneWidget);
    expect(find.text('Jane Dev'), findsWidgets);
    expect(find.text('Sign Out'), findsOneWidget);
  });
}
