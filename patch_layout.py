import re

with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'r') as f:
    content = f.read()

# Replace the Row of buttons with Wrap
pattern = r"else if \(server.lastKnownState == ServerState.running \|\| server.lastKnownState == ServerState.degraded\)\s*Row\(\s*children: \[\s*AppButton\(\s*label: 'Copy URL'.*?\]\s*,\s*\),"

replacement = """              else if (server.lastKnownState == ServerState.running || server.lastKnownState == ServerState.degraded)
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.end,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    AppButton(
                      label: 'Copy URL',
                      icon: Icons.copy,
                      onPressed: () => _copyUrl(server, context),
                    ),
                    AppButton(
                      label: 'Restart',
                      variant: AppButtonVariant.secondary,
                      icon: Icons.refresh,
                      onPressed: () => notifier.restartServer(server),
                    ),
                    AppButton(
                      label: 'Manage Repos',
                      variant: AppButtonVariant.secondary,
                      icon: Icons.folder,
                      onPressed: () {
                        Navigator.push(context, MaterialPageRoute(
                          builder: (_) => RepositoryManagerScreen(server: server)
                        ));
                      },
                    ),
                    AppButton(
                      label: 'Stop',
                      variant: AppButtonVariant.destructive,
                      icon: Icons.stop,
                      onPressed: () => notifier.stopServer(server),
                    ),
                  ],
                ),"""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'w') as f:
    f.write(new_content)
