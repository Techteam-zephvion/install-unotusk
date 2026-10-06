import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/status_badge.dart';
import '../domain/project.dart';
import 'project_members_controller.dart';

class ManageProjectTeamDialog extends ConsumerStatefulWidget {
  final Project project;

  const ManageProjectTeamDialog({
    super.key,
    required this.project,
  });

  @override
  ConsumerState<ManageProjectTeamDialog> createState() =>
      _ManageProjectTeamDialogState();
}

class _ManageProjectTeamDialogState
    extends ConsumerState<ManageProjectTeamDialog> {
  final _emailController = TextEditingController();
  String _selectedRole = 'MEMBER';
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _handleAddMember() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      setState(() => _errorMessage = 'Please enter an employee email address.');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    final notifier =
        ref.read(projectMembersControllerProvider(widget.project.id).notifier);
    final success = await notifier.addMember(
      email: email,
      role: _selectedRole,
    );

    if (mounted) {
      setState(() => _isSubmitting = false);
      if (success) {
        _emailController.clear();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Added $email to project team.'),
            backgroundColor: AppColors.success,
          ),
        );
      } else {
        setState(() => _errorMessage =
            'Failed to add member. Ensure the user belongs to your organization and is not already assigned.');
      }
    }
  }

  Future<void> _handleRemoveMember(String userId, String memberName) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove Team Member'),
        content: Text('Remove $memberName from this project? They will lose access to its codebase context and findings.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    final notifier =
        ref.read(projectMembersControllerProvider(widget.project.id).notifier);
    final success = await notifier.removeMember(userId);

    if (mounted) {
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Removed $memberName from project.'),
            backgroundColor: AppColors.success,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to remove member.'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final membersAsync =
        ref.watch(projectMembersControllerProvider(widget.project.id));
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Dialog(
      backgroundColor: Theme.of(context).cardColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isDark ? AppColors.divider : AppColors.dividerLight,
        ),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620, maxHeight: 680),
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Project Access & Team', style: AppTextStyles.h2),
                        const SizedBox(height: 4),
                        Text(
                          'Manage who can view and query ${widget.project.name}',
                          style: AppTextStyles.bodySmall,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 20),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Add Member Section
              AppCard(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Assign Colleague', style: AppTextStyles.h3),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: AppTextField(
                            controller: _emailController,
                            hint: 'colleague@company.com',
                            prefixIcon: const Icon(Icons.email_outlined, size: 16),
                            onEditingComplete: _handleAddMember,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: isDark ? AppColors.divider : AppColors.dividerLight,
                            ),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<String>(
                              value: _selectedRole,
                              items: const [
                                DropdownMenuItem(value: 'MEMBER', child: Text('Member')),
                                DropdownMenuItem(value: 'ADMIN', child: Text('Admin')),
                              ],
                              onChanged: (val) {
                                if (val != null) setState(() => _selectedRole = val);
                              },
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        AppButton(
                          text: 'Add',
                          icon: Icons.person_add_outlined,
                          isLoading: _isSubmitting,
                          onPressed: _handleAddMember,
                        ),
                      ],
                    ),
                    if (_errorMessage != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        _errorMessage!,
                        style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Member List Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Assigned Team Members', style: AppTextStyles.label),
                  membersAsync.maybeWhen(
                    data: (members) => Text(
                      '${members.length} total',
                      style: AppTextStyles.bodySmall,
                    ),
                    orElse: () => const SizedBox.shrink(),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Members List
              Expanded(
                child: membersAsync.when(
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (err, _) => Center(
                    child: Text(
                      'Failed to load members: $err',
                      style: const TextStyle(color: AppColors.error),
                    ),
                  ),
                  data: (members) {
                    if (members.isEmpty) {
                      return const Center(
                        child: Text('No members assigned yet.'),
                      );
                    }

                    return ListView.separated(
                      itemCount: members.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final member = members[index];
                        final initial = (member.displayName.isNotEmpty
                                ? member.displayName[0]
                                : 'M')
                            .toUpperCase();

                        return Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 10,
                          ),
                          decoration: BoxDecoration(
                            color: isDark ? AppColors.bgElevated : AppColors.slate50,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: isDark ? AppColors.divider : AppColors.dividerLight,
                            ),
                          ),
                          child: Row(
                            children: [
                              CircleAvatar(
                                radius: 16,
                                backgroundColor: AppColors.primary.withValues(alpha: 0.2),
                                child: Text(
                                  initial,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                    color: AppColors.primary,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      member.displayName,
                                      style: AppTextStyles.bodyMedium.copyWith(
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    if (member.userEmail != null)
                                      Text(
                                        member.userEmail!,
                                        style: AppTextStyles.bodySmall.copyWith(
                                          color: isDark
                                              ? AppColors.textSecondary
                                              : AppColors.textSecondaryLight,
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                              StatusBadge(
                                label: member.role.toUpperCase(),
                                variant: member.isAdmin
                                    ? BadgeVariant.info
                                    : BadgeVariant.neutral,
                              ),
                              const SizedBox(width: 8),
                              IconButton(
                                icon: const Icon(
                                  Icons.remove_circle_outline,
                                  size: 18,
                                  color: AppColors.error,
                                ),
                                tooltip: 'Remove from project',
                                onPressed: () => _handleRemoveMember(
                                  member.userId,
                                  member.displayName,
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

              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerRight,
                child: AppButton(
                  text: 'Done',
                  variant: AppButtonVariant.secondary,
                  onPressed: () => Navigator.pop(context),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
