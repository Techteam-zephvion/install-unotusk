import 'project_dependency.dart';
import 'project_file.dart';

class ComponentNode {
  final String path;
  final String name;
  final String? fileId;
  final String? language;
  final List<ProjectDependency> incomingCallers;
  final List<ProjectDependency> outgoingDependencies;

  const ComponentNode({
    required this.path,
    required this.name,
    this.fileId,
    this.language,
    this.incomingCallers = const [],
    this.outgoingDependencies = const [],
  });

  int get callerCount => incomingCallers.length;
  int get dependencyCount => outgoingDependencies.length;

  static List<ComponentNode> aggregateComponents({
    required List<ProjectDependency> dependencies,
    required List<ProjectFile> files,
  }) {
    final Map<String, ProjectFile> fileMap = {
      for (final f in files) f.path: f,
    };

    final Map<String, List<ProjectDependency>> incoming = {};
    final Map<String, List<ProjectDependency>> outgoing = {};
    final Set<String> allPaths = {};

    // Collect all files
    for (final f in files) {
      allPaths.add(f.path);
    }

    // Map dependencies
    for (final dep in dependencies) {
      if (dep.sourcePath != null) {
        allPaths.add(dep.sourcePath!);
        outgoing.putIfAbsent(dep.sourcePath!, () => []).add(dep);
      }
      if (dep.targetPath != null) {
        allPaths.add(dep.targetPath!);
        incoming.putIfAbsent(dep.targetPath!, () => []).add(dep);
      }
    }

    final List<ComponentNode> nodes = [];

    for (final path in allPaths) {
      final file = fileMap[path];
      final name = path.split('/').last;

      nodes.add(ComponentNode(
        path: path,
        name: name,
        fileId: file?.id,
        language: file?.language ?? 'UNKNOWN',
        incomingCallers: incoming[path] ?? [],
        outgoingDependencies: outgoing[path] ?? [],
      ));
    }

    // Sort by most used (highest caller count), then alphabetical
    nodes.sort((a, b) {
      final cmp = b.callerCount.compareTo(a.callerCount);
      if (cmp != 0) return cmp;
      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });

    return nodes;
  }
}
