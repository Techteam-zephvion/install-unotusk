import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:unotusk_flutter_app/main.dart';

void main() {
  testWidgets('Unotusk App smoke test', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const UnotuskApp());
    expect(find.text('Sign in to Unotusk'), findsOneWidget);
  });
}
