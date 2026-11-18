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
    expect(find.text('Acme Corporation Auth'), findsNothing);
    expect(find.text('Acme Workspace'), findsNothing);
    expect(find.text('Sign In'), findsWidgets);
    expect(find.text('Sign Up'), findsWidgets);

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

    // Switch to Sign Up mode
    final signUpTab = find.text('Sign Up').first;
    await tester.tap(signUpTab);
    await tester.pumpAndSettle();

    expect(find.text('Sign up to Unotusk'), findsOneWidget);
    expect(find.text('Organisation Name'), findsOneWidget);
  });

  testWidgets('AuthScreen toggles dark and light mode smoothly without layout errors', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    bool isDark = true;

    await tester.pumpWidget(
      StatefulBuilder(
        builder: (context, setState) {
          return MaterialApp(
            home: AuthScreen(
              palette: isDark ? UnoPalette.dark : UnoPalette.light,
              isDark: isDark,
              onToggleTheme: () => setState(() => isDark = !isDark),
              onAuthenticated: (_) {},
            ),
          );
        },
      ),
    );

    await tester.pumpAndSettle();

    // In dark mode, card has 'Dark' indicator and sign in text
    expect(find.text('Dark'), findsOneWidget);
    expect(find.text('Sign in to Unotusk'), findsOneWidget);

    // Tap theme toggle button
    await tester.tap(find.text('Dark'));
    await tester.pumpAndSettle();

    // After toggle, now in light mode
    expect(find.text('Light'), findsOneWidget);
    expect(find.text('Sign in to Unotusk'), findsOneWidget);

    // Verify textfield vertical alignment and centered padding
    final emailFieldFinder = find.byType(TextField).first;
    final emailField = tester.widget<TextField>(emailFieldFinder);
    expect(emailField.textAlignVertical, TextAlignVertical.center);
    expect(emailField.decoration?.contentPadding, const EdgeInsets.symmetric(vertical: 12));
    expect(emailField.decoration?.isDense, isTrue);
  });
}
