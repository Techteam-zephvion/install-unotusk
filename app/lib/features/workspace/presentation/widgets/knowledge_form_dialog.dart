import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/project_knowledge.dart';

class KnowledgeFormDialog extends StatefulWidget {
  final ProjectKnowledge? initialItem;
  final Future<void> Function({
    required String category,
    required String title,
    required String content,
    String? relatedFilePath,
    String? relatedSymbol,
  }) onSave;

  const KnowledgeFormDialog({
    super.key,
    this.initialItem,
    required this.onSave,
  });

  @override
  State<KnowledgeFormDialog> createState() => _KnowledgeFormDialogState();
}

class _KnowledgeFormDialogState extends State<KnowledgeFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late String _category;
  late final TextEditingController _titleController;
  late final TextEditingController _contentController;
  late final TextEditingController _filePathController;
  late final TextEditingController _symbolController;
  bool _isSaving = false;

  final _categories = const [
    'ARCHITECTURE_DECISION',
    'BUSINESS_RULE',
    'INTENT',
    'CONSTRAINT',
    'EXCEPTION',
    'LEGACY_CONTEXT',
    'CRITICAL_COMPONENT',
    'TEMPORARY_STATE',
    'OTHER',
  ];

  @override
  void initState() {
    super.initState();
    _category = widget.initialItem?.category ?? 'ARCHITECTURE_DECISION';
    _titleController = TextEditingController(text: widget.initialItem?.title ?? '');
    _contentController = TextEditingController(text: widget.initialItem?.content ?? '');
    _filePathController = TextEditingController(text: widget.initialItem?.relatedFilePath ?? '');
    _symbolController = TextEditingController(text: widget.initialItem?.relatedSymbol ?? '');
  }

  @override
  void dispose() {
    _titleController.dispose();
    _contentController.dispose();
    _filePathController.dispose();
    _symbolController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSaving = true;
    });

    try {
      await widget.onSave(
        category: _category,
        title: _titleController.text.trim(),
        content: _contentController.text.trim(),
        relatedFilePath: _filePathController.text.trim().isNotEmpty
            ? _filePathController.text.trim()
            : null,
        relatedSymbol: _symbolController.text.trim().isNotEmpty
            ? _symbolController.text.trim()
            : null,
      );
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save knowledge item: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isEditing = widget.initialItem != null;

    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      backgroundColor: Colors.white,
      child: Container(
        width: 580,
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Row(
                children: [
                  Text(
                    isEditing ? 'Edit Knowledge Item' : 'Add Project Knowledge',
                    style: AppTextStyles.h2.copyWith(fontSize: 16, color: AppColors.slate900),
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close, size: 16, color: AppColors.slate500),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Category Selector
              Text('Category', style: AppTextStyles.bodySmall.copyWith(fontWeight: FontWeight.w600, color: AppColors.slate700)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.slate300),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _category,
                    isExpanded: true,
                    style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate900),
                    items: _categories.map((c) {
                      return DropdownMenuItem(
                        value: c,
                        child: Text(c.replaceAll('_', ' ')),
                      );
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) {
                        setState(() {
                          _category = val;
                        });
                      }
                    },
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // Title Field
              Text('Title', style: AppTextStyles.bodySmall.copyWith(fontWeight: FontWeight.w600, color: AppColors.slate700)),
              const SizedBox(height: 4),
              TextFormField(
                controller: _titleController,
                style: AppTextStyles.bodyMedium,
                decoration: InputDecoration(
                  hintText: 'e.g., Use Connection Pooling for all Outbound HTTP',
                  hintStyle: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate400),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate300)),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate900)),
                ),
                validator: (val) => val == null || val.trim().isEmpty ? 'Title is required' : null,
              ),
              const SizedBox(height: 12),

              // Content Field
              Text('Content / Engineering Context', style: AppTextStyles.bodySmall.copyWith(fontWeight: FontWeight.w600, color: AppColors.slate700)),
              const SizedBox(height: 4),
              TextFormField(
                controller: _contentController,
                maxLines: 4,
                style: AppTextStyles.bodyMedium,
                decoration: InputDecoration(
                  hintText: 'Document architectural intent, business rules, or team conventions...',
                  hintStyle: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate400),
                  contentPadding: const EdgeInsets.all(12),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate300)),
                  focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate900)),
                ),
                validator: (val) => val == null || val.trim().isEmpty ? 'Content is required' : null,
              ),
              const SizedBox(height: 12),

              // Related File & Symbol Row
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Related File (optional)', style: AppTextStyles.bodySmall.copyWith(fontWeight: FontWeight.w600, color: AppColors.slate700)),
                        const SizedBox(height: 4),
                        TextFormField(
                          controller: _filePathController,
                          style: AppTextStyles.code.copyWith(fontSize: 12),
                          decoration: InputDecoration(
                            hintText: 'src/requests/adapters.py',
                            hintStyle: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate300)),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Related Symbol (optional)', style: AppTextStyles.bodySmall.copyWith(fontWeight: FontWeight.w600, color: AppColors.slate700)),
                        const SizedBox(height: 4),
                        TextFormField(
                          controller: _symbolController,
                          style: AppTextStyles.code.copyWith(fontSize: 12),
                          decoration: InputDecoration(
                            hintText: 'HTTPAdapter',
                            hintStyle: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(6), borderSide: const BorderSide(color: AppColors.slate300)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Action Buttons
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: _isSaving ? null : () => Navigator.of(context).pop(),
                    child: Text('Cancel', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600)),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _isSaving ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.slate900,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                    ),
                    child: Text(
                      _isSaving ? 'Saving...' : (isEditing ? 'Update Item' : 'Add Item'),
                      style: AppTextStyles.bodyMedium.copyWith(color: Colors.white, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
