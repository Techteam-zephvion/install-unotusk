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

  testWidgets('Sign Up card matches Sign In card dimensions identically across all sections', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(
      MaterialApp(
        home: AuthScreen(
          palette: UnoPalette.dark,
          onAuthenticated: (_) {},
        ),
      ),
    );
    await tester.pumpAndSettle();

    final cardFinder = find.byKey(const ValueKey('auth-card-shell'));
    expect(cardFinder, findsOneWidget);
    final signInSize = tester.getSize(cardFinder);

    // Switch to Sign Up (Step 1)
    await tester.tap(find.text('Sign Up').first);
    await tester.pumpAndSettle();
    final step1Size = tester.getSize(cardFinder);
    expect(step1Size.width, closeTo(signInSize.width, 0.1));
    expect(step1Size.height, closeTo(signInSize.height, 0.1));
    expect(find.text('Step 1 of 3 · Workspace'), findsOneWidget);

    // Fill Step 1 and advance to Step 2
    final step1Fields = find.byType(TextField);
    await tester.enterText(step1Fields.at(0), 'Alex Morgan');
    await tester.enterText(step1Fields.at(1), 'Acme Corp');
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    final step2Size = tester.getSize(cardFinder);
    expect(step2Size.width, closeTo(signInSize.width, 0.1));
    expect(step2Size.height, closeTo(signInSize.height, 0.1));
    expect(find.text('Step 2 of 3 · Credentials'), findsOneWidget);

    // Fill Step 2 and advance to Step 3
    final step2Fields = find.byType(TextField);
    await tester.enterText(step2Fields.at(0), 'alex@acme.com');
    await tester.enterText(step2Fields.at(1), 'secret123');
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    final step3Size = tester.getSize(cardFinder);
    expect(step3Size.width, closeTo(signInSize.width, 0.1));
    expect(step3Size.height, closeTo(signInSize.height, 0.1));
    expect(find.text('Step 3 of 3 · Role'), findsOneWidget);
    expect(find.text('Member'), findsOneWidget);
    expect(find.text('Manager'), findsOneWidget);
  });
}
