import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../features/wizard/presentation/wizard_shell.dart';
import '../features/manager/presentation/server_manager_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        name: 'manager',
        builder: (context, state) => const ServerManagerScreen(),
      ),
      GoRoute(
        path: '/wizard',
        name: 'wizard',
        builder: (context, state) => const WizardShell(),
      ),
    ],
  );
});
