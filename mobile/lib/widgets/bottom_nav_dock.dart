import 'package:flutter/material.dart';
import '../theme/colors.dart';
import 'mic_pill.dart';

class BottomNavDock extends StatefulWidget {
  final VoidCallback onAddTask;
  final VoidCallback onVoiceTrigger;
  final VoidCallback onOpenSettings;
  final bool isListening;

  const BottomNavDock({
    super.key,
    required this.onAddTask,
    required this.onVoiceTrigger,
    required this.onOpenSettings,
    this.isListening = true,
  });

  @override
  State<BottomNavDock> createState() => _BottomNavDockState();
}

class _BottomNavDockState extends State<BottomNavDock>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  bool _expanded = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF161310).withOpacity(0.94),
        borderRadius: BorderRadius.circular(40),
        border: Border.all(color: BixyColors.surfaceBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.5),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: AnimatedSize(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
        child: _expanded
            ? MicPill(
                isListening: widget.isListening,
                onClose: () => setState(() => _expanded = false),
                onSend: () {
                  setState(() => _expanded = false);
                  widget.onVoiceTrigger();
                },
              )
            : Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Add Task (+)
          _buildCircleButton(
            icon: Icons.add,
            onTap: widget.onAddTask,
          ),
          const SizedBox(width: 14),

          // Glowing Mic Button -> expands into the voice pill
          AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              final glowSpread = widget.isListening
                  ? 4.0 + _pulseController.value * 6.0
                  : 0.0;
              final glowBlur = widget.isListening
                  ? 14.0 + _pulseController.value * 8.0
                  : 4.0;

              return GestureDetector(
                onTap: () => setState(() => _expanded = true),
                child: Container(
                  width: 58,
                  height: 58,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: BixyColors.accentGreen,
                    boxShadow: [
                      BoxShadow(
                        color: BixyColors.accentGreen.withOpacity(0.55),
                        blurRadius: glowBlur,
                        spreadRadius: glowSpread,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.mic,
                      color: Color(0xFF03160D),
                      size: 28,
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(width: 14),

          // Settings (Gear)
          _buildCircleButton(
            icon: Icons.settings_outlined,
            onTap: widget.onOpenSettings,
          ),
        ],
      ),
      ),
    );
  }

  Widget _buildCircleButton({
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(24),
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: BixyColors.surfaceLight,
          border: Border.all(color: BixyColors.surfaceBorderSubtle),
        ),
        child: Icon(
          icon,
          color: BixyColors.textPrimary,
          size: 20,
        ),
      ),
    );
  }
}
