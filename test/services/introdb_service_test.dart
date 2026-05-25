import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:plezy/media/media_source_info.dart';
import 'package:plezy/services/introdb_service.dart';

void main() {
  group('IntroDbService', () {
    test('parses intro, recap, and outro from API response', () async {
      final client = MockClient((request) async {
        expect(request.url.host, 'api.introdb.app');
        return http.Response(
          '''
          {
            "imdb_id": "tt0944947",
            "season": 1,
            "episode": 2,
            "intro": {"start_ms": 6000, "end_ms": 105000},
            "recap": {"start_sec": 0, "end_sec": 30},
            "outro": {"start_ms": 3252000, "end_ms": 3320000}
          }
          ''',
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = IntroDbService(client: client);
      final markers = await service.fetchSegments(imdbId: 'tt0944947', season: 1, episode: 2);

      expect(markers.map((m) => m.type), ['recap', 'intro', 'credits']);
      expect(markers[0].startTimeOffset, 0);
      expect(markers[0].endTimeOffset, 30000);
      expect(markers[1].startTimeOffset, 6000);
      expect(markers[1].endTimeOffset, 105000);
      expect(markers[2].startTimeOffset, 3252000);
      expect(markers[2].endTimeOffset, 3320000);
    });

    test('mergeIntroDbMarkers keeps native types and fills gaps', () {
      final native = [
        MediaMarker(id: 1, type: 'intro', startTimeOffset: 1000, endTimeOffset: 90000),
      ];
      final introDb = [
        MediaMarker(id: -1, type: 'intro', startTimeOffset: 5000, endTimeOffset: 80000),
        MediaMarker(id: -2, type: 'recap', startTimeOffset: 0, endTimeOffset: 4000),
        MediaMarker(id: -3, type: 'credits', startTimeOffset: 100000, endTimeOffset: 120000),
      ];

      final merged = mergeIntroDbMarkers(native: native, introDb: introDb);
      expect(merged.map((m) => m.type), ['recap', 'intro', 'credits']);
      expect(merged.firstWhere((m) => m.type == 'intro').startTimeOffset, 1000);
    });
  });
}
