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
    MailtrapProvider,
    WebexProvider,
    ResendProvider,
    PostmarkProvider,
    TwilioProvider,
    ZoomProvider,
    SendGridProvider,
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
    PostmanProvider,
    TailscaleProvider,
    PostHogProvider,
    VercelProvider,
    NewRelicProvider,
    SentryProvider,
    GrafanaProvider,
    CircleCIProvider,
    DatadogProvider,
    PagerDutyProvider,
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
    CalProvider,
    TrelloProvider,
    TodoistProvider,
    PandaDocProvider,
    WrikeProvider,
    SmartsheetProvider,
)

# AI & LLM Services Providers
from app.providers.builtins.ai import (
    OpenAIProvider,
    AnthropicProvider,
    PerplexityProvider,
    GroqCloudProvider,
    CohereProvider,
    ElevenLabsProvider,
    FirecrawlProvider,
    MistralAIProvider,
    V0Provider,
    PineconeProvider,
    ReplicateProvider,
    QdrantProvider,
    WeaviateProvider,
    DeepSeekProvider,
    TogetherAIProvider,
)

# CRM, Helpdesk & Marketing Providers
from app.providers.builtins.crm import (
    HubSpotProvider,
    PipedriveProvider,
    ZendeskProvider,
    IntercomProvider,
    MailchimpProvider,
    BrevoProvider,
    CustomerIOProvider,
    CloseProvider,
    SalesloftProvider,
    GongProvider,
)

# Payments & E-Commerce Providers
from app.providers.builtins.ecommerce import (
    StripeProvider,
    PayPalProvider,
    ShopifyProvider,
    LemonSqueezyProvider,
    SquareProvider,
    QuickBooksProvider,
    WooCommerceProvider,
    XeroProvider,
)

# Social, Media & Storage Providers
from app.providers.builtins.media import (
    DiscordProvider,
    LinkedInProvider,
    SpotifyProvider,
    RedditProvider,
    DropboxProvider,
    BoxProvider,
)

# Utility Providers
from app.providers.builtins.utility import (
    CustomHttpProvider,
    OktaProvider,
    SurveyMonkeyProvider,
    WorkdayProvider,
    TypeformProvider,
    RipplingProvider,
    BambooHRProvider,
    TallyProvider,
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
        self.register(PostmanProvider())
        self.register(TailscaleProvider())
        self.register(PostHogProvider())
        self.register(VercelProvider())
        self.register(NewRelicProvider())
        self.register(SentryProvider())
        self.register(GrafanaProvider())
        self.register(CircleCIProvider())
        self.register(DatadogProvider())
        self.register(PagerDutyProvider())

        # 2. Project Management & Issue Tracking
        self.register(NotionProvider())
        self.register(LinearProvider())
        self.register(JiraProvider())
        self.register(AsanaProvider())
        self.register(ClickUpProvider())
        self.register(MondayProvider())
        self.register(AirtableProvider())
        self.register(CodaProvider())
        self.register(CalProvider())
        self.register(TrelloProvider())
        self.register(TodoistProvider())
        self.register(PandaDocProvider())
        self.register(WrikeProvider())
        self.register(SmartsheetProvider())

        # 3. Communication & Social
        self.register(SlackProvider())
        self.register(WhatsAppProvider())
        self.register(TwitterProvider())
        self.register(TelegramProvider())
        self.register(MailtrapProvider())
        self.register(WebexProvider())
        self.register(ResendProvider())
        self.register(PostmarkProvider())
        self.register(TwilioProvider())
        self.register(ZoomProvider())
        self.register(SendGridProvider())

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

        # 6. AI & LLM Services
        self.register(OpenAIProvider())
        self.register(AnthropicProvider())
        self.register(PerplexityProvider())
        self.register(GroqCloudProvider())
        self.register(CohereProvider())
        self.register(ElevenLabsProvider())
        self.register(FirecrawlProvider())
        self.register(MistralAIProvider())
        self.register(V0Provider())
        self.register(PineconeProvider())
        self.register(ReplicateProvider())
        self.register(QdrantProvider())
        self.register(WeaviateProvider())
        self.register(DeepSeekProvider())
        self.register(TogetherAIProvider())

        # 7. CRM, Helpdesk & Marketing
        self.register(HubSpotProvider())
        self.register(PipedriveProvider())
        self.register(ZendeskProvider())
        self.register(IntercomProvider())
        self.register(MailchimpProvider())
        self.register(BrevoProvider())
        self.register(CustomerIOProvider())
        self.register(CloseProvider())
        self.register(SalesloftProvider())
        self.register(GongProvider())

        # 8. Payments & E-Commerce
        self.register(StripeProvider())
        self.register(PayPalProvider())
        self.register(ShopifyProvider())
        self.register(LemonSqueezyProvider())
        self.register(SquareProvider())
        self.register(QuickBooksProvider())
        self.register(WooCommerceProvider())
        self.register(XeroProvider())

        # 9. Social, Media & Storage
        self.register(DiscordProvider())
        self.register(LinkedInProvider())
        self.register(SpotifyProvider())
        self.register(RedditProvider())
        self.register(DropboxProvider())
        self.register(BoxProvider())

        # 10. Utilities & Forms / Identity / HR
        self.register(CustomHttpProvider())
        self.register(OktaProvider())
        self.register(SurveyMonkeyProvider())
        self.register(WorkdayProvider())
        self.register(TypeformProvider())
        self.register(RipplingProvider())
        self.register(BambooHRProvider())
        self.register(TallyProvider())

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
