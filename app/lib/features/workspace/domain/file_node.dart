import 'project_file.dart';

class FileNode {
  final String name;
  final String path;
  final bool isDirectory;
  final ProjectFile? file;
  final List<FileNode> children;

  FileNode({
    required this.name,
    required this.path,
    required this.isDirectory,
    this.file,
    List<FileNode>? children,
  }) : children = children ?? [];

  static List<FileNode> buildTree(List<ProjectFile> files) {
    final Map<String, dynamic> rootMap = {};

    for (final file in files) {
      final segments = file.path.replaceAll('\\', '/').split('/').where((s) => s.isNotEmpty).toList();
      Map<String, dynamic> current = rootMap;

      for (int i = 0; i < segments.length; i++) {
        final segment = segments[i];
        final isLast = i == segments.length - 1;

        if (isLast) {
          current[segment] = file;
        } else {
          current[segment] = current[segment] ?? <String, dynamic>{};
          current = current[segment] as Map<String, dynamic>;
        }
      }
    }

    List<FileNode> convertMap(Map<String, dynamic> map, String currentPath) {
      final List<FileNode> nodes = [];

      for (final entry in map.entries) {
        final nodePath = currentPath.isEmpty ? entry.key : '$currentPath/${entry.key}';
        if (entry.value is ProjectFile) {
          nodes.add(FileNode(
            name: entry.key,
            path: nodePath,
            isDirectory: false,
            file: entry.value as ProjectFile,
          ));
        } else if (entry.value is Map<String, dynamic>) {
          final childNodes = convertMap(entry.value as Map<String, dynamic>, nodePath);
          nodes.add(FileNode(
            name: entry.key,
            path: nodePath,
            isDirectory: true,
            children: childNodes,
          ));
        }
      }

      nodes.sort((a, b) {
        if (a.isDirectory && !b.isDirectory) return -1;
        if (!a.isDirectory && b.isDirectory) return 1;
        return a.name.toLowerCase().compareTo(b.name.toLowerCase());
      });

      return nodes;
    }

    return convertMap(rootMap, '');
  }

  static List<FileNode> filterTree(List<FileNode> nodes, String query) {
    if (query.trim().isEmpty) return nodes;
    final lowerQuery = query.toLowerCase().trim();
    final List<FileNode> result = [];

    for (final node in nodes) {
      if (node.isDirectory) {
        final filteredChildren = filterTree(node.children, query);
        if (filteredChildren.isNotEmpty || node.name.toLowerCase().contains(lowerQuery)) {
          result.add(FileNode(
            name: node.name,
            path: node.path,
            isDirectory: true,
            children: filteredChildren,
          ));
        }
      } else {
        if (node.name.toLowerCase().contains(lowerQuery) || node.path.toLowerCase().contains(lowerQuery)) {
          result.add(node);
        }
      }
    }

    return result;
  }
}
