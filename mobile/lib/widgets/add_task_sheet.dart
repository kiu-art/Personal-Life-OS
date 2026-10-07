import 'package:flutter/material.dart';
import '../models/task_item.dart';

class AddTaskSheet extends StatefulWidget {
  final Function(TaskItem newTask) onTaskAdded;

  const AddTaskSheet({
    super.key,
    required this.onTaskAdded,
  });

  @override
  State<AddTaskSheet> createState() => _AddTaskSheetState();
}

class _AddTaskSheetState extends State<AddTaskSheet> {
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _timeController =
      TextEditingController(text: '16:30');
  String _category = 'Deep Focus';
  String _source = 'Manual';

  final List<String> _categories = [
    'Deep Focus',
    'Personal',
    'Email',
    'General'
  ];
  final List<String> _sources = [
    'WhatsApp',
    'Gmail',
    'Calendar',
    'Voice Note',
    'Manual'
  ];

  @override
  void dispose() {
    _titleController.dispose();
    _timeController.dispose();
    super.dispose();
  }

  void _save() {
    final title = _titleController.text.trim();
    if (title.isEmpty) return;

    final newTask = TaskItem(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: title,
      time: _timeController.text.trim(),
      category: _category,
      source: _source,
      actions: const ['Mark Done', 'Reschedule'],
    );

    widget.onTaskAdded(newTask);
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;

    return Container(
      padding: EdgeInsets.only(
        top: 12,
        left: 20,
        right: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 38,
              height: 4,
              decoration: BoxDecoration(
                color: scheme.onSurfaceVariant.withOpacity(0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('New task', style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  )),
              IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _titleController,
            style: theme.textTheme.bodyLarge,
            decoration: const InputDecoration(
              hintText: 'Title',
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _timeController,
            style: theme.textTheme.bodyLarge
                ?.copyWith(fontFamily: 'monospace'),
            decoration: const InputDecoration(
              hintText: 'Time (HH:MM)',
              prefixIcon: Icon(Icons.schedule_rounded, size: 20),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _categories.map((cat) {
              return ChoiceChip(
                label: Text(cat),
                selected: _category == cat,
                onSelected: (val) {
                  if (val) setState(() => _category = cat);
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _sources.map((src) {
              final isSel = _source == src;
              return FilterChip(
                label: Text(src),
                selected: isSel,
                onSelected: (val) {
                  if (val) setState(() => _source = src);
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _save,
              child: const Text('Add task'),
            ),
          ),
        ],
      ),
    );
  }
}
