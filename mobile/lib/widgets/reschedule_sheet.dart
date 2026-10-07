import 'package:flutter/material.dart';

class RescheduleSheet extends StatefulWidget {
  final int initialShiftMinutes;
  final Function(int newShiftMinutes) onShiftApplied;

  const RescheduleSheet({
    super.key,
    required this.initialShiftMinutes,
    required this.onShiftApplied,
  });

  @override
  State<RescheduleSheet> createState() => _RescheduleSheetState();
}

class _RescheduleSheetState extends State<RescheduleSheet> {
  late int _currentShift;

  final List<int> _quickPresets = [-30, -15, 0, 15, 30, 40, 60, 90];

  @override
  void initState() {
    super.initState();
    _currentShift = widget.initialShiftMinutes;
  }

  String get _readout {
    if (_currentShift > 0) return '+$_currentShift min';
    if (_currentShift < 0) return '$_currentShift min';
    return 'On time';
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
              Text('Move day', style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  )),
              IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text(
                  _readout,
                  style: theme.textTheme.displaySmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: _currentShift == 0
                        ? scheme.onSurface
                        : scheme.tertiary,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _quickPresets.map((mins) {
              final label = mins == 0
                  ? 'Reset'
                  : mins > 0
                      ? '+$mins'
                      : '$mins';
              return ChoiceChip(
                label: Text(label),
                selected: _currentShift == mins,
                onSelected: (val) {
                  if (val) setState(() => _currentShift = mins);
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () {
                widget.onShiftApplied(_currentShift);
                Navigator.of(context).pop();
              },
              child: const Text('Apply'),
            ),
          ),
        ],
      ),
    );
  }
}
