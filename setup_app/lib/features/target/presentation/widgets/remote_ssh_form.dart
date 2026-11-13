import 'package:flutter/material.dart';
import '../../../../core/theme/uno_palette.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/widgets/app_text_field.dart';
import '../../domain/target_config.dart';

class RemoteSshForm extends StatefulWidget {
  final TargetConfig config;
  final ValueChanged<TargetConfig> onChanged;

  const RemoteSshForm({
    super.key,
    required this.config,
    required this.onChanged,
  });

  @override
  State<RemoteSshForm> createState() => _RemoteSshFormState();
}

class _RemoteSshFormState extends State<RemoteSshForm> {
  late final TextEditingController _hostController;
  late final TextEditingController _portController;
  late final TextEditingController _userController;
  late final TextEditingController _keyPathController;
  late final TextEditingController _passwordController;
  bool _usePassword = false;

  @override
  void initState() {
    super.initState();
    _hostController = TextEditingController(text: widget.config.host == 'localhost' ? '' : widget.config.host);
    _portController = TextEditingController(text: widget.config.port.toString());
    _userController = TextEditingController(text: widget.config.username);
    _keyPathController = TextEditingController(text: widget.config.privateKeyPath ?? '~/.ssh/id_rsa');
    _passwordController = TextEditingController(text: widget.config.password ?? '');
    _usePassword = widget.config.password != null && widget.config.password!.isNotEmpty;
  }

  @override
  void dispose() {
    _hostController.dispose();
    _portController.dispose();
    _userController.dispose();
    _keyPathController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _notify() {
    widget.onChanged(
      widget.config.copyWith(
        host: _hostController.text.trim(),
        port: int.tryParse(_portController.text.trim()) ?? 22,
        username: _userController.text.trim(),
        privateKeyPath: _usePassword ? null : _keyPathController.text.trim(),
        password: _usePassword ? _passwordController.text : null,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: palette.bgElevated,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: palette.div),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.terminal_rounded, size: 16, color: palette.accent),
              const SizedBox(width: 8),
              Text(
                'SSH Connection Details',
                style: AppTextStyles.h3Of(context).copyWith(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                flex: 3,
                child: AppTextField(
                  label: 'Server Host / IP',
                  hintText: 'e.g. 192.168.1.100 or server.internal',
                  controller: _hostController,
                  onChanged: (_) => _notify(),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 1,
                child: AppTextField(
                  label: 'Port',
                  hintText: '22',
                  controller: _portController,
                  keyboardType: TextInputType.number,
                  onChanged: (_) => _notify(),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          AppTextField(
            label: 'SSH Username',
            hintText: 'e.g. root or ubuntu',
            controller: _userController,
            onChanged: (_) => _notify(),
          ),
          const SizedBox(height: 14),
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            runSpacing: 8,
            children: [
              Text(
                'Authentication Method:',
                style: AppTextStyles.labelOf(context).copyWith(
                  color: palette.textSec,
                  fontWeight: FontWeight.w500,
                ),
              ),
              _buildAuthChoice(
                label: 'SSH Key',
                isSelected: !_usePassword,
                onTap: () {
                  setState(() => _usePassword = false);
                  _notify();
                },
              ),
              _buildAuthChoice(
                label: 'Password',
                isSelected: _usePassword,
                onTap: () {
                  setState(() => _usePassword = true);
                  _notify();
                },
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (!_usePassword)
            AppTextField(
              label: 'Private Key Path',
              hintText: '~/.ssh/id_rsa',
              controller: _keyPathController,
              onChanged: (_) => _notify(),
            )
          else
            AppTextField(
              label: 'SSH Password',
              hintText: '••••••••',
              obscureText: true,
              controller: _passwordController,
              onChanged: (_) => _notify(),
            ),
        ],
      ),
    );
  }

  Widget _buildAuthChoice({
    required String label,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    final palette = UnoPalette.of(context);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? palette.accent.withValues(alpha: 0.15) : palette.bgSurface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? palette.accent : palette.div,
          ),
        ),
        child: Text(
          label,
          style: AppTextStyles.labelOf(context).copyWith(
            color: isSelected ? palette.accent : palette.textSec,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}
