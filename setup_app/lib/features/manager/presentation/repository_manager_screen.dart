import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/widgets/app_button.dart';
import '../domain/server_instance.dart';
import '../data/repository_client.dart';

class RepositoryManagerScreen extends ConsumerStatefulWidget {
  final ServerInstance server;

  const RepositoryManagerScreen({super.key, required this.server});

  @override
  ConsumerState<RepositoryManagerScreen> createState() => _RepositoryManagerScreenState();
}

class _RepositoryManagerScreenState extends ConsumerState<RepositoryManagerScreen> {
  late RepositoryClient _client;
  List<dynamic> _projects = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _client = RepositoryClient(widget.server.lanUrl);
    _loadProjects();
  }

  Future<void> _loadProjects() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      await _client.loginAdmin();
      final projects = await _client.getProjects();
      setState(() {
        _projects = projects;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Projects & Repositories - ${widget.server.name}'),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error: $_error', style: const TextStyle(color: AppColors.error)),
            const SizedBox(height: 16),
            AppButton(label: 'Retry', onPressed: _loadProjects),
          ],
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(24),
      itemCount: _projects.length + 1,
      itemBuilder: (context, index) {
        if (index == _projects.length) {
          return Padding(
            padding: const EdgeInsets.only(top: 24),
            child: AppButton(
              label: 'Connect Repository',
              icon: Icons.add,
              onPressed: () => _showConnectRepoDialog(context),
            ),
          );
        }
        final project = _projects[index];
        return _buildProjectCard(project);
      },
    );
  }

  Widget _buildProjectCard(Map<String, dynamic> project) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(project['name'] ?? 'Unnamed', style: AppTextStyles.h3),
            const SizedBox(height: 8),
            Text('Status: ${project['status']}', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (project['repositories'] != null && (project['repositories'] as List).isNotEmpty)
              ...((project['repositories'] as List).map((repo) => Text('Repo: ${repo['full_name']}')))
            else
              const Text('No repositories connected.'),
          ],
        ),
      ),
    );
  }

  Future<void> _showConnectRepoDialog(BuildContext context) async {
    final projectNameController = TextEditingController();
    final urlController = TextEditingController();
    final tokenController = TextEditingController();
    
    await showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Connect Repository'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: projectNameController,
                  decoration: const InputDecoration(labelText: 'Project Name'),
                ),
                TextField(
                  controller: urlController,
                  decoration: const InputDecoration(labelText: 'Repository URL (e.g. https://github.com/owner/repo)'),
                ),
                TextField(
                  controller: tokenController,
                  decoration: const InputDecoration(labelText: 'GitHub Token (if private)'),
                  obscureText: true,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () async {
                final url = urlController.text.trim();
                final parts = url.split('/');
                if (parts.length < 2) return;
                final repoName = parts.last.replaceAll('.git', '');
                final owner = parts[parts.length - 2];
                
                try {
                  await _client.connectRepository(
                    projectNameController.text.trim(),
                    url,
                    tokenController.text.trim(),
                    owner,
                    repoName,
                  );
                  if (!context.mounted) return;
                  Navigator.pop(context);
                  _loadProjects();
                } catch (e) {
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
                }
              },
              child: const Text('Connect'),
            ),
          ],
        );
      }
    );
  }
}
