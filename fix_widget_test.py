import re

with open('app/test/widget_test.dart', 'r') as f:
    content = f.read()

# Add pumpWidget(Container()) to dispose
if 'tester.pumpWidget(const SizedBox());' not in content:
    content = content.replace("expect(find.text('Sign in to Unotusk'), findsOneWidget);", "expect(find.text('Sign in to Unotusk'), findsOneWidget);\n    await tester.pumpWidget(const SizedBox());\n    await tester.pump();")

with open('app/test/widget_test.dart', 'w') as f:
    f.write(content)

