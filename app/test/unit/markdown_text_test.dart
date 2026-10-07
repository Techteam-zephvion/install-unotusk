import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app/widgets/markdown_text.dart';

void main() {
  group('MarkdownText.clean', () {
    test('removes bold and italic markdown markers', () {
      final input = 'This is **bold text** and *italicized word*.';
      final cleaned = MarkdownText.clean(input);
      expect(cleaned, equals('This is bold text and italicized word.'));
    });

    test('removes header markers', () {
      final input = '### Architecture Overview\n## Core Engine\n# Introduction';
      final cleaned = MarkdownText.clean(input);
      expect(cleaned, equals('Architecture Overview\nCore Engine\nIntroduction'));
    });

    test('cleans inline code backticks', () {
      final input = 'Run `docker compose up -d` to start the service.';
      final cleaned = MarkdownText.clean(input);
      expect(cleaned, equals('Run docker compose up -d to start the service.'));
    });

    test('removes markdown horizontal divider rules', () {
      final input = 'Section 1\n---\nSection 2\n***\nSection 3';
      final cleaned = MarkdownText.clean(input);
      expect(cleaned, equals('Section 1\n\nSection 2\n\nSection 3'));
    });

    test('formats bullet lists into clean readable lines', () {
      final input = '- Item one\n* Item two\n+ Item three';
      final cleaned = MarkdownText.clean(input);
      expect(cleaned, equals('• Item one\n• Item two\n• Item three'));
    });

    test('converts complex markdown responses to normal English statements', () {
      final input = '''
### Authentication Layer
The service uses **JWT authentication** with `HS256` signatures.
---
Key properties:
- Fast verification
- Stateless session management
''';
      final cleaned = MarkdownText.clean(input);
      expect(cleaned.contains('###'), isFalse);
      expect(cleaned.contains('**'), isFalse);
      expect(cleaned.contains('---'), isFalse);
      expect(cleaned.contains('`'), isFalse);
      expect(cleaned.contains('- '), isFalse);
      expect(cleaned.contains('The service uses JWT authentication with HS256 signatures.'), isTrue);
    });
  });

  group('MarkdownText Widget & Formats Rendering', () {
    testWidgets('renders GFM tables with columns and rows properly', (tester) async {
      const tableMarkdown = '''
| Feature | Status | Tier |
|:---|:---:|---:|
| Ingestion Pipeline | Active | Hot |
| Proactive Discovery | Active | Warm |
''';

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MarkdownText(text: tableMarkdown),
          ),
        ),
      );

      expect(find.byType(DataTable), findsOneWidget);
      expect(find.text('Feature'), findsOneWidget);
      expect(find.text('Status'), findsOneWidget);
      expect(find.text('Tier'), findsOneWidget);
      expect(find.text('Ingestion Pipeline'), findsOneWidget);
      expect(find.text('Proactive Discovery'), findsOneWidget);
    });

    testWidgets('renders fenced code blocks with language badge and file name', (tester) async {
      const codeMarkdown = '''
```dart:lib/main.dart
void main() {
  runApp(const MyApp());
}
```
''';

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MarkdownText(text: codeMarkdown),
          ),
        ),
      );

      expect(find.text('lib/main.dart'), findsOneWidget);
      expect(find.text('DART'), findsOneWidget);
      expect(find.text('Copy code'), findsOneWidget);
      expect(find.byType(SelectableText), findsOneWidget);
    });

    testWidgets('renders Claude-style Callout alert blocks', (tester) async {
      const calloutMarkdown = '''
> [!NOTE]
> Database migrations must be run before starting the worker.
''';

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MarkdownText(text: calloutMarkdown),
          ),
        ),
      );

      expect(find.text('NOTE'), findsOneWidget);
      expect(find.textContaining('Database migrations must be run'), findsOneWidget);
    });

    testWidgets('renders Task lists with checkboxes', (tester) async {
      const taskMarkdown = '''
- [x] Complete AST parsing
- [ ] Implement cloud export
''';

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MarkdownText(text: taskMarkdown),
          ),
        ),
      );

      expect(find.text('Complete AST parsing'), findsOneWidget);
      expect(find.text('Implement cloud export'), findsOneWidget);
    });
  });
}
