class TaskItem {
  final String id;
  final String title;
  final String time;
  final String category; // 'Deep Focus' | 'Rescheduled' | 'Personal' | 'Email' | 'General'
  final String source; // 'From Gmail' | 'From Calendar' | 'From WhatsApp' | 'Heard at 08:42 AM'
  final bool isCompleted;
  final bool isCurrent;
  final double? progress; // e.g. 0.40 for 40%
  final String? focusTimer; // e.g. '25:00'
  final List<String> actions;
  final String? notes;

  const TaskItem({
    required this.id,
    required this.title,
    required this.time,
    required this.category,
    required this.source,
    this.isCompleted = false,
    this.isCurrent = false,
    this.progress,
    this.focusTimer,
    this.actions = const [],
    this.notes,
  });

  TaskItem copyWith({
    String? id,
    String? title,
    String? time,
    String? category,
    String? source,
    bool? isCompleted,
    bool? isCurrent,
    double? progress,
    String? focusTimer,
    List<String>? actions,
    String? notes,
  }) {
    return TaskItem(
      id: id ?? this.id,
      title: title ?? this.title,
      time: time ?? this.time,
      category: category ?? this.category,
      source: source ?? this.source,
      isCompleted: isCompleted ?? this.isCompleted,
      isCurrent: isCurrent ?? this.isCurrent,
      progress: progress ?? this.progress,
      focusTimer: focusTimer ?? this.focusTimer,
      actions: actions ?? this.actions,
      notes: notes ?? this.notes,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'time': time,
      'category': category,
      'source': source,
      'isCompleted': isCompleted,
      'isCurrent': isCurrent,
      'progress': progress,
      'focusTimer': focusTimer,
      'actions': actions,
      'notes': notes,
    };
  }

  factory TaskItem.fromJson(Map<String, dynamic> json) {
    return TaskItem(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      time: json['time'] ?? '',
      category: json['category'] ?? 'General',
      source: json['source'] ?? 'Manual',
      isCompleted: json['isCompleted'] ?? false,
      isCurrent: json['isCurrent'] ?? false,
      progress: (json['progress'] as num?)?.toDouble(),
      focusTimer: json['focusTimer'],
      actions: (json['actions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [],
      notes: json['notes'],
    );
  }
}
