import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Expanding voice pill, per the spec screenshot: white X button on the
/// left, live dot-waveform in the middle, solid send button on the right.
/// X collapses back to the mic; send confirms and opens the voice sheet.
class MicPill extends StatefulWidget {
  final bool isListening;
  final VoidCallback onClose;
  final VoidCallback onSend;

  const MicPill({
    super.key,
    required this.isListening,
    required this.onClose,
    required this.onSend,
  });

  @override
  State<MicPill> createState() => _MicPillState();
}

class _MicPillState extends State<MicPill>
    with SingleTickerProviderStateMixin {
  late AnimationController _wave;

  @override
  void initState() {
    super.initState();
    _wave = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    )..repeat();
  }

  @override
  void dispose() {
    _wave.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AnimatedBuilder(
      animation: _wave,
      builder: (context, _) {
        return Container(
          height: 62,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: scheme.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(40),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.45),
                blurRadius: 22,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // X: collapse back to mic
              GestureDetector(
                onTap: widget.onClose,
                child: Container(
                  width: 46,
                  height: 46,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                  ),
                  child: const Icon(Icons.close_rounded,
                      color: Colors.black, size: 24),
                ),
              ),
              // Live dot-waveform
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: List.generate(9, (i) {
                    final phase = _wave.value * 2 * math.pi;
                    final h = widget.isListening
                        ? 5 +
                            (math.sin(phase + i * 0.9).abs() * 13) +
                            (i == 4 ? 5 : 0)
                        : 4.0;
                    return Container(
                      width: 3.5,
                      height: h,
                      margin: EdgeInsets.only(
                          left: i == 0 ? 0 : 5),
                      decoration: BoxDecoration(
                        color: scheme.onSurface.withOpacity(
                            widget.isListening ? 0.92 : 0.35),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    );
                  }),
                ),
              ),
              // Send: confirm into the voice sheet
              GestureDetector(
                onTap: widget.onSend,
                child: Container(
                  width: 46,
                  height: 46,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Color(0xFF1E3A8A),
                  ),
                  child: const Icon(Icons.arrow_upward_rounded,
                      color: Colors.white, size: 24),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
