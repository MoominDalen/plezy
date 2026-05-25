import '../../database/app_database.dart';
import '../../media/media_item.dart';
import '../../media/media_kind.dart';
import '../../media/media_server_client.dart';
import '../../media/media_source_info.dart';
import '../../services/cached_playback_metadata_service.dart';
import '../../services/introdb_service.dart';
import '../../services/settings_service.dart';
import '../../utils/app_logger.dart';
import '../../utils/global_key_utils.dart';

class VideoControlsPlaybackExtrasLoader {
  final MediaItem metadata;
  final MediaServerClient? client;
  final AppDatabase database;
  final IntroDbService _introDb;

  VideoControlsPlaybackExtrasLoader({
    required this.metadata,
    required this.database,
    required this.client,
    IntroDbService? introDb,
  }) : _introDb = introDb ?? IntroDbService();

  Future<PlaybackExtras?> load({bool forceRefresh = false}) async {
    if (client == null) {
      return _loadFromCacheOnly(cacheServerId: await _resolveCacheServerId());
    }

    try {
      appLogger.d('_loadPlaybackExtras: starting for ${metadata.id} (forceRefresh=$forceRefresh)');
      final settings = await SettingsService.getInstance();
      var extras = await client!.fetchPlaybackExtras(
        metadata.id,
        introPattern: settings.read(SettingsService.introPattern),
        creditsPattern: settings.read(SettingsService.creditsPattern),
        forceChapterFallback: settings.read(SettingsService.forceSkipMarkerFallback),
        forceRefresh: forceRefresh,
      );
      extras = await _enrichWithIntroDb(extras, settings);
      appLogger.d('_loadPlaybackExtras: got ${extras.chapters.length} chapters, ${extras.markers.length} markers');
      return extras;
    } catch (e, stack) {
      appLogger.d('_loadPlaybackExtras: network path failed, trying cache fallback');
      try {
        final settings = await SettingsService.getInstance();
        var extras = await client!.fetchPlaybackExtrasFromCacheOnly(
          metadata.id,
          introPattern: settings.read(SettingsService.introPattern),
          creditsPattern: settings.read(SettingsService.creditsPattern),
          forceChapterFallback: settings.read(SettingsService.forceSkipMarkerFallback),
        );
        if (extras != null) {
          extras = await _enrichWithIntroDb(extras, settings);
          appLogger.d('_loadPlaybackExtras: loaded ${extras.chapters.length} chapters from cache');
          return extras;
        }
      } catch (cacheError) {
        appLogger.d('_loadPlaybackExtras: cache fallback failed', error: cacheError);
      }
      appLogger.e('_loadPlaybackExtras failed', error: e, stackTrace: stack);
      return null;
    }
  }

  Future<PlaybackExtras> _enrichWithIntroDb(PlaybackExtras extras, SettingsService settings) async {
    if (!settings.read(SettingsService.enableIntroDb)) return extras;
    if (metadata.kind != MediaKind.episode) return extras;

    final season = metadata.parentIndex;
    final episode = metadata.index;
    if (season == null || episode == null) return extras;

    try {
      final external = await client!.fetchExternalIds(metadata.id);
      final imdb = external.imdb;
      if (imdb == null || imdb.isEmpty) return extras;

      final introDbMarkers = await _introDb.fetchSegments(imdbId: imdb, season: season, episode: episode);
      if (introDbMarkers.isEmpty) return extras;

      return PlaybackExtras(
        chapters: extras.chapters,
        markers: mergeIntroDbMarkers(native: extras.markers, introDb: introDbMarkers),
      );
    } catch (e) {
      appLogger.d('_loadPlaybackExtras: IntroDB enrichment skipped', error: e);
      return extras;
    }
  }

  Future<PlaybackExtras?> _loadFromCacheOnly({required String? cacheServerId}) async {
    if (cacheServerId == null) {
      appLogger.w('_loadPlaybackExtras: no client or cache scope for server ${metadata.serverId}');
      return null;
    }
    try {
      final settings = await SettingsService.getInstance();
      return CachedPlaybackMetadataService.fetchPlaybackExtras(
        backend: metadata.backend,
        cacheServerId: cacheServerId,
        itemId: metadata.id,
        introPattern: settings.read(SettingsService.introPattern),
        creditsPattern: settings.read(SettingsService.creditsPattern),
        forceChapterFallback: settings.read(SettingsService.forceSkipMarkerFallback),
      );
    } catch (e) {
      appLogger.d('_loadPlaybackExtras: cache-only path failed', error: e);
      return null;
    }
  }

  Future<String?> _resolveCacheServerId() async {
    final serverId = metadata.serverId;
    if (serverId == null) return null;
    try {
      final row = await (database.select(
        database.downloadedMedia,
      )..where((tbl) => tbl.globalKey.equals(buildGlobalKey(serverId, metadata.id)))).getSingleOrNull();
      return row?.clientScopeId ?? serverId;
    } catch (_) {
      return serverId;
    }
  }
}
