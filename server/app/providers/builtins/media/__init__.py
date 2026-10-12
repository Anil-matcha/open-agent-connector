"""
Media, Social & Storage Providers Suite for ConnectorHub.
"""
from app.providers.builtins.media.discord import DiscordProvider
from app.providers.builtins.media.linkedin import LinkedInProvider
from app.providers.builtins.media.spotify import SpotifyProvider
from app.providers.builtins.media.reddit import RedditProvider
from app.providers.builtins.media.dropbox import DropboxProvider
from app.providers.builtins.media.box import BoxProvider

__all__ = [
    "DiscordProvider",
    "LinkedInProvider",
    "SpotifyProvider",
    "RedditProvider",
    "DropboxProvider",
    "BoxProvider",
]
