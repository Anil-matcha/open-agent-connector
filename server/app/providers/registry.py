from typing import Dict, List, Optional
from app.providers.base import Provider, Action

# Google Ecosystem Providers
from app.providers.builtins.google import (
    GmailProvider,
    GoogleCalendarProvider,
    GoogleDriveProvider,
    GoogleSheetsProvider,
    GoogleDocsProvider,
    GoogleTasksProvider,
    GoogleMeetProvider,
    GoogleChatProvider,
    GoogleFormsProvider,
    GooglePhotosProvider,
    YouTubeProvider,
)

# Microsoft Ecosystem Providers
from app.providers.builtins.microsoft import (
    OutlookProvider,
    OutlookCalendarProvider,
    OneDriveProvider,
    MicrosoftTeamsProvider,
    MicrosoftTodoProvider,
    ExcelProvider,
    MicrosoftClarityProvider,
    MicrosoftTextTranslateProvider,
)

# Communication & Social Providers
from app.providers.builtins.communication import (
    SlackProvider,
    WhatsAppProvider,
    TelegramProvider,
    TwitterProvider,
)

# Developer Tools & Cloud Infrastructure
from app.providers.builtins.developer import (
    GitHubProvider,
    HackerNewsProvider,
    GitLabProvider,
    BitbucketProvider,
    SupabaseProvider,
    CloudflareWorkerProvider,
    CloudflareR2Provider,
    AWSS3Provider,
    DockerHubProvider,
    DigitalOceanProvider,
)

# Project Management & Issue Tracking Providers
from app.providers.builtins.project_management import (
    NotionProvider,
    LinearProvider,
    JiraProvider,
    AsanaProvider,
    ClickUpProvider,
    MondayProvider,
    AirtableProvider,
    CodaProvider,
)

# Utility Providers
from app.providers.builtins.utility import (
    CustomHttpProvider,
)

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._actions: Dict[str, Action] = {}
        self._action_to_provider: Dict[str, str] = {}
        
        # 1. Developer Tools & Cloud Infrastructure
        self.register(GitHubProvider())
        self.register(HackerNewsProvider())
        self.register(GitLabProvider())
        self.register(BitbucketProvider())
        self.register(SupabaseProvider())
        self.register(CloudflareWorkerProvider())
        self.register(CloudflareR2Provider())
        self.register(AWSS3Provider())
        self.register(DockerHubProvider())
        self.register(DigitalOceanProvider())

        # 2. Project Management & Issue Tracking
        self.register(NotionProvider())
        self.register(LinearProvider())
        self.register(JiraProvider())
        self.register(AsanaProvider())
        self.register(ClickUpProvider())
        self.register(MondayProvider())
        self.register(AirtableProvider())
        self.register(CodaProvider())

        # 3. Communication & Social
        self.register(SlackProvider())
        self.register(WhatsAppProvider())
        self.register(TwitterProvider())
        self.register(TelegramProvider())

        # 4. Google Workspace Ecosystem
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
        self.register(YouTubeProvider())

        # 5. Microsoft Ecosystem
        self.register(OutlookProvider())
        self.register(OutlookCalendarProvider())
        self.register(OneDriveProvider())
        self.register(MicrosoftTeamsProvider())
        self.register(MicrosoftTodoProvider())
        self.register(ExcelProvider())
        self.register(MicrosoftClarityProvider())
        self.register(MicrosoftTextTranslateProvider())

        # 6. Utilities
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
