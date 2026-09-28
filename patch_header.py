import re
with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'r') as f:
    content = f.read()

pattern = r"Row\(\s*mainAxisAlignment: MainAxisAlignment.spaceBetween,\s*children: \[\s*Text\('Unotusk Server Manager', style: AppTextStyles.h1\),\s*AppButton\(\s*label: 'Add Server'.*?\],\s*\),"
replacement = """Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: 16,
                  runSpacing: 16,
                  children: [
                    Text('Unotusk Server Manager', style: AppTextStyles.h1),
                    AppButton(
                      label: 'Add Server',
                      icon: Icons.add,
                      onPressed: () => _startNewServerWizard(context, ref),
                    ),
                  ],
                ),"""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'w') as f:
    f.write(new_content)
