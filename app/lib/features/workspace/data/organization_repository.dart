import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../domain/organization_member.dart';

final organizationRepositoryProvider = Provider<OrganizationRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OrganizationRepository(apiClient);
});

class OrganizationRepository {
  final ApiClient _apiClient;

  OrganizationRepository(this._apiClient);

  Future<List<OrganizationMember>> getOrganizationMembers(String organizationId) async {
    final response = await _apiClient.get(ApiEndpoints.organizationMembers(organizationId));
    final data = response.data;
    if (data is List) {
      return data
          .map((item) => OrganizationMember.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }
    return [];
  }
}
