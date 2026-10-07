import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/workspace/domain/file_node.dart';
import 'package:app/features/workspace/domain/project_file.dart';

void main() {
  group('FileNode Tree Utilities', () {
    final testFiles = [
      const ProjectFile(
        id: '1',
        snapshotId: 's1',
        path: 'src/requests/sessions.py',
        filename: 'sessions.py',
        extension: '.py',
        language: 'Python',
        sizeBytes: 1000,
        contentHash: 'h1',
        isBinary: false,
        isGenerated: false,
        isTest: false,
        lineCount: 780,
        parserSupported: true,
      ),
      const ProjectFile(
        id: '2',
        snapshotId: 's1',
        path: 'src/requests/adapters.py',
        filename: 'adapters.py',
        extension: '.py',
        language: 'Python',
        sizeBytes: 800,
        contentHash: 'h2',
        isBinary: false,
        isGenerated: false,
        isTest: false,
        lineCount: 450,
        parserSupported: true,
      ),
      const ProjectFile(
        id: '3',
        snapshotId: 's1',
        path: 'tests/test_requests.py',
        filename: 'test_requests.py',
        extension: '.py',
        language: 'Python',
        sizeBytes: 500,
        contentHash: 'h3',
        isBinary: false,
        isGenerated: false,
        isTest: true,
        lineCount: 200,
        parserSupported: true,
      ),
      const ProjectFile(
        id: '4',
        snapshotId: 's1',
        path: 'README.md',
        filename: 'README.md',
        extension: '.md',
        language: 'Markdown',
        sizeBytes: 200,
        contentHash: 'h4',
        isBinary: false,
        isGenerated: false,
        isTest: false,
        lineCount: 50,
        parserSupported: false,
      ),
    ];

    test('buildTree correctly constructs hierarchical tree with directories first', () {
      final tree = FileNode.buildTree(testFiles);

      // Root level: 'src' (dir), 'tests' (dir), 'README.md' (file)
      expect(tree.length, 3);
      expect(tree[0].name, 'src');
      expect(tree[0].isDirectory, isTrue);
      expect(tree[1].name, 'tests');
      expect(tree[1].isDirectory, isTrue);
      expect(tree[2].name, 'README.md');
      expect(tree[2].isDirectory, isFalse);

      // src level: 'requests' (dir)
      final srcDir = tree[0];
      expect(srcDir.children.length, 1);
      expect(srcDir.children[0].name, 'requests');

      // requests level: 'adapters.py', 'sessions.py' (sorted alphabetically)
      final reqDir = srcDir.children[0];
      expect(reqDir.children.length, 2);
      expect(reqDir.children[0].name, 'adapters.py');
      expect(reqDir.children[1].name, 'sessions.py');
    });

    test('filterTree filters files by query matching filename or directory', () {
      final tree = FileNode.buildTree(testFiles);

      // Filter by 'session'
      final filtered = FileNode.filterTree(tree, 'session');
      expect(filtered.length, 1);
      expect(filtered[0].name, 'src');
      final reqDir = filtered[0].children[0];
      expect(reqDir.children.length, 1);
      expect(reqDir.children[0].name, 'sessions.py');

      // Filter by 'tests'
      final testFiltered = FileNode.filterTree(tree, 'test');
      expect(testFiltered.length, 1);
      expect(testFiltered[0].name, 'tests');

      // Filter by nonexistent string
      final emptyFiltered = FileNode.filterTree(tree, 'nonexistent_file');
      expect(emptyFiltered.isEmpty, isTrue);
    });
  });
}
