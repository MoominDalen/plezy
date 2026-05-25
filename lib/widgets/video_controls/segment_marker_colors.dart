import 'package:flutter/material.dart';

/// Timeline and button accent colors for intro / recap / credits segments.
Color segmentMarkerColor(String type) {
  return switch (type) {
    'intro' => const Color(0xFF3B82F6),
    'recap' => const Color(0xFFF59E0B),
    'credits' => const Color(0xFF8B5CF6),
    _ => const Color(0xFF6B7280),
  };
}
