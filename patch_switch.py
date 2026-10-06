import re
with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'r') as f:
    content = f.read()

content = content.replace("case ServerState.unknown:\n        break;", "case ServerState.unknown:\n        break;\n      case ServerState.starting:\n        statusColor = AppColors.primary;\n        statusText = 'Starting';\n        break;")

with open('setup_app/lib/features/manager/presentation/server_manager_screen.dart', 'w') as f:
    f.write(content)
