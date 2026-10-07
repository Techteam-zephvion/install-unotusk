import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/organization_repository.dart';
import '../domain/organization_member.dart';

final organizationMembersProvider =
    FutureProvider<List<OrganizationMember>>((ref) async {
  final authState = ref.watch(authControllerProvider);
  final orgId = authState.user?.organizationId;
  if (orgId == null || orgId.isEmpty) {
    return [];
  }
  final repository = ref.watch(organizationRepositoryProvider);
  return repository.getOrganizationMembers(orgId);
});
