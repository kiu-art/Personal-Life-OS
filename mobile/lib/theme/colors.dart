import 'package:flutter/material.dart';

/// Bixy "Nocturne Editorial" palette.
///
/// Ink-black paper, warm bone text, one marigold sun, one mint breath.
/// Dominant ink + bone, sharp mint/marigold accents — no purple-on-white cliché.
class BixyColors {
  // Base Surfaces (warm ink, not blue-navy)
  static const Color background = Color(0xFF0A0908);
  static const Color surface = Color(0xFF141210);
  static const Color surfaceLight = Color(0xFF1D1A16);
  static const Color surfaceBorder = Color(0x26F6F0E4);
  static const Color surfaceBorderSubtle = Color(0x14F6F0E4);

  // Accent Colors
  static const Color accentGreen = Color(0xFF2BFF88);
  static const Color accentGreenMuted = Color(0xFF0A2B1D);
  static const Color accentGreenGlow = Color(0x552BFF88);

  static const Color accentAmber = Color(0xFFFFB224);
  static const Color accentAmberMuted = Color(0xFF2B1D0E);
  static const Color accentAmberGlow = Color(0x44FFB224);

  static const Color accentPurple = Color(0xFFB79CFF);
  static const Color accentPurpleMuted = Color(0xFF22173D);

  static const Color accentBlue = Color(0xFF7CD4FC);
  static const Color accentBlueMuted = Color(0xFF0F253E);

  static const Color clayRose = Color(0xFFFF6B4A);

  // Text Hierarchy (warm bone, not cold slate)
  static const Color textPrimary = Color(0xFFF6F0E4);
  static const Color textSecondary = Color(0xFFB8AE9C);
  static const Color textMuted = Color(0xFF7A7264);
  static const Color textDark = Color(0xFF051A11);

  // Surfaces, bone-tinted
  static const Color cardDeep = Color(0xFF12100D);
  static const Color cardRaised = Color(0xFF191612);
  static const Color cardInset = Color(0xFF0C0B09);

  // Timeline & States
  static const Color timelineLine = Color(0xFF2A251E);
  static const Color liveIndicator = Color(0xFF2BFF88);

  // Aurora washes for the masthead / shade backgrounds
  static const Color auroraMint = Color(0xFF123B28);
  static const Color auroraAmber = Color(0xFF3B2708);
  static const Color auroraClay = Color(0xFF3B1A10);
}

/// Shared motion + shape tokens so every screen breathes at the same tempo.
class BixyMotion {
  static const Duration fast = Duration(milliseconds: 180);
  static const Duration medium = Duration(milliseconds: 320);
  static const Duration slow = Duration(milliseconds: 560);
  static const Duration breath = Duration(milliseconds: 4200);

  static const Curve easeOut = Curves.easeOutCubic;
  static const Curve easeInOut = Curves.easeInOutCubic;
  static const Curve spring = Curves.elasticOut;

  static const double radiusCard = 20;
  static const double radiusSheet = 28;
  static const double radiusPill = 100;
}
