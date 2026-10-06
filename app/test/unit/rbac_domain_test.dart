import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/auth/domain/user.dart';
import 'package:app/features/auth/domain/auth_state.dart';
import 'package:app/features/projects/domain/project.dart';
import 'package:app/features/projects/domain/project_member.dart';
import 'package:app/features/workspace/domain/organization_member.dart';

void main() {
  group('User Role RBAC Getters', () {
    test('identifies OWNER role accurately', () {
      const user = User(
        id: 'usr-owner',
        email: 'owner@acme.com',
        fullName: 'Acme Owner',
        role: 'OWNER',
      );
      expect(user.isOwner, isTrue);
      expect(user.isAdmin, isTrue); // Owner has admin privileges
      expect(user.isMember, isFalse);
    });

    test('identifies ADMIN role accurately', () {
      const user = User(
        id: 'usr-admin',
        email: 'admin@acme.com',
        fullName: 'Acme Admin',
        role: 'ADMIN',
      );
      expect(user.isOwner, isFalse);
      expect(user.isAdmin, isTrue);
      expect(user.isMember, isFalse);
    });

    test('identifies MEMBER role accurately', () {
      const user = User(
        id: 'usr-member',
        email: 'dev@acme.com',
        fullName: 'Acme Dev',
        role: 'MEMBER',
      );
      expect(user.isOwner, isFalse);
      expect(user.isAdmin, isFalse);
      expect(user.isMember, isTrue);
    });
  });

  group('AuthState RBAC Getters', () {
    test('reflects underlying authenticated user permissions', () {
      const user = User(
        id: 'usr-admin',
        email: 'admin@acme.com',
        fullName: 'Admin',
        role: 'ADMIN',
      );
      final state = AuthState(
        status: AuthStatus.authenticated,
        user: user,
        token: 'tok-123',
      );
      expect(state.isAdmin, isTrue);
      expect(state.isOwner, isFalse);
      expect(state.userRole, 'ADMIN');
    });

    test('defaults to false for unauthenticated state', () {
      const state = AuthState(status: AuthStatus.unauthenticated);
      expect(state.isAdmin, isFalse);
      expect(state.isOwner, isFalse);
      expect(state.userRole, 'member');
    });
  });

  group('Project Role and Admin State', () {
    test('parses role from JSON and recognizes project admin', () {
      final json = {
        'id': 'proj-1',
        'name': 'Core Backend',
        'status': 'READY',
        'role': 'ADMIN',
        'created_at': '2026-10-06T00:00:00Z',
        'updated_at': '2026-10-06T00:00:00Z',
      };
      final project = Project.fromJson(json);
      expect(project.role, 'ADMIN');
      expect(project.isProjectAdmin, isTrue);
    });

    test('recognizes regular project member', () {
      final json = {
        'id': 'proj-2',
        'name': 'Client UI',
        'status': 'READY',
        'role': 'MEMBER',
        'created_at': '2026-10-06T00:00:00Z',
        'updated_at': '2026-10-06T00:00:00Z',
      };
      final project = Project.fromJson(json);
      expect(project.role, 'MEMBER');
      expect(project.isProjectAdmin, isFalse);
    });
  });

  group('ProjectMember Serialization & Properties', () {
    test('serializes and deserializes correctly', () {
      final json = {
        'id': 'pm-101',
        'project_id': 'proj-1',
        'user_id': 'usr-2',
        'role': 'ADMIN',
        'user_email': 'alice@acme.com',
        'user_name': 'Alice Engineer',
        'created_at': '2026-10-06T04:00:00Z',
      };

      final member = ProjectMember.fromJson(json);
      expect(member.id, 'pm-101');
      expect(member.projectId, 'proj-1');
      expect(member.userId, 'usr-2');
      expect(member.role, 'ADMIN');
      expect(member.userEmail, 'alice@acme.com');
      expect(member.displayName, 'Alice Engineer');
      expect(member.isAdmin, isTrue);
      expect(member.isMember, isFalse);

      final outJson = member.toJson();
      expect(outJson['id'], 'pm-101');
      expect(outJson['user_email'], 'alice@acme.com');
      expect(outJson['user_name'], 'Alice Engineer');
    });
  });

  group('OrganizationMember Serialization & Properties', () {
    test('serializes and deserializes correctly', () {
      final json = {
        'id': 'om-201',
        'organization_id': 'org-1',
        'user_id': 'usr-1',
        'role': 'OWNER',
        'user_email': 'ceo@acme.com',
        'user_name': 'CEO Founder',
        'created_at': '2026-10-01T00:00:00Z',
      };

      final member = OrganizationMember.fromJson(json);
      expect(member.id, 'om-201');
      expect(member.organizationId, 'org-1');
      expect(member.userId, 'usr-1');
      expect(member.role, 'OWNER');
      expect(member.userEmail, 'ceo@acme.com');
      expect(member.displayName, 'CEO Founder');
      expect(member.isOwner, isTrue);
      expect(member.isAdmin, isTrue);
      expect(member.isMember, isFalse);

      final outJson = member.toJson();
      expect(outJson['organization_id'], 'org-1');
      expect(outJson['role'], 'OWNER');
    });
  });
}
