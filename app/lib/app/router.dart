import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/connection/presentation/server_connection_screen.dart';
import '../features/projects/presentation/projects_screen.dart';
import '../features/settings/presentation/settings_screen.dart';
import '../features/workspace/presentation/workspace_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authControllerProvider);

  return GoRouter(
    initialLocation: '/projects',
    redirect: (BuildContext context, GoRouterState state) {
      final isAuth = authState.isAuthenticated;
      final isLoggingIn = state.matchedLocation == '/login';
      final isConfiguringServer = state.matchedLocation == '/connection';

      // Always allow server connection config
      if (isConfiguringServer) return null;

      // If not authenticated and not on login, go to login
      if (!isAuth && !isLoggingIn) {
        return '/login';
      }

      // If authenticated and on login, go to projects
      if (isAuth && isLoggingIn) {
        return '/projects';
      }

      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/connection',
        builder: (context, state) => const ServerConnectionScreen(),
      ),
      GoRoute(
        path: '/projects',
        builder: (context, state) => const ProjectsScreen(),
        routes: [
          GoRoute(
            path: ':id',
            builder: (context, state) {
              final projectId = state.pathParameters['id'] ?? '';
              return WorkspaceScreen(projectId: projectId);
            },
          ),
        ],
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
    ],
  );
});
