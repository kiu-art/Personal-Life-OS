import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/task_item.dart';
import '../models/ambient_state.dart';
import '../theme/bixy_theme.dart';
import '../widgets/task_tile.dart';
import '../widgets/progress_ring.dart';
import '../widgets/listening_icon.dart';
import '../widgets/bottom_nav_dock.dart';
import '../widgets/voice_dialog.dart';
import '../widgets/reschedule_sheet.dart';
import '../widgets/add_task_sheet.dart';
import 'settings_screen.dart';
import '../services/backend_service.dart';

class TodayScreen extends StatefulWidget {
  final AmbientState ambientState;
  final Function(AmbientState newState) onStateChanged;
  final VoidCallback onToggleListening;

  const TodayScreen({
    super.key,
    required this.ambientState,
    required this.onStateChanged,
    required this.onToggleListening,
  });

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  late List<TaskItem> _tasks;
  late BackendService _backend;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _backend = BackendService(baseUrl: widget.ambientState.backendBaseUrl);
    _initDefaultTasks();
    _loadScheduleFromBackend();
  }

  void _initDefaultTasks() {
    _tasks = [
      const TaskItem(
        id: 'task-1',
        title: 'Pay electricity bill',
        time: '08:55',
        category: 'Completed',
        source: 'Gmail',
        isCompleted: true,
      ),
      const TaskItem(
        id: 'task-2',
        title: 'Flutter auth flow',
        time: '09:40',
        category: 'Deep Focus',
        source: 'Calendar',
        isCurrent: true,
        progress: 0.40,
        focusTimer: '25:00',
        actions: ['Stop'],
      ),
      const TaskItem(
        id: 'task-3',
        title: 'Dev Team Standup',
        time: '11:30',
        category: 'Rescheduled',
        source: 'WhatsApp',
        actions: ['Mark Done', 'Reschedule', 'Snooze'],
      ),
      const TaskItem(
        id: 'task-4',
        title: 'Call Aai about Saturday',
        time: '13:15',
        category: 'Personal',
        source: 'Heard 08:42',
        actions: ['Call', 'Add Note', 'Reminder'],
      ),
      const TaskItem(
        id: 'task-5',
        title: 'Project update draft',
        time: '15:00',
        category: 'Email',
        source: 'Gmail',
        actions: ['Open', 'Mark Done', 'Snooze'],
      ),
    ];
  }

  /// Load real schedule from backend
  Future<void> _loadScheduleFromBackend() async {
    setState(() => _isLoading = true);
    final res = await _backend.fetchScheduleToday();
    final List<TaskItem> fetchedTasks = res['tasks'] as List<TaskItem>? ?? [];
    final String summary = res['summary'] as String? ?? '';

    if (mounted) {
      setState(() {
        _isLoading = false;
        if (fetchedTasks.isNotEmpty) {
          _tasks = fetchedTasks;
        }
      });

      if (summary.isNotEmpty) {
        final updatedState = widget.ambientState.copyWith(
          disruptionNotice: summary,
          tasksSyncedCount: _tasks.length,
        );
        widget.onStateChanged(updatedState);
      }
    }
  }

  /// Handle real voice commands (e.g. "Bixy: I woke up late", Hindi, Marathi)
  Future<void> _handleVoiceCommand(String command) async {
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      SnackBar(
        content: Text('Bixy: "$command"'),
        duration: const Duration(seconds: 2),
      ),
    );

    final res = await _backend.sendVoiceCheckIn(command);
    final bool disruptionDetected = res['disruption_detected'] == true;

    await _loadScheduleFromBackend();

    if (mounted) {
      if (disruptionDetected) {
        final updatedState = widget.ambientState.copyWith(
          rescheduledTodayCount: widget.ambientState.rescheduledTodayCount + 1,
          disruptionNotice: '"$command" — shifted +40 min.',
        );
        widget.onStateChanged(updatedState);
      }
    }
  }

  /// Shift agenda times via real backend API
  Future<void> _applyCadenceShift(int deltaMinutes, {String? reason}) async {
    setState(() {
      final updatedTasks = _tasks.map((t) {
        if (!t.isCompleted && !t.isCurrent) {
          final parts = t.time.split(':');
          if (parts.length == 2) {
            int h = int.tryParse(parts[0]) ?? 0;
            int m = int.tryParse(parts[1]) ?? 0;
            int totalM = h * 60 + m + (deltaMinutes > 0 ? 40 : deltaMinutes);
            int newH = (totalM ~/ 60) % 24;
            int newM = totalM % 60;
            final newTimeStr =
                '${newH.toString().padLeft(2, '0')}:${newM.toString().padLeft(2, '0')}';
            return t.copyWith(time: newTimeStr, category: 'Rescheduled');
          }
        }
        return t;
      }).toList();

      _tasks = updatedTasks;
    });

    await _backend.shiftSchedule(deltaMinutes, reason ?? 'Manual shift');
    await _loadScheduleFromBackend();

    if (mounted) {
      final updatedState = widget.ambientState.copyWith(
        dayShiftMinutes: deltaMinutes,
        rescheduledTodayCount: widget.ambientState.rescheduledTodayCount + 1,
        disruptionNotice: '"${reason ?? 'I woke up late'}" — shifted +$deltaMinutes min.',
      );
      widget.onStateChanged(updatedState);
    }
  }

  void _openVoiceModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => VoiceAssistantModal(
        onCommandProcessed: _handleVoiceCommand,
      ),
    );
  }

  void _openRescheduleSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => RescheduleSheet(
        initialShiftMinutes: widget.ambientState.dayShiftMinutes,
        onShiftApplied: (mins) => _applyCadenceShift(mins),
      ),
    );
  }

  void _openAddTaskSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => AddTaskSheet(
        onTaskAdded: (newTask) async {
          setState(() {
            _tasks.add(newTask);
            final updatedState = widget.ambientState.copyWith(
              tasksSyncedCount: _tasks.length,
            );
            widget.onStateChanged(updatedState);
          });

          final created = await _backend.createTask(
            title: newTask.title,
            time: newTask.time,
            category: newTask.category,
            source: newTask.source,
          );

          if (created != null && mounted) {
            setState(() {
              final idx = _tasks.indexWhere((t) => t.title == newTask.title);
              if (idx != -1) {
                _tasks[idx] = created;
              }
            });
          }
        },
      ),
    );
  }

  void _openSettings() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => SettingsScreen(
          ambientState: widget.ambientState,
          onStateChanged: widget.onStateChanged,
        ),
      ),
    );
  }

  Future<void> _toggleTaskCompleted(TaskItem task,
      {bool offerUndo = true}) async {
    final newCompleted = !task.isCompleted;
    setState(() {
      final idx = _tasks.indexWhere((t) => t.id == task.id);
      if (idx != -1) {
        _tasks[idx] = task.copyWith(
          isCompleted: newCompleted,
          category: newCompleted ? 'Completed' : 'Rescheduled',
        );
      }
    });

    if (newCompleted) {
      await _backend.completeTask(task.id);
    }

    if (mounted && offerUndo && newCompleted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('"${task.title}" done'),
          duration: const Duration(seconds: 4),
          action: SnackBarAction(
            label: 'Undo',
            onPressed: () {
              final idx = _tasks.indexWhere((t) => t.id == task.id);
              if (idx != -1) {
                _toggleTaskCompleted(_tasks[idx], offerUndo: false);
              }
            },
          ),
        ),
      );
    }
  }

  double get _dayProgress {
    if (_tasks.isEmpty) return 0;
    final done = _tasks.where((t) => t.isCompleted).length;
    final current = _tasks.where((t) => t.isCurrent).length;
    return ((done + current * 0.5) / _tasks.length).clamp(0.0, 1.0);
  }

  String _greeting() {
    final int hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final listening = widget.ambientState.isListeningActive;
    final doneCount = _tasks.where((t) => t.isCompleted).length;
    final movedCount =
        _tasks.where((t) => t.category == 'Rescheduled').length;

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            RefreshIndicator(
              onRefresh: _loadScheduleFromBackend,
              color: scheme.primary,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(_greeting(),
                                style: BixyTheme.display(30)),
                            const SizedBox(height: 2),
                            Text(
                              DateFormat('EEEE, d MMM')
                                  .format(DateTime.now()),
                              style: theme.textTheme.bodyMedium?.copyWith(
                                color: scheme.onSurfaceVariant,
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        onPressed:
                            _isLoading ? null : _loadScheduleFromBackend,
                        icon: _isLoading
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2),
                              )
                            : const Icon(Icons.refresh_rounded),
                      ),
                      const SizedBox(width: 4),
                      ListeningIcon(
                        listening: listening,
                        onTap: widget.onToggleListening,
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Card(
                    margin: EdgeInsets.zero,
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Row(
                        children: [
                          ProgressRing(progress: _dayProgress),
                          const SizedBox(width: 20),
                          Expanded(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                _StatLine(
                                  icon: Icons.check_circle_rounded,
                                  color: scheme.primary,
                                  text:
                                      '$doneCount of ${_tasks.length} done',
                                ),
                                const SizedBox(height: 10),
                                _StatLine(
                                  icon: Icons.calendar_month_rounded,
                                  color: scheme.tertiary,
                                  text: '$movedCount moved today',
                                ),
                                const SizedBox(height: 10),
                                _StatLine(
                                  icon: Icons.mic_rounded,
                                  color: listening
                                      ? scheme.primary
                                      : scheme.onSurfaceVariant,
                                  text: listening
                                      ? 'Hindi • English • मराठी'
                                      : 'Listening paused',
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: _openAddTaskSheet,
                          icon: const Icon(Icons.add_rounded),
                          label: const Text('Add task'),
                          style: FilledButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                                vertical: 14),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: _openVoiceModal,
                          icon: const Icon(Icons.mic_rounded),
                          label: const Text('Ask Bixy'),
                          style: FilledButton.styleFrom(
                            padding: const EdgeInsets.symmetric(
                                vertical: 14),
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (widget.ambientState.disruptionNotice != null) ...[
                    const SizedBox(height: 12),
                    Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
                        child: Row(
                          children: [
                            Icon(Icons.wb_sunny_rounded,
                                color: scheme.tertiary, size: 20),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                widget.ambientState.disruptionNotice!,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: theme.textTheme.bodyMedium,
                              ),
                            ),
                            TextButton(
                              onPressed: _openRescheduleSheet,
                              child: const Text('Adjust'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Today',
                          style: theme.textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w700)),
                      Text('${_tasks.length} tasks',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: scheme.onSurfaceVariant,
                          )),
                    ],
                  ),
                  const SizedBox(height: 8),
                  if (_tasks.isEmpty)
                    Card(
                      margin: EdgeInsets.zero,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            Icon(Icons.wb_sunny_rounded,
                                color: scheme.onSurfaceVariant),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'Nothing scheduled. Enjoy the quiet.',
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: scheme.onSurfaceVariant,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    ..._tasks.map(
                      (task) => BixyTaskTile(
                        key: ValueKey(task.id),
                        task: task,
                        onToggle: () => _toggleTaskCompleted(task),
                        onMove: _openRescheduleSheet,
                      ),
                    ),
                ],
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 24,
              child: Center(
                child: BottomNavDock(
                  isListening: listening,
                  onAddTask: _openAddTaskSheet,
                  onVoiceTrigger: _openVoiceModal,
                  onOpenSettings: _openSettings,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatLine extends StatelessWidget {
  const _StatLine({
    required this.icon,
    required this.color,
    required this.text,
  });

  final IconData icon;
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Icon(icon, size: 18, color: color),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }
}
