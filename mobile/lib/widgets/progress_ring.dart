import 'package:flutter/material.dart';

// Adapted from `tasky` by Youssef Awad Sadek (MIT License):
// lib/features/home/widgets/progress_ring.dart
// A circular progress indicator with a percentage label in the center.
// Pure presentation: pass a [progress] value in [0, 1].
class ProgressRing extends StatelessWidget {
  const ProgressRing({
    required this.progress,
    this.size = 104,
    this.strokeWidth = 11,
    super.key,
  });

  final double progress;
  final double size;
  final double strokeWidth;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final double clamped = progress.clamp(0.0, 1.0);
    final int percent = (clamped * 100).round();

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: <Widget>[
          SizedBox.expand(
            child: TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0, end: clamped),
              duration: const Duration(milliseconds: 600),
              curve: Curves.easeOutCubic,
              builder: (BuildContext context, double value, _) {
                return CircularProgressIndicator(
                  value: value,
                  strokeWidth: strokeWidth,
                  strokeCap: StrokeCap.round,
                  backgroundColor:
                      theme.colorScheme.surfaceContainerHighest,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    theme.colorScheme.primary,
                  ),
                );
              },
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text(
                '$percent%',
                style: theme.textTheme.headlineSmall
                    ?.copyWith(fontWeight: FontWeight.w700),
              ),
              Text(
                'done',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
