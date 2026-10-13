import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/models/models.dart';
import 'package:app/screens/auth_screen.dart';
import 'package:app/theme/app_theme.dart';

void main() {
  testWidgets('AuthScreen enforces @acme.com domain and renders clean organization UI', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    UserModel? authenticatedUser;

    await tester.pumpWidget(
      MaterialApp(
        home: AuthScreen(
          palette: UnoPalette.dark,
          onAuthenticated: (user) {
            authenticatedUser = user;
          },
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify UI branding
    expect(find.text('Sign in to Unotusk'), findsOneWidget);
    expect(find.text('Acme Corporation Auth'), findsOneWidget);
    expect(find.text('Acme Workspace'), findsOneWidget);
    expect(find.text('Sign In'), findsWidgets);
    expect(find.text('Create Workspace'), findsOneWidget);

    // Enter a non-acme.com email
    final emailField = find.byType(TextField).first;
    await tester.enterText(emailField, 'alex@gmail.com');
    await tester.pumpAndSettle();

    // Tap Sign In button
    final signInButton = find.widgetWithText(ElevatedButton, 'Sign In');
    await tester.tap(signInButton);
    await tester.pumpAndSettle();

    // Verify strict error message
    expect(
      find.text('Access restricted: Only organization accounts ending in @acme.com are permitted.'),
      findsOneWidget,
    );
    expect(authenticatedUser, isNull);

    // Switch to Create Workspace mode
    final createWorkspaceTab = find.text('Create Workspace');
    await tester.tap(createWorkspaceTab);
    await tester.pumpAndSettle();

    expect(find.text('Create Acme Workspace'), findsOneWidget);
    expect(find.text('Organisation Name'), findsOneWidget);
  });
}
