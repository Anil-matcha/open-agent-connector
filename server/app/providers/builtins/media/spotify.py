"""
Spotify Provider for ConnectorHub.
Loads and registers 88 actions from 'actions_catalog.json'.
Music catalog browsing, user library, and playback control via Spotify Web API.
"""
import urllib.parse
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

SPOTIFY_API_BASE = "https://api.spotify.com/v1"

SPOTIFY_ENDPOINT_MAP = {
    "spotify.add_item_to_playback_queue": [
        "POST",
        "/me/player/queue"
    ],
    "spotify.add_items_to_playlist": [
        "POST",
        "/playlists/{playlistId}/tracks"
    ],
    "spotify.change_playlist_details": [
        "PUT",
        "/playlists/{playlistId}"
    ],
    "spotify.check_saved_albums": [
        "GET",
        "/me/albums/contains"
    ],
    "spotify.check_saved_audiobooks": [
        "GET",
        "/me/audiobooks/contains"
    ],
    "spotify.check_saved_episodes": [
        "GET",
        "/me/episodes/contains"
    ],
    "spotify.check_saved_shows": [
        "GET",
        "/me/shows/contains"
    ],
    "spotify.check_saved_tracks": [
        "GET",
        "/me/tracks/contains"
    ],
    "spotify.check_user_follows_artists_or_users": [
        "GET",
        "/me/following/contains"
    ],
    "spotify.check_users_follow_playlist": [
        "GET",
        "/playlists/{playlistId}/followers/contains"
    ],
    "spotify.create_playlist": [
        "POST",
        "/users/{userId}/playlists"
    ],
    "spotify.follow_artists_or_users": [
        "PUT",
        "/me/following"
    ],
    "spotify.follow_playlist": [
        "PUT",
        "/playlists/{playlistId}/followers"
    ],
    "spotify.get_album": [
        "GET",
        "/albums/{albumId}"
    ],
    "spotify.get_album_tracks": [
        "GET",
        "/albums/{albumId}/tracks"
    ],
    "spotify.get_artist": [
        "GET",
        "/artists/{artistId}"
    ],
    "spotify.get_artist_albums": [
        "GET",
        "/artists/{artistId}/albums"
    ],
    "spotify.get_artist_related_artists": [
        "GET",
        "/artists/{artistId}/related-artists"
    ],
    "spotify.get_artist_top_tracks": [
        "GET",
        "/artists/{artistId}/top-tracks"
    ],
    "spotify.get_audiobook": [
        "GET",
        "/audiobooks/{audiobookId}"
    ],
    "spotify.get_audiobook_chapters": [
        "GET",
        "/audiobooks/{audiobookId}/chapters"
    ],
    "spotify.get_available_devices": [
        "GET",
        "/me/player/devices"
    ],
    "spotify.get_available_genre_seeds": [
        "GET",
        "/recommendations/available-genre-seeds"
    ],
    "spotify.get_available_markets": [
        "GET",
        "/markets"
    ],
    "spotify.get_browse_categories": [
        "GET",
        "/browse/categories"
    ],
    "spotify.get_browse_category": [
        "GET",
        "/browse/categories/{categoryId}"
    ],
    "spotify.get_category_playlists": [
        "GET",
        "/browse/categories/{categoryId}/playlists"
    ],
    "spotify.get_chapter": [
        "GET",
        "/chapters/{chapterId}"
    ],
    "spotify.get_current_user_playlists": [
        "GET",
        "/me/playlists"
    ],
    "spotify.get_current_user_profile": [
        "GET",
        "/me"
    ],
    "spotify.get_currently_playing_track": [
        "GET",
        "/me/player/currently-playing"
    ],
    "spotify.get_episode": [
        "GET",
        "/episodes/{episodeId}"
    ],
    "spotify.get_featured_playlists": [
        "GET",
        "/browse/featured-playlists"
    ],
    "spotify.get_followed_artists": [
        "GET",
        "/me/following"
    ],
    "spotify.get_new_releases": [
        "GET",
        "/browse/new-releases"
    ],
    "spotify.get_playback_state": [
        "GET",
        "/me/player"
    ],
    "spotify.get_playlist": [
        "GET",
        "/playlists/{playlistId}"
    ],
    "spotify.get_playlist_cover_image": [
        "GET",
        "/playlists/{playlistId}/images"
    ],
    "spotify.get_playlist_items": [
        "GET",
        "/playlists/{playlistId}/tracks"
    ],
    "spotify.get_recently_played_tracks": [
        "GET",
        "/me/player/recently-played"
    ],
    "spotify.get_recommendations": [
        "GET",
        "/recommendations"
    ],
    "spotify.get_several_albums": [
        "GET",
        "/albums"
    ],
    "spotify.get_several_artists": [
        "GET",
        "/artists"
    ],
    "spotify.get_several_audiobooks": [
        "GET",
        "/audiobooks"
    ],
    "spotify.get_several_chapters": [
        "GET",
        "/chapters"
    ],
    "spotify.get_several_episodes": [
        "GET",
        "/episodes"
    ],
    "spotify.get_several_shows": [
        "GET",
        "/shows"
    ],
    "spotify.get_several_track_audio_features": [
        "GET",
        "/audio-features"
    ],
    "spotify.get_several_tracks": [
        "GET",
        "/tracks"
    ],
    "spotify.get_show": [
        "GET",
        "/shows/{showId}"
    ],
    "spotify.get_show_episodes": [
        "GET",
        "/shows/{showId}/episodes"
    ],
    "spotify.get_track": [
        "GET",
        "/tracks/{trackId}"
    ],
    "spotify.get_track_audio_analysis": [
        "GET",
        "/audio-analysis/{trackId}"
    ],
    "spotify.get_track_audio_features": [
        "GET",
        "/audio-features/{trackId}"
    ],
    "spotify.get_user_playlists": [
        "GET",
        "/users/{userId}/playlists"
    ],
    "spotify.get_user_profile": [
        "GET",
        "/users/{userId}"
    ],
    "spotify.get_user_queue": [
        "GET",
        "/me/player/queue"
    ],
    "spotify.get_user_saved_albums": [
        "GET",
        "/me/albums"
    ],
    "spotify.get_user_saved_audiobooks": [
        "GET",
        "/me/audiobooks"
    ],
    "spotify.get_user_saved_episodes": [
        "GET",
        "/me/episodes"
    ],
    "spotify.get_user_saved_shows": [
        "GET",
        "/me/shows"
    ],
    "spotify.get_user_saved_tracks": [
        "GET",
        "/me/tracks"
    ],
    "spotify.get_user_top_artists": [
        "GET",
        "/me/top/artists"
    ],
    "spotify.get_user_top_tracks": [
        "GET",
        "/me/top/tracks"
    ],
    "spotify.pause_playback": [
        "PUT",
        "/me/player/pause"
    ],
    "spotify.remove_playlist_items": [
        "DELETE",
        "/playlists/{playlistId}/tracks"
    ],
    "spotify.remove_user_s_saved_audiobooks": [
        "DELETE",
        "/me/audiobooks"
    ],
    "spotify.remove_user_s_saved_episodes": [
        "DELETE",
        "/me/episodes"
    ],
    "spotify.remove_user_s_saved_shows": [
        "DELETE",
        "/me/shows"
    ],
    "spotify.remove_user_s_saved_tracks": [
        "DELETE",
        "/me/tracks"
    ],
    "spotify.remove_users_saved_albums": [
        "DELETE",
        "/me/albums"
    ],
    "spotify.save_albums_for_current_user": [
        "PUT",
        "/me/albums"
    ],
    "spotify.save_audiobooks_for_current_user": [
        "PUT",
        "/me/audiobooks"
    ],
    "spotify.save_episodes_for_current_user": [
        "PUT",
        "/me/episodes"
    ],
    "spotify.save_shows_for_current_user": [
        "PUT",
        "/me/shows"
    ],
    "spotify.save_tracks_for_current_user": [
        "PUT",
        "/me/tracks"
    ],
    "spotify.search_items": [
        "GET",
        "/search"
    ],
    "spotify.seek_to_position": [
        "PUT",
        "/me/player/seek"
    ],
    "spotify.set_playback_volume": [
        "PUT",
        "/me/player/volume"
    ],
    "spotify.set_repeat_mode": [
        "PUT",
        "/me/player/repeat"
    ],
    "spotify.skip_to_next": [
        "POST",
        "/me/player/next"
    ],
    "spotify.skip_to_previous": [
        "POST",
        "/me/player/previous"
    ],
    "spotify.start_resume_playback": [
        "PUT",
        "/me/player/play"
    ],
    "spotify.toggle_playback_shuffle": [
        "PUT",
        "/me/player/shuffle"
    ],
    "spotify.transfer_playback": [
        "PUT",
        "/me/player"
    ],
    "spotify.unfollow_artists_or_users": [
        "DELETE",
        "/me/following"
    ],
    "spotify.unfollow_playlist": [
        "DELETE",
        "/playlists/{playlistId}/followers"
    ],
    "spotify.update_playlist_items": [
        "PUT",
        "/playlists/{playlistId}/tracks"
    ]
}

def _spotify_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = cred.get("accessToken") or cred.get("apiKey") or cred.get("token") or ""
    if not str(token).strip():
        raise ValueError("Spotify access token required. Please connect your Spotify account first.")

    return {
        "Authorization": f"Bearer {str(token).strip()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

class SpotifyDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Media"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )
        mapped = SPOTIFY_ENDPOINT_MAP.get(action_meta["id"], ["GET", "/me"])
        self.method = mapped[0]
        self.endpoint_template = mapped[1]

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        inputs = dict(input_data or {})
        headers = _spotify_headers(credential)

        path = self.endpoint_template
        # Substitute path parameters
        for var in [
            "playlistId", "playlist_id", "albumId", "album_id", "trackId", "track_id",
            "artistId", "artist_id", "showId", "show_id", "episodeId", "episode_id",
            "audiobookId", "audiobook_id", "chapterId", "chapter_id", "categoryId", "category_id",
            "userId", "user_id"
        ]:
            placeholder = "{" + var + "}"
            if placeholder in path and var in inputs:
                val = inputs.pop(var)
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        url = f"{SPOTIFY_API_BASE}/{path.lstrip('/')}"
        assert_public_url(url)

        req_method = self.method
        json_body = inputs if req_method in ["POST", "PUT", "PATCH"] else None
        params = {k: v for k, v in inputs.items() if v is not None} if req_method in ["GET", "DELETE"] else None

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=url,
            headers=headers,
            json_body=json_body,
            params=params
        )

        try:
            res_data = resp.json()
        except Exception:
            res_data = resp.text

        if resp.status_code >= 400:
            err_msg = str(res_data)
            if isinstance(res_data, dict):
                error_obj = res_data.get("error")
                if isinstance(error_obj, dict):
                    err_msg = error_obj.get("message") or str(error_obj)
                elif error_obj:
                    err_msg = str(error_obj)
            raise ValueError(f"Spotify API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": res_data}

class SpotifyProvider(Provider):
    def __init__(self):
        super().__init__(
            service="spotify",
            display_name="Spotify",
            category="Media",
            auth_types=["oauth2"],
            description="Digital music, podcast, and audiobook streaming service with global catalog and user playback control.",
            homepage_url="https://spotify.com",
            base_url=SPOTIFY_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Spotify OAuth 2.0",
                    "description": "Connect your Spotify account to control playback, manage playlists, and browse music.",
                    "docs_url": "https://developer.spotify.com/documentation/web-api/tutorials/code-flow",
                    "docs_label": "Spotify Authorization Code Flow",
                    "setup_guide": {
                        "title": "Spotify App Setup Guide",
                        "docs_url": "https://developer.spotify.com/dashboard",
                        "docs_label": "Spotify Developer Dashboard",
                        "instructions": [
                            "1. Go to the Spotify Developer Dashboard (https://developer.spotify.com/dashboard).",
                            "2. Click 'Create App' and enter your App Name and Description.",
                            "3. Add your Redirect URI in the App Settings.",
                            "4. Copy your Client ID and Client Secret.",
                            "5. Configure requested scopes: user-read-playback-state, user-modify-playback-state, playlist-read-private, playlist-modify-public."
                        ],
                        "scopes": [
                            "user-read-private",
                            "user-read-email",
                            "user-read-playback-state",
                            "user-modify-playback-state",
                            "user-read-currently-playing",
                            "playlist-read-private",
                            "playlist-modify-public",
                            "playlist-modify-private",
                            "user-library-read",
                            "user-library-modify",
                            "user-top-read"
                        ]
                    }
                }
            ]
        )

        for meta in get_provider_actions("spotify"):
            self.register_action(SpotifyDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Spotify credentials by querying GET /v1/me."""
        headers = _spotify_headers(credential)
        url = f"{SPOTIFY_API_BASE}/me"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach Spotify API: {str(e)}")

        if resp.status_code in (401, 403):
            detail = ""
            try:
                err_data = resp.json().get("error", {})
                detail = f": {err_data.get('message')}" if isinstance(err_data, dict) else f": {err_data}"
            except Exception:
                detail = f": {resp.text[:200]}" if resp.text else ""
            raise ValueError(f"Spotify authentication failed ({resp.status_code}){detail}")
        elif resp.status_code != 200:
            raise ValueError(f"Spotify credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        account_id = str(body.get("id", "spotify_user"))
        display_name = body.get("display_name") or body.get("email") or f"Spotify User ({account_id})"

        return {
            "valid": True,
            "accountId": account_id,
            "displayName": display_name,
            "metadata": {
                "validationEndpoint": "/me",
                "email": body.get("email"),
                "product": body.get("product"),
                "country": body.get("country"),
                "followers": body.get("followers", {}).get("total")
            }
        }
