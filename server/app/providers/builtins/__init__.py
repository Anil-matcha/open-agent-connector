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
from app.providers.builtins.communication import (
    SlackProvider,
    WhatsAppProvider,
    TelegramProvider,
    TwitterProvider,
)
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
from app.providers.builtins.utility import (
    CustomHttpProvider,
)

__all__ = [
    # Google Ecosystem
    "GmailProvider",
    "GoogleCalendarProvider",
    "GoogleDriveProvider",
    "GoogleSheetsProvider",
    "GoogleDocsProvider",
    "GoogleTasksProvider",
    "GoogleMeetProvider",
    "GoogleChatProvider",
    "GoogleFormsProvider",
    "GooglePhotosProvider",
    "YouTubeProvider",
    # Microsoft Ecosystem
    "OutlookProvider",
    "OutlookCalendarProvider",
    "OneDriveProvider",
    "MicrosoftTeamsProvider",
    "MicrosoftTodoProvider",
    "ExcelProvider",
    "MicrosoftClarityProvider",
    "MicrosoftTextTranslateProvider",
    # Project Management & Issue Tracking
    "NotionProvider",
    "LinearProvider",
    "JiraProvider",
    "AsanaProvider",
    "ClickUpProvider",
    "MondayProvider",
    "AirtableProvider",
    "CodaProvider",
    # Communication & Social
    "SlackProvider",
    "WhatsAppProvider",
    "TelegramProvider",
    "TwitterProvider",
    # Developer Tools & Cloud Infrastructure
    "GitHubProvider",
    "HackerNewsProvider",
    "GitLabProvider",
    "BitbucketProvider",
    "SupabaseProvider",
    "CloudflareWorkerProvider",
    "CloudflareR2Provider",
    "AWSS3Provider",
    "DockerHubProvider",
    "DigitalOceanProvider",
    # Utility
    "CustomHttpProvider",
]
