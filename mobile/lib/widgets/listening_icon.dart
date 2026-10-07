import 'package:flutter/material.dart';

/// Top-right listening indicator: a mic button wrapped in expanding pulse
/// rings while live, a quiet static button while paused. Tap toggles.
///
/// (Pulse-ring live indicator — the pattern used across OSS voice apps —
/// kept to one widget so the header stays text-free.)
class ListeningIcon extends StatefulWidget {
  final bool listening;
  final VoidCallback onTap;

  const ListeningIcon({
    super.key,
    required this.listening,
    required this.onTap,
  });

  @override
  State<ListeningIcon> createState() => _ListeningIconState();
}

class _ListeningIconState extends State<ListeningIcon>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );
    if (widget.listening) _pulse.repeat();
  }

  @override
  void didUpdateWidget(ListeningIcon old) {
    super.didUpdateWidget(old);
    if (widget.listening && !_pulse.isAnimating) {
      _pulse.repeat();
    } else if (!widget.listening && _pulse.isAnimating) {
      _pulse.stop();
    }
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: 46,
        height: 46,
        child: Stack(
          alignment: Alignment.center,
          children: [
            if (widget.listening)
              AnimatedBuilder(
                animation: _pulse,
                builder: (context, _) => CustomPaint(
                  size: const Size(46, 46),
                  painter: _PulsePainter(
                    progress: _pulse.value,
                    color: scheme.primary,
                  ),
                ),
              ),
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: widget.listening
                    ? scheme.primaryContainer
                    : scheme.surfaceContainerHighest.withOpacity(0.5),
              ),
              child: Icon(
                widget.listening
                    ? Icons.mic_rounded
                    : Icons.mic_none_rounded,
                size: 19,
                color: widget.listening
                    ? scheme.onPrimaryContainer
                    : scheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PulsePainter extends CustomPainter {
  final double progress;
  final Color color;

  _PulsePainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    // Two staggered expanding rings.
    for (final offset in [0.0, 0.5]) {
      final t = (progress + offset) % 1.0;
      final r = 12.0 + t * 11.0;
      canvas.drawCircle(
        center,
        r,
        Paint()
          ..color = color.withOpacity((1 - t) * 0.5)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _PulsePainter old) =>
      old.progress != progress || old.color != color;
}
