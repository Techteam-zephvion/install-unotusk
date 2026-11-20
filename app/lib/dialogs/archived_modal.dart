import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class ArchivedModal extends StatefulWidget {
  final UnoPalette palette;
  final VoidCallback onClose;
  final Function(dynamic)? onSelectChat;

  const ArchivedModal({
    super.key,
    required this.palette,
    required this.onClose,
    this.onSelectChat,
  });

  @override
  State<ArchivedModal> createState() => _ArchivedModalState();
}

class _ArchivedModalState extends State<ArchivedModal> {
  List<ArchivedChat> _chats = [];
  String _search = '';

  @override
  void initState() {
    super.initState();
    _loadChats();
  }

  void _loadChats() async {
    final list = await ApiService.fetchArchivedChats();
    if (mounted) {
      setState(() => _chats = list);
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _chats
        .where((c) => c.title.toLowerCase().contains(_search.toLowerCase()))
        .toList();

    return Material(
      color: Colors.black.withValues(alpha: 0.55),
      child: Center(
        child: Container(
          width: 560,
          constraints: const BoxConstraints(maxHeight: 580),
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: widget.palette.bgSurface,
            border: Border.all(color: widget.palette.div),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.36),
                blurRadius: 60,
                offset: const Offset(0, 24),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 18, 20, 18),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Icon(
                          LucideIcons.archive,
                          size: 18,
                          color: widget.palette.accent,
                        ),
                        const SizedBox(width: 9),
                        Text(
                          'Archived chats',
                          style: UnoTypography.body(
                            color: widget.palette.text,
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    IconButton(
                      icon: Icon(LucideIcons.x,
                          size: 18, color: widget.palette.textSec),
                      onPressed: widget.onClose,
                    ),
                  ],
                ),
              ),
              Divider(height: 1, thickness: 1, color: widget.palette.div),

              // Search
              Padding(
                padding: const EdgeInsets.all(16),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: widget.palette.bgElevated,
                    border: Border.all(color: widget.palette.div),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(LucideIcons.search,
                          size: 14, color: widget.palette.textSec),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          onChanged: (val) => setState(() => _search = val),
                          style: UnoTypography.body(
                            color: widget.palette.text,
                            fontSize: 13,
                          ),
                          decoration: InputDecoration(
                            hintText: 'Search archived chats...',
                            hintStyle: UnoTypography.body(
                              color: widget.palette.textSec,
                              fontSize: 13,
                            ),
                            border: InputBorder.none,
                            isDense: true,
                            contentPadding:
                                const EdgeInsets.symmetric(vertical: 10),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Divider(height: 1, thickness: 1, color: widget.palette.div),

              // List
              Flexible(
                child: filtered.isEmpty
                    ? Padding(
                        padding: const EdgeInsets.symmetric(vertical: 48),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(LucideIcons.archive,
                                size: 32, color: widget.palette.textSec),
                            const SizedBox(height: 10),
                            Text(
                              'No archived chats found',
                              style: UnoTypography.body(
                                color: widget.palette.textSec,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        shrinkWrap: true,
                        padding: const EdgeInsets.all(16),
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final item = filtered[index];
                          return Container(
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 14, vertical: 12),
                            decoration: BoxDecoration(
                              color: widget.palette.bgElevated,
                              border: Border.all(color: widget.palette.div),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: InkWell(
                                    onTap: widget.onSelectChat != null
                                        ? () {
                                            widget.onClose();
                                            widget.onSelectChat!(item.id);
                                          }
                                        : null,
                                    borderRadius: BorderRadius.circular(8),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item.title,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: UnoTypography.body(
                                            color: widget.palette.text,
                                            fontSize: 13,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                        const SizedBox(height: 3),
                                        Text(
                                          'Archived ${item.date} · ${item.messages} messages',
                                          style: UnoTypography.mono(
                                            color: widget.palette.textSec,
                                            fontSize: 11,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton(
                                  onPressed: () async {
                                    setState(() {
                                      _chats.removeWhere(
                                          (c) => c.id == item.id);
                                    });
                                    await ApiService.archiveConversation(
                                        item.id.toString(),
                                        archive: false);
                                  },
                                  style: OutlinedButton.styleFrom(
                                    side: BorderSide(color: widget.palette.div),
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 6),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(16),
                                    ),
                                  ),
                                  child: Text(
                                    'Unarchive',
                                    style: UnoTypography.body(
                                      color: widget.palette.text,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 4),
                                IconButton(
                                  icon: const Icon(LucideIcons.trash2,
                                      size: 15, color: Color(0xFFEF4444)),
                                  onPressed: () async {
                                    final confirm = await showDialog<bool>(
                                      context: context,
                                      builder: (ctx) => AlertDialog(
                                        backgroundColor: widget.palette.bgSurface,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(16),
                                          side: BorderSide(color: widget.palette.div),
                                        ),
                                        title: Text('Delete conversation?',
                                            style: UnoTypography.body(
                                                color: widget.palette.text,
                                                fontWeight: FontWeight.w600,
                                                fontSize: 16)),
                                        content: Text(
                                            'Are you sure you want to delete "${item.title}"? This cannot be undone.',
                                            style: UnoTypography.body(
                                                color: widget.palette.textSec,
                                                fontSize: 13)),
                                        actions: [
                                          TextButton(
                                            onPressed: () => Navigator.of(ctx).pop(false),
                                            child: Text('Cancel',
                                                style: UnoTypography.body(
                                                    color: widget.palette.textSec,
                                                    fontSize: 13)),
                                          ),
                                          FilledButton(
                                            style: FilledButton.styleFrom(
                                                backgroundColor:
                                                    const Color(0xFFEF4444)),
                                            onPressed: () => Navigator.of(ctx).pop(true),
                                            child: Text('Delete',
                                                style: UnoTypography.body(
                                                    color: Colors.white,
                                                    fontWeight: FontWeight.w600,
                                                    fontSize: 13)),
                                          ),
                                        ],
                                      ),
                                    );
                                    if (confirm == true) {
                                      setState(() {
                                        _chats.removeWhere(
                                            (c) => c.id == item.id);
                                      });
                                      await ApiService.deleteConversation(
                                          item.id.toString());
                                    }
                                  },
                                ),
                              ],
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
