import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

class AppTextField extends StatelessWidget {
  final String? label;
  final String? hintText;
  final String? helperText;
  final String? errorText;
  final TextEditingController? controller;
  final bool obscureText;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onChanged;
  final FormFieldValidator<String>? validator;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final bool enabled;
  final int maxLines;

  const AppTextField({
    super.key,
    this.label,
    this.hintText,
    this.helperText,
    this.errorText,
    this.controller,
    this.obscureText = false,
    this.keyboardType,
    this.onChanged,
    this.validator,
    this.prefixIcon,
    this.suffixIcon,
    this.enabled = true,
    this.maxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (label != null) ...[
          Text(label!, style: AppTextStyles.label),
          const SizedBox(height: 6),
        ],
        TextFormField(
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          onChanged: onChanged,
          validator: validator,
          enabled: enabled,
          maxLines: maxLines,
          style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate900),
          decoration: InputDecoration(
            hintText: hintText,
            errorText: errorText,
            prefixIcon: prefixIcon,
            suffixIcon: suffixIcon,
            helperText: helperText,
            helperStyle: AppTextStyles.bodySmall,
          ),
        ),
      ],
    );
  }
}
