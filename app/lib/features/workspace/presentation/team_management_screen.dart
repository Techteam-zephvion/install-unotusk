import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/desktop_scaffold.dart';
import '../../../core/widgets/empty_state_view.dart';
import '../../../core/widgets/error_state_view.dart';
import '../../../core/widgets/loading_state_view.dart';
import '../../../core/widgets/status_badge.dart';
import '../../auth/presentation/auth_controller.dart';
import 'team_controller.dart';

class TeamManagementScreen extends ConsumerStatefulWidget {
  const TeamManagementScreen({super.key});

  @override
  ConsumerState<TeamManagementScreen> createState() =>
      _TeamManagementScreenState();
}

class _TeamManagementScreenState extends ConsumerState<TeamManagementScreen> {
  final _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final membersAsync = ref.watch(organizationMembersProvider);
    final authState = ref.watch(authControllerProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return DesktopScaffold(
      currentRoute: '/team',
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Page Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Team & Organization', style: AppTextStyles.h1),
                    const SizedBox(height: 4),
                    Text(
                      'Manage colleagues and role-based permissions in your workspace',
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
                AppButton(
                  text: 'Refresh Roster',
                  icon: Icons.refresh,
                  variant: AppButtonVariant.secondary,
                  onPressed: () => ref.refresh(organizationMembersProvider),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Metrics Cards
            membersAsync.maybeWhen(
              data: (members) {
                final total = members.length;
                final admins = members.where((m) => m.isAdmin).length;
                final regularMembers = total - admins;

                return Row(
                  children: [
                    Expanded(
                      child: _MetricCard(
                        title: 'Total Members',
                        value: total.toString(),
                        subtitle: 'Registered accounts',
                        icon: Icons.people_outline,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _MetricCard(
                        title: 'Administrators',
                        value: admins.toString(),
                        subtitle: 'Owners & Admins',
                        icon: Icons.admin_panel_settings_outlined,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _MetricCard(
                        title: 'Developers',
                        value: regularMembers.toString(),
                        subtitle: 'Project-scoped members',
                        icon: Icons.code_outlined,
                      ),
                    ),
                  ],
                );
              },
              orElse: () => const SizedBox.shrink(),
            ),
            const SizedBox(height: 20),

            // Search Bar
            SizedBox(
              width: 340,
              child: AppTextField(
                controller: _searchController,
                hint: 'Filter team by name or email...',
                prefixIcon: const Icon(Icons.search, size: 16),
                onChanged: (val) {
                  setState(() {
                    _searchQuery = val.trim().toLowerCase();
                  });
                },
              ),
            ),
            const SizedBox(height: 16),

            // Members List
            Expanded(
              child: membersAsync.when(
                loading: () =>
                    const LoadingStateView(message: 'Loading team members...'),
                error: (err, _) => ErrorStateView(
                  message: err.toString(),
                  onRetry: () => ref.refresh(organizationMembersProvider),
                ),
                data: (members) {
                  final filtered = members.where((m) {
                    if (_searchQuery.isEmpty) return true;
                    return m.displayName.toLowerCase().contains(_searchQuery) ||
                        m.userEmail.toLowerCase().contains(_searchQuery) ||
                        m.role.toLowerCase().contains(_searchQuery);
                  }).toList();

                  if (filtered.isEmpty) {
                    return EmptyStateView(
                      icon: Icons.person_search_outlined,
                      title: _searchQuery.isEmpty
                          ? 'No team members found'
                          : 'No matching members',
                      description: _searchQuery.isEmpty
                          ? 'No members registered under this organization yet.'
                          : 'Try adjusting your search terms.',
                    );
                  }

                  return ListView.separated(
                    itemCount: filtered.length,
                    separatorBuilder: (_, unused) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final member = filtered[index];
                      final isCurrentUser = member.userId == authState.user?.id;
                      final initial = (member.displayName.isNotEmpty
                              ? member.displayName[0]
                              : 'U')
                          .toUpperCase();

                      return AppCard(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 14,
                        ),
                        child: Row(
                          children: [
                            CircleAvatar(
                              radius: 18,
                              backgroundColor: AppColors.primary.withValues(alpha: 0.2),
                              child: Text(
                                initial,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                  color: AppColors.primary,
                                ),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Text(
                                        member.displayName,
                                        style: AppTextStyles.h3,
                                      ),
                                      if (isCurrentUser) ...[
                                        const SizedBox(width: 8),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 6,
                                            vertical: 2,
                                          ),
                                          decoration: BoxDecoration(
                                            color: AppColors.primary
                                                .withValues(alpha: 0.15),
                                            borderRadius:
                                                BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            'YOU',
                                            style: TextStyle(
                                              fontSize: 9,
                                              fontWeight: FontWeight.bold,
                                              color: AppColors.primary,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    member.userEmail,
                                    style: AppTextStyles.bodySmall,
                                  ),
                                ],
                              ),
                            ),
                            StatusBadge(
                              label: member.role.toUpperCase(),
                              variant: member.isOwner
                                  ? BadgeVariant.confirmed
                                  : member.isAdmin
                                      ? BadgeVariant.info
                                      : BadgeVariant.neutral,
                            ),
                            const SizedBox(width: 16),
                            Text(
                              'Joined ${_formatDate(member.createdAt)}',
                              style: AppTextStyles.bodySmall.copyWith(
                                color: isDark
                                    ? AppColors.textSecondary
                                    : AppColors.textSecondaryLight,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final String subtitle;
  final IconData icon;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              icon,
              size: 20,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(width: 14),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: AppTextStyles.bodySmall.copyWith(fontSize: 11),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: AppTextStyles.h2.copyWith(fontSize: 18),
              ),
              Text(
                subtitle,
                style: AppTextStyles.bodySmall.copyWith(
                  fontSize: 10,
                  color: isDark
                      ? AppColors.textSecondary
                      : AppColors.textSecondaryLight,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
