import 'dart:convert';

import 'package:http/http.dart' as http;

import '../media/media_source_info.dart';
import '../utils/app_logger.dart';

/// Fetches intro, recap, and outro segments from [IntroDB](https://introdb.app).
class IntroDbService {
  IntroDbService({http.Client? client}) : _client = client ?? http.Client();

  static const _baseUrl = 'https://api.introdb.app';

  final http.Client _client;

  /// Returns markers for the given TV episode, or empty when none are known.
  Future<List<MediaMarker>> fetchSegments({
    required String imdbId,
    required int season,
    required int episode,
  }) async {
    final uri = Uri.parse('$_baseUrl/segments').replace(
      queryParameters: {
        'imdb_id': imdbId,
        'season': season.toString(),
        'episode': episode.toString(),
      },
    );

    try {
      final response = await _client.get(uri, headers: const {'Accept': 'application/json'});
      if (response.statusCode == 404) return const [];
      if (response.statusCode != 200) {
        appLogger.d('IntroDB: HTTP ${response.statusCode} for $uri');
        return const [];
      }

      final body = jsonDecode(response.body);
      if (body is! Map<String, dynamic>) return const [];

      final markers = <MediaMarker>[];
      var id = -1000;

      void addSegment(String type, Map<String, dynamic>? segment) {
        if (segment == null) return;
        final startMs = segment['start_ms'] as int? ?? _valueToMs(segment['start_sec']);
        final endMs = segment['end_ms'] as int? ?? _valueToMs(segment['end_sec']);
        if (startMs == null || endMs == null || endMs <= startMs) return;
        markers.add(
          MediaMarker(id: id--, type: type, startTimeOffset: startMs, endTimeOffset: endMs),
        );
      }

      addSegment('intro', body['intro'] as Map<String, dynamic>?);
      addSegment('recap', body['recap'] as Map<String, dynamic>?);
      addSegment('credits', body['outro'] as Map<String, dynamic>?);

      markers.sort((a, b) => a.startTimeOffset.compareTo(b.startTimeOffset));
      return markers;
    } catch (e, stack) {
      appLogger.d('IntroDB fetch failed', error: e, stackTrace: stack);
      return const [];
    }
  }

  static int? _valueToMs(Object? value) {
    if (value == null) return null;
    if (value is int) return value * 1000;
    if (value is num) return (value * 1000).round();
    if (value is String) {
      if (value.contains(':')) {
        final parts = value.split(':');
        final nums = parts.map((p) => int.tryParse(p)).toList();
        if (nums.any((n) => n == null)) return null;
        var seconds = 0;
        for (final n in nums) {
          seconds = seconds * 60 + n!;
        }
        return seconds * 1000;
      }
      final seconds = int.tryParse(value);
      return seconds == null ? null : seconds * 1000;
    }
    return null;
  }
}

/// Merges [native] markers with [introDb] segments. Native markers win when they
/// share a type; IntroDB fills missing types only.
List<MediaMarker> mergeIntroDbMarkers({
  required List<MediaMarker> native,
  required List<MediaMarker> introDb,
}) {
  if (introDb.isEmpty) return native;
  if (native.isEmpty) return introDb;

  final nativeTypes = native.map((m) => m.type).toSet();
  final merged = <MediaMarker>[
    ...native,
    ...introDb.where((m) => !nativeTypes.contains(m.type)),
  ];
  merged.sort((a, b) => a.startTimeOffset.compareTo(b.startTimeOffset));
  return merged;
}
