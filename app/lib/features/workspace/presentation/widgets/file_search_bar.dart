import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class FileSearchBar extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;
  final String hintText;

  const FileSearchBar({
    super.key,
    required this.controller,
    required this.onChanged,
    required this.onClear,
    this.hintText = 'Filter files by name or path...',
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 38,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.slate200),
      ),
      child: TextField(
        controller: controller,
        onChanged: onChanged,
        textAlignVertical: TextAlignVertical.center,
        style: AppTextStyles.bodyMedium.copyWith(fontSize: 13),
        decoration: InputDecoration(
          isDense: true,
          hintText: hintText,
          hintStyle: AppTextStyles.bodySmall.copyWith(
            color: AppColors.slate400,
            fontSize: 13,
          ),
          prefixIcon: const Icon(
            Icons.search,
            size: 18,
            color: AppColors.slate400,
          ),
          prefixIconConstraints: const BoxConstraints(minWidth: 36, minHeight: 38),
          suffixIcon: controller.text.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.close, size: 16, color: AppColors.slate500),
                  onPressed: () {
                    controller.clear();
                    onClear();
                  },
                )
              : null,
          suffixIconConstraints: const BoxConstraints(minWidth: 36, minHeight: 38),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.only(right: 12),
        ),
      ),
    );
  }
}
