"""
Project Management & Issue Tracking Provider Suite for ConnectorHub.
Includes Notion, Linear, Jira, Asana, ClickUp, Monday, Airtable, and Coda.
"""
from app.providers.builtins.project_management.notion import NotionProvider
from app.providers.builtins.project_management.linear import LinearProvider
from app.providers.builtins.project_management.jira import JiraProvider
from app.providers.builtins.project_management.asana import AsanaProvider
from app.providers.builtins.project_management.clickup import ClickUpProvider
from app.providers.builtins.project_management.monday import MondayProvider
from app.providers.builtins.project_management.airtable import AirtableProvider
from app.providers.builtins.project_management.coda import CodaProvider
from app.providers.builtins.project_management.cal import CalProvider
from app.providers.builtins.project_management.trello import TrelloProvider
from app.providers.builtins.project_management.todoist import TodoistProvider
from app.providers.builtins.project_management.pandadoc import PandaDocProvider
from app.providers.builtins.project_management.wrike import WrikeProvider
from app.providers.builtins.project_management.smartsheet import SmartsheetProvider
from app.providers.builtins.project_management.calendly import CalendlyProvider
from app.providers.builtins.project_management.figma import FigmaProvider
from app.providers.builtins.project_management.n8n import N8nProvider
from app.providers.builtins.project_management.sunsama_mcp import SunsamaMcpProvider
from app.providers.builtins.project_management.karakeep import KarakeepProvider
from app.providers.builtins.project_management.mingdao import MingdaoProvider
from app.providers.builtins.project_management.toggl import TogglProvider
from app.providers.builtins.project_management.capsule_crm import CapsuleCrmProvider
from app.providers.builtins.project_management.clickmeeting import ClickMeetingProvider
from app.providers.builtins.project_management.nozbe_teams import NozbeTeamsProvider
from app.providers.builtins.project_management.quipteams import QuipteamsProvider
from app.providers.builtins.project_management.kobotoolbox import KoboToolboxProvider
from app.providers.builtins.project_management.dropbox_sign import DropboxSignProvider
from app.providers.builtins.project_management.systeme_io import SystemeIoProvider
from app.providers.builtins.project_management.miro import MiroProvider
from app.providers.builtins.project_management.jotform import JotformProvider
from app.providers.builtins.project_management.esa import EsaProvider
from app.providers.builtins.project_management.apaleo import ApaleoProvider
from app.providers.builtins.project_management.mymind import MymindProvider
from app.providers.builtins.project_management.ticktick import TickTickProvider
from app.providers.builtins.project_management.harvest import HarvestProvider
from app.providers.builtins.project_management.confluence import ConfluenceProvider
from app.providers.builtins.project_management.clockify import ClockifyProvider
from app.providers.builtins.project_management.shortcut import ShortcutProvider


__all__ = [
    "NotionProvider",
    "LinearProvider",
    "JiraProvider",
    "AsanaProvider",
    "ClickUpProvider",
    "MondayProvider",
    "AirtableProvider",
    "CodaProvider",
    "CalProvider",
    "TrelloProvider",
    "TodoistProvider",
    "PandaDocProvider",
    "WrikeProvider",
    "SmartsheetProvider",
    "CalendlyProvider",
    "FigmaProvider",
    "N8nProvider",
    "SunsamaMcpProvider",
    "KarakeepProvider",
    "MingdaoProvider",
    "TogglProvider",
    "CapsuleCrmProvider",
    "ClickMeetingProvider",
    "NozbeTeamsProvider",
    "QuipteamsProvider",
    "KoboToolboxProvider",
    "DropboxSignProvider",
    "SystemeIoProvider",
    "MiroProvider",
    "JotformProvider",
    "EsaProvider",
    "ApaleoProvider",
    "MymindProvider",
    "TickTickProvider",
    "HarvestProvider",
    "ConfluenceProvider",
    "ClockifyProvider",
    "ShortcutProvider",
]



