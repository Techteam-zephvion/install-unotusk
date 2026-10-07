import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/app/theme/app_theme.dart';
import 'package:app/core/network/api_client.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/auth/data/auth_repository.dart';
import 'package:app/features/auth/domain/auth_state.dart';
import 'package:app/features/auth/domain/user.dart';
import 'package:app/features/auth/presentation/auth_controller.dart';
import 'package:app/features/projects/presentation/create_project_dialog.dart';

void main() {
  testWidgets('CreateProjectDialog renders fields and validates Git URL', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          authControllerProvider.overrideWith(
            (ref) => AuthController(
              ref.watch(authRepositoryProvider),
              ref.watch(apiClientProvider),
            )..state = const AuthState(
                status: AuthStatus.authenticated,
                token: 'mock_token',
                user: User(
                  id: 'user-1',
                  email: 'test@example.com',
                  fullName: 'Alex Morgan',
                  role: 'OWNER',
                  organizationId: 'org-1',
                ),
              ),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: const Scaffold(
            body: CreateProjectDialog(),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Connect Codebase'), findsOneWidget);
    expect(find.text('Repository URL'), findsOneWidget);
    expect(find.text('Project Name'), findsOneWidget);
    expect(find.text('Project Slug'), findsOneWidget);
    expect(find.text('Connect & Ingest'), findsOneWidget);

    // Enter Git URL and check auto-fill of Project Name and Slug
    await tester.enterText(
      find.widgetWithText(TextFormField, 'https://github.com/owner/repository'),
      'https://github.com/psf/requests',
    );
    await tester.pump();

    expect(find.text('requests'), findsWidgets);
  });
}
