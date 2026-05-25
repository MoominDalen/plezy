import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show KeyDownEvent, LogicalKeyboardKey;
import 'package:material_symbols_icons/symbols.dart';

import '../../../focus/focusable_wrapper.dart';
import '../../../i18n/strings.g.dart';
import '../../../media/media_source_info.dart';
import '../../../theme/mono_tokens.dart';
import '../segment_marker_colors.dart';
import '../../app_icon.dart';

/// Skip intro / recap / credits and play-next actions shown during playback.
class SegmentSkipButtons extends StatelessWidget {
  final MediaMarker? currentMarker;
  final List<MediaMarker> markers;
  final Duration position;
  final Duration playerDuration;
  final bool hasNextEpisode;
  final bool isAutoSkipActive;
  final bool shouldShowAutoSkip;
  final int autoSkipDelay;
  final double autoSkipProgress;
  final FocusNode focusNode;
  final VoidCallback onCancelAutoSkip;
  final VoidCallback onSkipIntro;
  final VoidCallback onSkipRecap;
  final VoidCallback onSkipCredits;
  final VoidCallback onNextEpisode;
  final VoidCallback onFocusDown;

  const SegmentSkipButtons({
    super.key,
    required this.currentMarker,
    required this.markers,
    required this.position,
    required this.playerDuration,
    required this.hasNextEpisode,
    required this.isAutoSkipActive,
    required this.shouldShowAutoSkip,
    required this.autoSkipDelay,
    required this.autoSkipProgress,
    required this.focusNode,
    required this.onCancelAutoSkip,
    required this.onSkipIntro,
    required this.onSkipRecap,
    required this.onSkipCredits,
    required this.onNextEpisode,
    required this.onFocusDown,
  });

  MediaMarker? _markerOfType(String type) {
    for (final m in markers) {
      if (m.type == type) return m;
    }
    return null;
  }

  bool _isInMarker(MediaMarker marker) => marker.containsPosition(position);

  bool _showNextEpisode(MediaMarker? credits) {
    if (!hasNextEpisode) return false;
    if (credits != null && _isInMarker(credits)) return true;
    if (playerDuration <= Duration.zero) return false;
    final remaining = playerDuration - position;
    return remaining <= const Duration(seconds: 90);
  }

  @override
  Widget build(BuildContext context) {
    final intro = _markerOfType('intro');
    final recap = _markerOfType('recap');
    final credits = _markerOfType('credits');

    final buttons = <_SegmentButtonSpec>[];

    if (intro != null && _isInMarker(intro)) {
      buttons.add(
        _SegmentButtonSpec(
          label: t.videoControls.skipIntro,
          icon: Symbols.fast_forward_rounded,
          color: segmentMarkerColor('intro'),
          onPressed: onSkipIntro,
          marker: intro,
        ),
      );
    }

    if (recap != null && _isInMarker(recap)) {
      buttons.add(
        _SegmentButtonSpec(
          label: t.videoControls.skipRecap,
          icon: Symbols.fast_forward_rounded,
          color: segmentMarkerColor('recap'),
          onPressed: onSkipRecap,
          marker: recap,
        ),
      );
    }

    if (credits != null && _isInMarker(credits) && !_showNextEpisode(credits)) {
      buttons.add(
        _SegmentButtonSpec(
          label: t.videoControls.skipCredits,
          icon: Symbols.fast_forward_rounded,
          color: segmentMarkerColor('credits'),
          onPressed: onSkipCredits,
          marker: credits,
        ),
      );
    }

    if (_showNextEpisode(credits)) {
      buttons.add(
        _SegmentButtonSpec(
          label: t.videoControls.nextEpisode,
          icon: Symbols.skip_next_rounded,
          color: segmentMarkerColor('credits'),
          onPressed: onNextEpisode,
          marker: credits,
        ),
      );
    }

    if (buttons.isEmpty) return const SizedBox.shrink();

    return Focus(
      focusNode: focusNode,
      onKeyEvent: (node, event) {
        if (event is KeyDownEvent && event.logicalKey == LogicalKeyboardKey.arrowDown) {
          onFocusDown();
          return KeyEventResult.handled;
        }
        return KeyEventResult.ignored;
      },
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        spacing: 8,
        children: [
          for (final spec in buttons)
            _SegmentActionButton(
              spec: spec,
              isAutoSkipActive: isAutoSkipActive && currentMarker == spec.marker,
              shouldShowAutoSkip: shouldShowAutoSkip && currentMarker == spec.marker,
              autoSkipDelay: autoSkipDelay,
              autoSkipProgress: autoSkipProgress,
              onCancelAutoSkip: onCancelAutoSkip,
            ),
        ],
      ),
    );
  }
}

class _SegmentButtonSpec {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onPressed;
  final MediaMarker? marker;

  const _SegmentButtonSpec({
    required this.label,
    required this.icon,
    required this.color,
    required this.onPressed,
    this.marker,
  });
}

class _SegmentActionButton extends StatelessWidget {
  final _SegmentButtonSpec spec;
  final bool isAutoSkipActive;
  final bool shouldShowAutoSkip;
  final int autoSkipDelay;
  final double autoSkipProgress;
  final VoidCallback onCancelAutoSkip;

  const _SegmentActionButton({
    required this.spec,
    required this.isAutoSkipActive,
    required this.shouldShowAutoSkip,
    required this.autoSkipDelay,
    required this.autoSkipProgress,
    required this.onCancelAutoSkip,
  });

  @override
  Widget build(BuildContext context) {
    final remainingSeconds = isAutoSkipActive && shouldShowAutoSkip
        ? (autoSkipDelay - (autoSkipProgress * autoSkipDelay)).ceil().clamp(0, autoSkipDelay)
        : 0;

    final buttonText = isAutoSkipActive && shouldShowAutoSkip && remainingSeconds > 0
        ? '${spec.label} ($remainingSeconds)'
        : spec.label;

    return FocusableWrapper(
      onSelect: () {
        if (isAutoSkipActive) onCancelAutoSkip();
        spec.onPressed();
      },
      borderRadius: tokens(context).radiusSm,
      useBackgroundFocus: true,
      autoScroll: false,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            if (isAutoSkipActive) onCancelAutoSkip();
            spec.onPressed();
          },
          borderRadius: BorderRadius.circular(tokens(context).radiusSm),
          child: Stack(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.92),
                  borderRadius: BorderRadius.circular(tokens(context).radiusSm),
                  border: Border.all(color: spec.color.withValues(alpha: 0.85), width: 2),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 8, offset: const Offset(0, 2)),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(color: spec.color, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      buttonText,
                      style: const TextStyle(color: Colors.black, fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(width: 8),
                    AppIcon(spec.icon, fill: 1, color: Colors.black, size: 20),
                  ],
                ),
              ),
              if (isAutoSkipActive && shouldShowAutoSkip)
                Positioned.fill(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(tokens(context).radiusSm),
                    child: Row(
                      children: [
                        Expanded(
                          flex: (autoSkipProgress * 100).round(),
                          child: Container(
                            decoration: BoxDecoration(
                              color: spec.color.withValues(alpha: 0.25),
                              borderRadius: BorderRadius.circular(tokens(context).radiusSm),
                            ),
                          ),
                        ),
                        Expanded(
                          flex: ((1.0 - autoSkipProgress) * 100).round(),
                          child: const SizedBox.shrink(),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
