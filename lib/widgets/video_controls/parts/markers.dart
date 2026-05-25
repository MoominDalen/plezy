part of '../video_controls.dart';

extension _PlexVideoControlsMarkerMethods on _PlexVideoControlsState {
  void _listenToPosition() {
    _positionSubscription = widget.player.streams.position.listen((position) {
      if (_markers.isEmpty || !_markersLoaded) {
        return;
      }

      _playbackPosition = position;

      MediaMarker? foundMarker;
      for (final marker in _markers) {
        if (marker.containsPosition(position)) {
          foundMarker = marker;
          break;
        }
      }

      if (foundMarker != _currentMarker && mounted) {
        _updateCurrentMarker(foundMarker);
      } else if (mounted) {
        // Rebuild segment buttons when position changes within/out of segments.
        _setControlsState(() {});
      }
    });
  }

  /// Updates the current marker and manages auto-skip/focus behavior.
  void _updateCurrentMarker(MediaMarker? foundMarker) {
    _setControlsState(() {
      _currentMarker = foundMarker;
      _skipButtonDismissed = false;
    });

    if (foundMarker == null) {
      _cancelAutoSkipTimer();
      _cancelSkipButtonDismissTimer();
      return;
    }

    _startAutoSkipTimer(foundMarker);

    if (!_shouldAutoSkipForMarker(foundMarker)) {
      _startSkipButtonDismissTimer();
    }

    if (PlatformDetector.isTV() && InputModeTracker.isKeyboardMode(context)) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          _skipMarkerFocusNode.requestFocus();
        }
      });
    }
  }

  Future<void> _skipMarker(MediaMarker marker, {bool skipAutoPlayCountdown = false}) async {
    final endTime = marker.endTime;
    final duration = widget.player.state.duration;
    final isAtEnd = duration > Duration.zero && (duration - endTime).inMilliseconds <= 1000;

    if (marker.isCredits && isAtEnd) {
      if (!skipAutoPlayCountdown && widget.onNext != null) {
        widget.onNext!.call();
      } else {
        await widget.player.pause();
        widget.onReachedEnd?.call(skipAutoPlayCountdown: skipAutoPlayCountdown);
      }
    } else {
      await _seekToPosition(endTime);
    }

    if (!mounted) return;
    _setControlsState(() {
      _currentMarker = null;
    });
    _cancelAutoSkipTimer();
    _cancelSkipButtonDismissTimer();
  }

  Future<void> _skipMarkerByType(String type) async {
    for (final marker in _markers) {
      if (marker.type == type) {
        await _skipMarker(marker);
        return;
      }
    }
  }

  void _playNextEpisode() {
    if (widget.onNext != null) {
      widget.onNext!.call();
      return;
    }
    unawaited(_skipMarkerByType('credits'));
  }

  void _startAutoSkipTimer(MediaMarker marker) {
    _cancelAutoSkipTimer();

    final shouldAutoSkip = _shouldAutoSkipForMarker(marker);

    if (!shouldAutoSkip || _autoSkipDelay <= 0) return;

    _autoSkipProgress = 0.0;
    const tickDuration = Duration(milliseconds: 200);
    final totalTicks = (_autoSkipDelay * 1000) / tickDuration.inMilliseconds;

    if (totalTicks <= 0) return;

    _autoSkipTimer = Timer.periodic(tickDuration, (timer) {
      if (!mounted || _currentMarker != marker) {
        timer.cancel();
        return;
      }

      _setControlsState(() {
        _autoSkipProgress = (timer.tick / totalTicks).clamp(0.0, 1.0);
      });

      if (timer.tick >= totalTicks) {
        timer.cancel();
        _performAutoSkip(skipAutoPlayCountdown: true);
      }
    });
  }

  void _cancelAutoSkipTimer() {
    _autoSkipTimer?.cancel();
    _autoSkipTimer = null;
    if (mounted) {
      _setControlsState(() {
        _autoSkipProgress = 0.0;
      });
    }
  }

  void _startSkipButtonDismissTimer() {
    _skipButtonDismissTimer?.cancel();
    _skipButtonDismissTimer = Timer(const Duration(seconds: 7), () {
      if (!mounted || _currentMarker == null) return;
      _setControlsState(() {
        _skipButtonDismissed = true;
      });
      _cancelAutoSkipTimer();
    });
  }

  void _cancelSkipButtonDismissTimer() {
    _skipButtonDismissTimer?.cancel();
    _skipButtonDismissTimer = null;
  }

  void _performAutoSkip({bool skipAutoPlayCountdown = false}) {
    if (_currentMarker == null) return;
    unawaited(_skipMarker(_currentMarker!, skipAutoPlayCountdown: skipAutoPlayCountdown));
  }

  bool _shouldAutoSkipForMarker(MediaMarker marker) {
    if (marker.isCredits) return _autoSkipCredits;
    if (marker.isRecap) return _autoSkipRecap;
    if (marker.isIntro) return _autoSkipIntro;
    return false;
  }

  bool _shouldShowAutoSkip() {
    if (_currentMarker == null) return false;
    return _shouldAutoSkipForMarker(_currentMarker!);
  }

  Widget _buildSegmentSkipButtons() {
    final isAutoSkipActive = _autoSkipTimer?.isActive ?? false;
    return SegmentSkipButtons(
      currentMarker: _currentMarker,
      markers: _markers,
      position: _playbackPosition,
      playerDuration: widget.player.state.duration,
      hasNextEpisode: widget.onNext != null,
      isAutoSkipActive: isAutoSkipActive,
      shouldShowAutoSkip: _shouldShowAutoSkip(),
      autoSkipDelay: _autoSkipDelay,
      autoSkipProgress: _autoSkipProgress,
      focusNode: _skipMarkerFocusNode,
      onCancelAutoSkip: _cancelAutoSkipTimer,
      onSkipIntro: () => unawaited(_skipMarkerByType('intro')),
      onSkipRecap: () => unawaited(_skipMarkerByType('recap')),
      onSkipCredits: () => unawaited(_skipMarkerByType('credits')),
      onNextEpisode: _playNextEpisode,
      onFocusDown: () => _desktopControlsKey.currentState?.requestPlayPauseFocus(),
    );
  }
}
