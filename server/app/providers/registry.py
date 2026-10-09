from typing import Dict, List, Optional
from app.providers.base import Provider, Action
from app.providers.builtins.hackernews import HackerNewsProvider
from app.providers.builtins.github import GitHubProvider
from app.providers.builtins.slack import SlackProvider
from app.providers.builtins.custom_http import CustomHttpProvider
from app.providers.builtins.gmail import GmailProvider
from app.providers.builtins.google_calendar import GoogleCalendarProvider
from app.providers.builtins.whatsapp import WhatsAppProvider
from app.providers.builtins.twitter import TwitterProvider
from app.providers.builtins.telegram import TelegramProvider
from app.providers.builtins.youtube import YouTubeProvider
from app.providers.builtins.google_drive import GoogleDriveProvider
from app.providers.builtins.google_sheets import GoogleSheetsProvider
from app.providers.builtins.google_docs import GoogleDocsProvider
from app.providers.builtins.google_tasks import GoogleTasksProvider
from app.providers.builtins.google_meet import GoogleMeetProvider
from app.providers.builtins.google_chat import GoogleChatProvider
from app.providers.builtins.google_forms import GoogleFormsProvider
from app.providers.builtins.google_photos import GooglePhotosProvider

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._actions: Dict[str, Action] = {}
        self._action_to_provider: Dict[str, str] = {}
        
        # Register core builtins
        self.register(HackerNewsProvider())
        self.register(GitHubProvider())
        self.register(SlackProvider())
        self.register(GmailProvider())
        self.register(GoogleCalendarProvider())
        self.register(GoogleDriveProvider())
        self.register(GoogleSheetsProvider())
        self.register(GoogleDocsProvider())
        self.register(GoogleTasksProvider())
        self.register(GoogleMeetProvider())
        self.register(GoogleChatProvider())
        self.register(GoogleFormsProvider())
        self.register(GooglePhotosProvider())
        self.register(WhatsAppProvider())
        self.register(TwitterProvider())
        self.register(TelegramProvider())
        self.register(YouTubeProvider())
        self.register(CustomHttpProvider())

    def register(self, provider: Provider):
        self._providers[provider.service] = provider
        for action_id, action in provider.actions.items():
            self._actions[action_id] = action
            self._action_to_provider[action_id] = provider.service

    def get_provider(self, service: str) -> Optional[Provider]:
        svc = service.lower().strip()
        if svc == "x":
            svc = "twitter"
        return self._providers.get(svc)

    def list_providers(self) -> List[Provider]:
        return list(self._providers.values())

    def get_action(self, action_id: str) -> Optional[Action]:
        return self._actions.get(action_id)

    def get_action_provider(self, action_id: str) -> Optional[Provider]:
        service = self._action_to_provider.get(action_id)
        return self._providers.get(service) if service else None

    def list_actions(self, service: Optional[str] = None) -> List[Action]:
        if service:
            provider = self._providers.get(service)
            return list(provider.actions.values()) if provider else []
        return list(self._actions.values())

    def search_actions(self, query: str = "", service: Optional[str] = None) -> List[Action]:
        actions = self.list_actions(service)
        if not query.strip():
            return actions
        q = query.lower().strip()
        matched = []
        for action in actions:
            if q in action.id.lower() or q in action.name.lower() or q in action.description.lower():
                matched.append(action)
        return matched

# Singleton registry
registry = ProviderRegistry()
