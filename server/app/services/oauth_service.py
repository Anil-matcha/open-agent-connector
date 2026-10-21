import asyncio
import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import OAuthState, OAuthClientConfig, Connection, utcnow_str
from app.core.security import encrypt_secret, decrypt_secret, safe_error_message
from app.core.ssrf import create_guarded_client, execute_guarded_request
from app.core.config import settings
from app.core.tenancy import DEFAULT_TENANT_ID, custom_oauth_config_key
from app.core.redirects import validate_return_uri
from app.providers.registry import registry

# Built-in OAuth provider endpoints and default scopes
OAUTH_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "github": {
        "display_name": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "default_scopes": ["repo", "read:user"],
    },
    "slack": {
        "display_name": "Slack",
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "default_scopes": ["chat:write", "channels:read"],
    },
    "gmail": {
        "display_name": "Gmail",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify"
        ],
    },
    "googlecalendar": {
        "display_name": "Google Calendar",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar"
        ],
    },
    "googledrive": {
        "display_name": "Google Drive",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file"
        ],
    },
    "googlesheets": {
        "display_name": "Google Sheets",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ],
    },
    "googledocs": {
        "display_name": "Google Docs",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive.file"
        ],
    },
    "googletasks": {
        "display_name": "Google Tasks",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/tasks",
            "https://www.googleapis.com/auth/tasks.readonly"
        ],
    },
    "googlemeet": {
        "display_name": "Google Meet",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/meetings.space.created",
            "https://www.googleapis.com/auth/meetings.space.readonly"
        ],
    },
    "googlechat": {
        "display_name": "Google Chat",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/chat.spaces.readonly",
            "https://www.googleapis.com/auth/chat.messages.readonly",
            "https://www.googleapis.com/auth/chat.messages.create"
        ],
    },
    "googleforms": {
        "display_name": "Google Forms",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/forms.body",
            "https://www.googleapis.com/auth/forms.body.readonly",
            "https://www.googleapis.com/auth/forms.responses.readonly"
        ],
    },
    "googlephotos": {
        "display_name": "Google Photos",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata",
            "https://www.googleapis.com/auth/photoslibrary.appendonly",
            "https://www.googleapis.com/auth/photospicker.mediaitems.readonly"
        ],
    },
    "youtube": {
        "display_name": "YouTube",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": [
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.readonly"
        ],
    },
    "whatsapp": {
        "display_name": "WhatsApp",
        "authorize_url": "https://www.facebook.com/v21.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v21.0/oauth/access_token",
        "default_scopes": [
            "whatsapp_business_messaging",
            "whatsapp_business_management"
        ],
    },
    "twitter": {
        "display_name": "X (Twitter)",
        "authorize_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "default_scopes": [
            "tweet.read",
            "tweet.write",
            "users.read",
            "offline.access"
        ],
    },
    "x": {
        "display_name": "X (Twitter)",
        "authorize_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "default_scopes": [
            "tweet.read",
            "tweet.write",
            "users.read",
            "offline.access"
        ],
    },
    "outlook": {
        "display_name": "Outlook",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "default_scopes": [
            "User.Read",
            "Mail.Read",
            "Mail.ReadWrite",
            "Mail.Send",
            "offline_access"
        ],
    },
    "outlook_calendar": {
        "display_name": "Outlook Calendar",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "default_scopes": [
            "User.Read",
            "Calendars.Read",
            "Calendars.ReadWrite",
            "offline_access"
        ],
    },
    "one_drive": {
        "display_name": "OneDrive",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "default_scopes": [
            "User.Read",
            "Files.Read",
            "Files.ReadWrite",
            "offline_access"
        ],
    },
    "microsoft_teams": {
        "display_name": "Microsoft Teams",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "default_scopes": [
            "User.Read",
            "Team.ReadBasic.All",
            "Channel.ReadBasic.All",
            "ChannelMessage.Send",
            "Chat.Read",
            "ChatMessage.Send",
            "offline_access"
        ],
    },
    "microsoft_todo": {
        "display_name": "Microsoft To Do",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "default_scopes": [
            "User.Read",
            "Tasks.Read",
            "Tasks.ReadWrite",
            "offline_access"
        ],
    },
    "excel": {
        "display_name": "Excel",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "default_scopes": [
            "User.Read",
            "Files.Read",
            "Files.ReadWrite",
            "offline_access"
        ],
    },
    "notion": {
        "display_name": "Notion",
        "authorize_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "token_auth_method": "basic",
        "default_scopes": [],
    },
    "linear": {
        "display_name": "Linear",
        "authorize_url": "https://linear.app/oauth/authorize",
        "token_url": "https://api.linear.app/oauth/token",
        "default_scopes": ["read", "write", "issues:create", "comments:create"],
    },
    "jira": {
        "display_name": "Jira",
        "authorize_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "default_scopes": ["read:jira-work", "write:jira-work", "read:jira-user", "offline_access"],
    },
    "asana": {
        "display_name": "Asana",
        "authorize_url": "https://app.asana.com/-/oauth_authorize",
        "token_url": "https://app.asana.com/-/oauth_token",
        "default_scopes": ["default"],
    },
    "clickup": {
        "display_name": "ClickUp",
        "authorize_url": "https://app.clickup.com/api",
        "token_url": "https://api.clickup.com/api/v2/oauth/token",
        "default_scopes": [],
    },
    "monday": {
        "display_name": "Monday.com",
        "authorize_url": "https://auth.monday.com/oauth2/authorize",
        "token_url": "https://auth.monday.com/oauth2/token",
        "default_scopes": ["boards:read", "boards:write", "workspaces:read", "users:read", "me:read"],
    },
    "airtable": {
        "display_name": "Airtable",
        "authorize_url": "https://airtable.com/oauth2/v1/authorize",
        "token_url": "https://airtable.com/oauth2/v1/token",
        "token_auth_method": "basic",
        "default_scopes": ["data.records:read", "data.records:write", "schema.bases:read", "schema.bases:write"],
    },
    "gitlab": {
        "display_name": "GitLab",
        "authorize_url": "https://gitlab.com/oauth/authorize",
        "token_url": "https://gitlab.com/oauth/token",
        "default_scopes": ["api", "read_api", "read_user"],
    },
    "bitbucket": {
        "display_name": "Bitbucket",
        "authorize_url": "https://bitbucket.org/site/oauth2/authorize",
        "token_url": "https://bitbucket.org/site/oauth2/access_token",
        "token_auth_method": "basic",
        "default_scopes": ["account", "repository", "pullrequest", "pipeline"],
    },
    "supabase": {
        "display_name": "Supabase",
        "authorize_url": "https://api.supabase.com/v1/oauth/authorize",
        "token_url": "https://api.supabase.com/v1/oauth/token",
        "token_auth_method": "basic",
        "default_scopes": ["all"],
    },
    "cloudflare_worker": {
        "display_name": "Cloudflare Worker",
        "authorize_url": "https://dash.cloudflare.com/oauth2/auth",
        "token_url": "https://api.cloudflare.com/client/v4/oauth2/token",
        "default_scopes": ["workers-scripts:write"],
    },
    "cloudflare_r2": {
        "display_name": "Cloudflare R2",
        "authorize_url": "https://dash.cloudflare.com/oauth2/auth",
        "token_url": "https://api.cloudflare.com/client/v4/oauth2/token",
        "default_scopes": ["workers-r2:write", "workers-r2:read"],
    },
    "hubspot": {
        "display_name": "HubSpot",
        "authorize_url": "https://app.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        "default_scopes": ["crm.objects.contacts.read", "crm.objects.companies.read", "crm.objects.deals.read"],
    },
    "intercom": {
        "display_name": "Intercom",
        "authorize_url": "https://app.intercom.com/oauth",
        "token_url": "https://api.intercom.io/auth/eagle/token",
        "default_scopes": [],
    },
    "mailchimp": {
        "display_name": "Mailchimp",
        "authorize_url": "https://login.mailchimp.com/oauth2/authorize",
        "token_url": "https://login.mailchimp.com/oauth2/token",
        "default_scopes": [],
    },
    "zendesk": {
        "display_name": "Zendesk",
        "authorize_url": "https://{subdomain}.zendesk.com/oauth/authorizations/new",
        "token_url": "https://{subdomain}.zendesk.com/oauth/tokens",
        "default_scopes": ["read", "write"],
    },
    "shopify": {
        "display_name": "Shopify",
        "authorize_url": "https://{shopDomain}.myshopify.com/admin/oauth/authorize",
        "token_url": "https://{shopDomain}.myshopify.com/admin/oauth/access_token",
        "default_scopes": ["read_content", "read_products", "read_themes"],
    },
    "square": {
        "display_name": "Square",
        "authorize_url": "https://connect.squareup.com/oauth2/authorize",
        "token_url": "https://connect.squareup.com/oauth2/token",
        "default_scopes": ["CUSTOMERS_READ", "CUSTOMERS_WRITE", "MERCHANT_PROFILE_READ"],
    },
    "stripe": {
        "display_name": "Stripe",
        "authorize_url": "https://connect.stripe.com/oauth/authorize",
        "token_url": "https://connect.stripe.com/oauth/token",
        "default_scopes": ["read_write"],
    },
    "paypal": {
        "display_name": "PayPal",
        "authorize_url": "https://www.paypal.com/signin/authorize",
        "token_url": "https://api-m.paypal.com/v1/oauth2/token",
        "default_scopes": ["openid", "profile", "email"],
    },
    "lemon_squeezy": {
        "display_name": "Lemon Squeezy",
        "authorize_url": "https://app.lemonsqueezy.com/oauth/authorize",
        "token_url": "https://api.lemonsqueezy.com/oauth/token",
        "default_scopes": [],
    },
    "pipedrive": {
        "display_name": "Pipedrive",
        "authorize_url": "https://oauth.pipedrive.com/oauth/authorize",
        "token_url": "https://oauth.pipedrive.com/oauth/token",
        "token_auth_method": "basic",
        "default_scopes": ["deals:full", "contacts:full", "activities:full"],
    },
    "digital_ocean": {
        "display_name": "DigitalOcean",
        "authorize_url": "https://cloud.digitalocean.com/v1/oauth/authorize",
        "token_url": "https://cloud.digitalocean.com/v1/oauth/token",
        "default_scopes": ["read", "write"],
    },
    "coda": {
        "display_name": "Coda",
        "authorize_url": "https://coda.io/oauth/authorize",
        "token_url": "https://coda.io/oauth/token",
        "default_scopes": [],
    },
    "discord": {
        "display_name": "Discord",
        "authorize_url": "https://discord.com/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "default_scopes": [
            "identify",
            "email",
            "guilds",
            "guilds.members.read",
            "connections",
        ],
    },
    "linkedin": {
        "display_name": "LinkedIn",
        "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "default_scopes": ["openid", "profile", "email", "w_member_social"],
    },
    "spotify": {
        "display_name": "Spotify",
        "authorize_url": "https://accounts.spotify.com/authorize",
        "token_url": "https://accounts.spotify.com/api/token",
        "token_auth_method": "basic",
        "default_scopes": [
            "user-read-private",
            "user-read-email",
            "user-read-playback-state",
            "user-modify-playback-state",
            "playlist-read-private",
            "playlist-modify-public"
        ],
    },
    "reddit": {
        "display_name": "Reddit",
        "authorize_url": "https://www.reddit.com/api/v1/authorize",
        "token_url": "https://www.reddit.com/api/v1/access_token",
        "token_auth_method": "basic",
        "default_scopes": ["identity", "read", "submit", "edit"],
    },
    "dropbox": {
        "display_name": "Dropbox",
        "authorize_url": "https://www.dropbox.com/oauth2/authorize",
        "token_url": "https://api.dropboxapi.com/oauth2/token",
        "default_scopes": [
            "account_info.read",
            "files.metadata.read",
            "files.metadata.write",
            "files.content.read",
            "files.content.write",
            "sharing.read",
            "sharing.write"
        ],
    },
    "box": {
        "display_name": "Box",
        "authorize_url": "https://account.box.com/api/oauth2/authorize",
        "token_url": "https://api.box.com/oauth2/token",
        "default_scopes": ["root_readwrite", "manage_webhook"],
    },
    "quickbooks": {
        "display_name": "QuickBooks Online",
        "authorize_url": "https://appcenter.intuit.com/connect/oauth2",
        "token_url": "https://oauth.platform.intuit.com/op/v1/token",
        "default_scopes": ["com.intuit.quickbooks.accounting"],
    },
    "xero": {
        "display_name": "Xero",
        "authorize_url": "https://login.xero.com/identity/connect/authorize",
        "token_url": "https://identity.xero.com/connect/token",
        "default_scopes": [
            "offline_access",
            "accounting.transactions",
            "accounting.contacts",
            "accounting.settings",
            "accounting.reports.read"
        ],
    },
    "webex": {
        "display_name": "Webex",
        "authorize_url": "https://webexapis.com/v1/authorize",
        "token_url": "https://webexapis.com/v1/access_token",
        "default_scopes": [
            "spark:kms",
            "spark:people_read",
            "spark:messages_read",
            "spark:messages_write",
            "spark:rooms_read",
            "spark:rooms_write",
            "spark:memberships_read",
            "spark:memberships_write",
            "spark:teams_read",
            "spark:teams_write"
        ],
    },
    "zoom": {
        "display_name": "Zoom",
        "authorize_url": "https://zoom.us/oauth/authorize",
        "token_url": "https://zoom.us/oauth/token",
        "token_auth_method": "basic",
        "default_scopes": [],
    },
    "cal": {
        "display_name": "Cal.com",
        "authorize_url": "https://app.cal.com/auth/oauth2/authorize",
        "token_url": "https://api.cal.com/v2/auth/oauth2/token",
        "default_scopes": ["BOOKING_READ", "BOOKING_WRITE", "EVENT_TYPE_READ", "SCHEDULE_READ"],
    },
    "todoist": {
        "display_name": "Todoist",
        "authorize_url": "https://app.todoist.com/oauth/authorize",
        "token_url": "https://api.todoist.com/oauth/access_token",
        "default_scopes": ["data:read_write"],
    },
    "survey_monkey": {
        "display_name": "SurveyMonkey",
        "authorize_url": "https://api.surveymonkey.com/oauth/authorize",
        "token_url": "https://api.surveymonkey.com/oauth/token",
        "pkce": False,
        "default_scopes": [
            "users_read",
            "surveys_read",
            "surveys_write",
            "responses_read",
            "responses_read_detail",
            "collectors_read",
            "collectors_write",
            "contacts_read",
            "contacts_write"
        ],
    },
    "surveymonkey": {
        "display_name": "SurveyMonkey",
        "authorize_url": "https://api.surveymonkey.com/oauth/authorize",
        "token_url": "https://api.surveymonkey.com/oauth/token",
        "pkce": False,
        "default_scopes": [
            "users_read",
            "surveys_read",
            "surveys_write",
            "responses_read",
            "responses_read_detail",
            "collectors_read",
            "collectors_write",
            "contacts_read",
            "contacts_write"
        ],
    },
    "typeform": {
        "display_name": "Typeform",
        "authorize_url": "https://api.typeform.com/oauth/authorize",
        "token_url": "https://api.typeform.com/oauth/token",
        "default_scopes": ["accounts:read", "forms:read", "responses:read", "workspaces:read", "offline"],
    },
    "workday": {
        "display_name": "Workday",
        "authorize_url": "https://{host}/ccx/oauth2/{tenant}/authorize",
        "token_url": "https://{host}/ccx/oauth2/{tenant}/token",
        "default_scopes": [],
    },
    "wrike": {
        "display_name": "Wrike",
        "authorize_url": "https://login.wrike.com/oauth2/v/tokens",
        "token_url": "https://login.wrike.com/oauth2/v/tokens",
        "default_scopes": ["Default,offline_access"],
    },
    "smartsheet": {
        "display_name": "Smartsheet",
        "authorize_url": "https://app.smartsheet.com/b/authorize",
        "token_url": "https://api.smartsheet.com/2.0/token",
        "default_scopes": ["READ_SHEETS", "WRITE_SHEETS"],
    },
    "salesloft": {
        "display_name": "Salesloft",
        "authorize_url": "https://accounts.salesloft.com/oauth/authorize",
        "token_url": "https://accounts.salesloft.com/oauth/token",
        "default_scopes": [],
    },
    "pandadoc": {
        "display_name": "PandaDoc",
        "authorize_url": "https://app.pandadoc.com/oauth2/authorize",
        "token_url": "https://api.pandadoc.com/oauth2/access_token",
        "default_scopes": ["read", "write"],
    },
    "calendly": {
        "display_name": "Calendly",
        "authorize_url": "https://auth.calendly.com/oauth/authorize",
        "token_url": "https://auth.calendly.com/oauth/token",
        "default_scopes": ["availability:write", "event_types:read", "scheduled_events:write", "users:read"],
    },
    "figma": {
        "display_name": "Figma",
        "authorize_url": "https://www.figma.com/oauth",
        "token_url": "https://api.figma.com/v1/oauth/token",
        "default_scopes": ["current_user:read", "file_metadata:read", "file_content:read", "file_comments:read", "file_comments:write"],
    },
    "wordpress": {
        "display_name": "WordPress",
        "authorize_url": "https://public-api.wordpress.com/oauth2/authorize",
        "token_url": "https://public-api.wordpress.com/oauth2/token",
        "default_scopes": [],
    },
    "webflow": {
        "display_name": "Webflow",
        "authorize_url": "https://webflow.com/oauth/authorize",
        "token_url": "https://api.webflow.com/oauth/access_token",
        "default_scopes": ["sites:read", "sites:write", "cms:read", "cms:write"],
    },
    "helpscout": {
        "display_name": "Help Scout",
        "authorize_url": "https://secure.helpscout.net/authentication/authorizeClientApplication",
        "token_url": "https://api.helpscout.net/v2/oauth2/token",
        "default_scopes": [],
    },
    "canva": {
        "display_name": "Canva",
        "authorize_url": "https://www.canva.com/api/oauth/authorize",
        "token_url": "https://api.canva.com/rest/v1/oauth/token",
        "token_auth_method": "basic",
        "default_scopes": [
            "design:meta:read",
            "design:content:read",
            "design:content:write",
            "asset:read",
            "asset:write",
            "folder:read",
            "folder:write",
            "profile:read"
        ],
    },
    "miro": {
        "display_name": "Miro",
        "authorize_url": "https://miro.com/oauth/authorize",
        "token_url": "https://api.miro.com/v1/oauth/token",
        "token_auth_method": "body",
        "default_scopes": ["boards:read", "boards:write"],
    },
    "tiktok_business": {
        "display_name": "TikTok for Business",
        "authorize_url": "https://business-api.tiktok.com/portal/auth",
        "token_url": "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/",
        "token_auth_method": "body",
        "default_scopes": [],
    },
    "slackbot": {
        "display_name": "Slack Bot",
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "token_auth_method": "body",
        "default_scopes": ["chat:write", "channels:read", "users:read"],
    },
    "esa": {
        "display_name": "esa",
        "authorize_url": "https://api.esa.io/oauth/authorize",
        "token_url": "https://api.esa.io/oauth/token",
        "token_auth_method": "body",
        "default_scopes": ["read", "write"],
    },
    "apaleo": {
        "display_name": "apaleo",
        "authorize_url": "https://identity.apaleo.com/connect/authorize",
        "token_url": "https://identity.apaleo.com/connect/token",
        "token_auth_method": "body",
        "default_scopes": ["offline_access"],
    },
    "bilibili": {
        "display_name": "Bilibili",
        "authorize_url": "https://passport.bilibili.com/register/verification.html",
        "token_url": "https://api.bilibili.com/x/account-oauth2/v1/token",
        "token_auth_method": "body",
        "default_scopes": [],
    },
    "bloomerang": {
        "display_name": "Bloomerang",
        "authorize_url": "https://crm.bloomerang.co/oauth/authorize",
        "token_url": "https://crm.bloomerang.co/oauth/token",
        "token_auth_method": "body",
        "default_scopes": [],
    },
    "strava": {
        "display_name": "Strava",
        "authorize_url": "https://www.strava.com/oauth/authorize",
        "token_url": "https://www.strava.com/oauth/token",
        "token_auth_method": "body",
        "default_scopes": ["read", "read_all", "profile:read_all", "activity:read_all", "activity:write"],
    },
    "vimeo": {
        "display_name": "Vimeo",
        "authorize_url": "https://api.vimeo.com/oauth/authorize",
        "token_url": "https://api.vimeo.com/oauth/access_token",
        "token_auth_method": "basic",
        "default_scopes": ["public", "private", "video_files", "edit", "upload"],
    },
    "sentry": {
        "display_name": "Sentry",
        "authorize_url": "https://sentry.io/oauth/authorize/",
        "token_url": "https://sentry.io/oauth/token/",
        "token_auth_method": "body",
        "default_scopes": ["project:read", "project:write", "event:read", "event:write", "org:read"],
    },
    "oura": {
        "display_name": "Oura",
        "authorize_url": "https://cloud.ouraring.com/oauth/authorize",
        "token_url": "https://api.ouraring.com/oauth/token",
        "token_auth_method": "body",
        "default_scopes": ["daily", "heartrate", "personal", "session", "workout"],
    },
    "huggingface": {
        "display_name": "Hugging Face",
        "authorize_url": "https://huggingface.co/oauth/authorize",
        "token_url": "https://huggingface.co/oauth/token",
        "token_auth_method": "body",
        "default_scopes": ["openid", "profile", "read-repos", "write-repos"],
    },
    "dropbox_sign": {
        "display_name": "Dropbox Sign",
        "authorize_url": "https://app.hellosign.com/oauth/authorize",
        "token_url": "https://app.hellosign.com/oauth/token",
        "token_auth_method": "basic",
        "default_scopes": ["basic_account_info", "signature_request.read", "signature_request.write"],
    },
    "google_analytics": {
        "display_name": "Google Analytics",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "token_auth_method": "body",
        "default_scopes": ["https://www.googleapis.com/auth/analytics.readonly"],
    },
    "google_bigquery": {
        "display_name": "Google BigQuery",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "token_auth_method": "body",
        "default_scopes": ["https://www.googleapis.com/auth/bigquery"],
    },
    "instagram": {
        "display_name": "Instagram",
        "authorize_url": "https://api.instagram.com/oauth/authorize",
        "token_url": "https://api.instagram.com/oauth/access_token",
        "token_auth_method": "body",
        "default_scopes": [
            "instagram_business_basic",
            "instagram_business_manage_comments",
            "instagram_business_content_publish",
            "instagram_business_manage_messages"
        ],
    },
    "netlify": {
        "display_name": "Netlify",
        "authorize_url": "https://app.netlify.com/authorize",
        "token_url": "https://api.netlify.com/oauth/token",
        "token_auth_method": "body",
        "default_scopes": [],
    },
    "ticktick": {
        "display_name": "TickTick",
        "authorize_url": "https://ticktick.com/oauth/authorize",
        "token_url": "https://ticktick.com/oauth/token",
        "token_auth_method": "basic",
        "default_scopes": ["tasks:read", "tasks:write"],
    },
    "googleslides": {
        "display_name": "Google Slides",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "token_auth_method": "body",
        "default_scopes": [
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/drive.readonly"
        ],
    },
    "google_search_console": {
        "display_name": "Google Search Console",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "token_auth_method": "body",
        "default_scopes": ["https://www.googleapis.com/auth/webmasters.readonly"],
    },
    "harvest": {
        "display_name": "Harvest",
        "authorize_url": "https://id.getharvest.com/oauth2/authorize",
        "token_url": "https://id.getharvest.com/api/v2/oauth2/token",
        "token_auth_method": "body",
        "default_scopes": [],
    },
    "confluence": {
        "display_name": "Confluence",
        "authorize_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "token_auth_method": "body",
        "default_scopes": [
            "read:page:confluence",
            "write:page:confluence",
            "read:space:confluence",
            "search:confluence",
            "offline_access"
        ],
    }
}


class OAuthService:
    @staticmethod
    def callback_url(service: str) -> str:
        """Redirect URI registered with the provider; must match authorize and token exchange."""
        return f"{settings.PUBLIC_ORIGIN.rstrip('/')}/api/oauth/{service}/callback"

    # In-memory per-connection locks to guarantee single-flight refresh operations
    _refresh_locks: Dict[str, asyncio.Lock] = {}

    @classmethod
    def _get_lock(cls, connection_id: str) -> asyncio.Lock:
        if connection_id not in cls._refresh_locks:
            cls._refresh_locks[connection_id] = asyncio.Lock()
        return cls._refresh_locks[connection_id]

    @staticmethod
    def create_pkce_pair() -> Tuple[str, str]:
        """Generate RFC 7636 PKCE code_verifier and code_challenge (S256)."""
        code_verifier = secrets.token_urlsafe(64)
        hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(hashed).decode("ascii").rstrip("=")
        return code_verifier, code_challenge

    @staticmethod
    def _get_candidates(service: str) -> list:
        candidates = [service.upper()]
        s_lower = service.lower()
        if s_lower in ("twitter", "x"):
            candidates.extend(["TWITTER", "X"])
        elif s_lower in ("whatsapp",):
            candidates.extend(["WHATSAPP", "META", "FACEBOOK"])
        elif s_lower.startswith("google") or s_lower in ("gmail", "youtube"):
            candidates.extend(["GOOGLE", "GOOGLE_WORKSPACE"])
        elif s_lower in ("outlook", "outlook_calendar", "one_drive", "onedrive", "microsoft_teams", "microsoft_todo", "excel") or "microsoft" in s_lower:
            candidates.extend(["MICROSOFT", "AZURE", "MS", "MICROSOFT_GRAPH"])
        elif s_lower == "jira":
            candidates.extend(["JIRA", "ATLASSIAN"])
        elif s_lower in ("cloudflare_worker", "cloudflare_r2"):
            candidates.extend(["CLOUDFLARE", "CF"])
        elif s_lower == "digital_ocean":
            candidates.extend(["DIGITALOCEAN", "DO"])
        elif s_lower == "docker_hub":
            candidates.extend(["DOCKER", "DOCKERHUB"])
        elif s_lower == "aws_s3":
            candidates.extend(["AWS", "S3"])
        elif s_lower == "openai":
            candidates.extend(["OPENAI"])
        elif s_lower == "anthropic":
            candidates.extend(["ANTHROPIC", "CLAUDE"])
        elif s_lower == "perplexity":
            candidates.extend(["PERPLEXITY", "PPLX"])
        elif s_lower == "groqcloud":
            candidates.extend(["GROQCLOUD", "GROQ"])
        elif s_lower == "cohere":
            candidates.extend(["COHERE"])
        elif s_lower == "elevenlabs":
            candidates.extend(["ELEVENLABS", "XI"])
        elif s_lower == "firecrawl":
            candidates.extend(["FIRECRAWL"])
        elif s_lower == "hubspot":
            candidates.extend(["HUBSPOT"])
        elif s_lower == "pipedrive":
            candidates.extend(["PIPEDRIVE"])
        elif s_lower == "zendesk":
            candidates.extend(["ZENDESK"])
        elif s_lower == "intercom":
            candidates.extend(["INTERCOM"])
        elif s_lower == "mailchimp":
            candidates.extend(["MAILCHIMP"])
        elif s_lower == "brevo":
            candidates.extend(["BREVO", "SENDINBLUE"])
        elif s_lower == "customerio":
            candidates.extend(["CUSTOMERIO", "CUSTOMER_IO"])
        elif s_lower == "stripe":
            candidates.extend(["STRIPE"])
        elif s_lower == "paypal":
            candidates.extend(["PAYPAL"])
        elif s_lower == "shopify":
            candidates.extend(["SHOPIFY"])
        elif s_lower == "lemon_squeezy":
            candidates.extend(["LEMON_SQUEEZY", "LEMONSQUEEZY"])
        elif s_lower == "square":
            candidates.extend(["SQUARE"])
        elif s_lower == "coda":
            candidates.extend(["CODA"])
        elif s_lower == "discord":
            candidates.extend(["DISCORD"])
        elif s_lower == "linkedin":
            candidates.extend(["LINKEDIN"])
        elif s_lower == "spotify":
            candidates.extend(["SPOTIFY"])
        elif s_lower == "reddit":
            candidates.extend(["REDDIT"])
        elif s_lower == "dropbox":
            candidates.extend(["DROPBOX"])
        elif s_lower == "box":
            candidates.extend(["BOX"])
        elif s_lower in ("survey_monkey", "surveymonkey"):
            candidates.extend(["SURVEY_MONKEY", "SURVEYMONKEY"])
        elif s_lower == "pandadoc":
            candidates.extend(["PANDADOC", "PANDA_DOC"])
        elif s_lower == "smartsheet":
            candidates.extend(["SMARTSHEET", "SMART_SHEET"])
        elif s_lower == "salesloft":
            candidates.extend(["SALESLOFT", "SALES_LOFT"])
        elif s_lower == "cal":
            candidates.extend(["CAL", "CAL_COM", "CALCOM"])
        elif s_lower == "todoist":
            candidates.extend(["TODOIST"])
        elif s_lower == "typeform":
            candidates.extend(["TYPEFORM"])
        elif s_lower == "workday":
            candidates.extend(["WORKDAY"])
        elif s_lower == "wrike":
            candidates.extend(["WRIKE"])
        elif s_lower == "calendly":
            candidates.extend(["CALENDLY"])
        elif s_lower == "figma":
            candidates.extend(["FIGMA"])
        elif s_lower in ("wordpress", "wp"):
            candidates.extend(["WORDPRESS", "WP"])
        elif s_lower == "webflow":
            candidates.extend(["WEBFLOW"])
        elif s_lower in ("helpscout", "help_scout"):
            candidates.extend(["HELPSCOUT", "HELP_SCOUT"])
        elif s_lower in ("launch_darkly", "launchdarkly"):
            candidates.extend(["LAUNCH_DARKLY", "LAUNCHDARKLY"])
        elif s_lower in ("upstash_redis", "upstash"):
            candidates.extend(["UPSTASH_REDIS", "UPSTASH"])
        elif s_lower in ("activecampaign", "active_campaign"):
            candidates.extend(["ACTIVECAMPAIGN", "ACTIVE_CAMPAIGN"])
        elif s_lower == "canva":
            candidates.extend(["CANVA"])
        elif s_lower == "miro":
            candidates.extend(["MIRO"])
        elif s_lower in ("tiktok_business", "tiktok"):
            candidates.extend(["TIKTOK_BUSINESS", "TIKTOK"])

        return candidates

    @staticmethod
    async def get_hosted_client_config(session: AsyncSession, service: str) -> Optional[Dict[str, str]]:
        """Retrieve stored hosted OAuth client credentials, falling back to hosted environment settings."""
        hosted_key = f"hosted:{service}"
        stmt = select(OAuthClientConfig).where(OAuthClientConfig.service == hosted_key)
        res = (await session.execute(stmt)).scalar_one_or_none()
        if res and res.encrypted_value:
            try:
                decrypted = decrypt_secret(res.encrypted_value)
                cfg = json.loads(decrypted)
                cfg["mode"] = "hosted"
                return cfg
            except Exception:
                pass

        candidates = OAuthService._get_candidates(service)
        for cand in candidates:
            cid = (
                getattr(settings, f"HOSTED_{cand}_CLIENT_ID", None)
                or os.environ.get(f"CONNECTOR_HOSTED_{cand}_CLIENT_ID")
                or os.environ.get(f"HOSTED_{cand}_CLIENT_ID")
            )
            csec = (
                getattr(settings, f"HOSTED_{cand}_CLIENT_SECRET", None)
                or os.environ.get(f"CONNECTOR_HOSTED_{cand}_CLIENT_SECRET")
                or os.environ.get(f"HOSTED_{cand}_CLIENT_SECRET")
            )
            if cid and csec:
                return {
                    "client_id": cid,
                    "client_secret": csec,
                    "mode": "hosted"
                }
        return None

    @staticmethod
    async def get_custom_client_config(session: AsyncSession, tenant_id: str, service: str) -> Optional[Dict[str, str]]:
        """Retrieve OAuth client credentials the tenant supplied for itself."""
        stmt = select(OAuthClientConfig).where(
            OAuthClientConfig.service == custom_oauth_config_key(tenant_id, service)
        )
        res = (await session.execute(stmt)).scalar_one_or_none()
        if res and res.encrypted_value:
            try:
                decrypted = decrypt_secret(res.encrypted_value)
                cfg = json.loads(decrypted)
                cfg["mode"] = "custom"
                return cfg
            except Exception:
                pass

        # Environment credentials belong to the operator, so only the default tenant may use them.
        if tenant_id != DEFAULT_TENANT_ID:
            return None

        candidates = OAuthService._get_candidates(service)
        for cand in candidates:
            cid = (
                getattr(settings, f"{cand}_CLIENT_ID", None)
                or os.environ.get(f"CONNECTOR_{cand}_CLIENT_ID")
                or os.environ.get(f"{cand}_CLIENT_ID")
            )
            csec = (
                getattr(settings, f"{cand}_CLIENT_SECRET", None)
                or os.environ.get(f"CONNECTOR_{cand}_CLIENT_SECRET")
                or os.environ.get(f"{cand}_CLIENT_SECRET")
            )
            if cid and csec:
                return {
                    "client_id": cid,
                    "client_secret": csec,
                    "mode": "custom"
                }
        return None

    @staticmethod
    async def get_client_config(
        session: AsyncSession,
        tenant_id: str,
        service: str,
        mode: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """Retrieve OAuth client credentials for requested mode ('hosted' or 'custom').
        If mode is omitted, checks custom first (user override), then hosted.
        """
        if mode == "hosted":
            return await OAuthService.get_hosted_client_config(session, service)
        elif mode == "custom":
            return await OAuthService.get_custom_client_config(session, tenant_id, service)

        # Fallback resolution: custom override if present, else hosted
        custom = await OAuthService.get_custom_client_config(session, tenant_id, service)
        if custom:
            return custom
        return await OAuthService.get_hosted_client_config(session, service)

    @staticmethod
    async def get_oauth_status(session: AsyncSession, tenant_id: str, service: str) -> Dict[str, Any]:
        """Inspect dual-mode OAuth availability for service."""
        hosted = await OAuthService.get_hosted_client_config(session, service)
        custom = await OAuthService.get_custom_client_config(session, tenant_id, service)
        meta = OAUTH_PROVIDERS.get(service, {})
        callback_url = OAuthService.callback_url(service)

        configured = bool(hosted or custom)
        active_mode = "custom" if custom else ("hosted" if hosted else None)

        return {
            "service": service,
            "displayName": meta.get("display_name", service.title()),
            "configured": configured,
            "hostedAvailable": bool(hosted),
            "customConfigured": bool(custom),
            "activeMode": active_mode,
            "callbackUrl": callback_url,
            "hostedDomain": getattr(settings, "HOSTED_DOMAIN", "connector.suparagent.ai"),
            "publicOrigin": settings.PUBLIC_ORIGIN.rstrip("/"),
            "defaultScopes": meta.get("default_scopes", [])
        }

    @staticmethod
    async def set_client_config(
        session: AsyncSession,
        tenant_id: str,
        service: str,
        client_id: str,
        client_secret: str,
        mode: str = "custom"
    ) -> None:
        """Store OAuth client credentials encrypted with AES-256-GCM.
        Mode can be 'hosted' or 'custom'.
        """
        payload = json.dumps({"client_id": client_id, "client_secret": client_secret})
        encrypted_val = encrypt_secret(payload)
        
        target_service = f"hosted:{service}" if mode == "hosted" else custom_oauth_config_key(tenant_id, service)
        stmt = select(OAuthClientConfig).where(OAuthClientConfig.service == target_service)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.encrypted_value = encrypted_val
            existing.updated_at = utcnow_str()
        else:
            new_conf = OAuthClientConfig(
                service=target_service,
                encrypted_value=encrypted_val
            )
            session.add(new_conf)
        await session.commit()

    @staticmethod
    async def create_authorization_url(
        session: AsyncSession,
        tenant_id: str,
        service: str,
        connection_name: str = "default",
        redirect_uri: Optional[str] = None,
        custom_scopes: Optional[list] = None,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate PKCE state, record expiring transaction state, and build authorization URL."""
        provider_meta = OAUTH_PROVIDERS.get(service)
        if not provider_meta:
            raise ValueError(f"OAuth is not supported for service '{service}'.")

        redirect_uri = validate_return_uri(redirect_uri)  # raises ValueError for disallowed origins

        config = await OAuthService.get_client_config(session, tenant_id, service, mode=mode)
        if not config or not config.get("client_id"):
            if mode == "hosted":
                raise ValueError(
                    f"Hosted OAuth app for '{service}' is not yet configured on {settings.PUBLIC_ORIGIN}. "
                    f"Please configure custom credentials or set up hosted app."
                )
            raise ValueError(f"OAuth client credentials have not been configured for '{service}'.")

        auth_mode = config.get("mode") or mode or "custom"
        client_id = config["client_id"]
        code_verifier, code_challenge = OAuthService.create_pkce_pair()
        state = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"

        # Record expiring transaction state
        oauth_state = OAuthState(
            state=state,
            tenant_id=tenant_id,
            service=service,
            connection_name=connection_name,
            code_verifier=code_verifier,
            return_uri=redirect_uri,
            auth_mode=auth_mode,
            created_at=utcnow_str(),
            expires_at=expires_at
        )
        session.add(oauth_state)
        await session.commit()

        scopes = custom_scopes or provider_meta.get("default_scopes", [])
        scope_str = ",".join(scopes) if service in ("github", "slack") else " ".join(scopes)
        if service == "zoom":
            scope_str = ""

        use_pkce = provider_meta.get("pkce", True)
        callback_uri = OAuthService.callback_url(service)
        params = {
            "client_id": client_id,
            "response_type": "code",
            "state": state,
            "redirect_uri": callback_uri
        }
        if use_pkce:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        if scope_str:
            params["scope"] = scope_str

        if service == "dropbox":
            params["token_access_type"] = "offline"
        elif service == "reddit":
            params["duration"] = "permanent"
        elif service == "notion":
            params["owner"] = "user"

        auth_url_base = provider_meta['authorize_url']
        subdomain = (config or {}).get("subdomain") or (config or {}).get("shopDomain") or (config or {}).get("shop") or ""
        if "{" in auth_url_base and subdomain:
            auth_url_base = auth_url_base.replace("{subdomain}", subdomain).replace("{shopDomain}", subdomain)

        auth_url = f"{auth_url_base}?{urlencode(params)}"
        return {
            "authorization_url": auth_url,
            "state": state,
            "service": service,
            "connectionName": connection_name,
            "expiresAt": expires_at
        }

    @staticmethod
    async def peek_return_uri(session: AsyncSession, service: str, state: str) -> Optional[str]:
        """Return URL stored with an OAuth state (revalidated), without consuming the state."""
        res = (await session.execute(
            select(OAuthState).where(and_(OAuthState.state == state, OAuthState.service == service))
        )).scalar_one_or_none()
        if not res or not res.return_uri:
            return None
        try:
            return validate_return_uri(res.return_uri)
        except ValueError:
            return None

    @staticmethod
    async def exchange_code(
        session: AsyncSession,
        service: str,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """Atomically validate one-time state, exchange code with PKCE, and persist encrypted credentials."""
        stmt = select(OAuthState).where(
            and_(OAuthState.state == state, OAuthState.service == service)
        )
        res = (await session.execute(stmt)).scalar_one_or_none()
        if not res:
            raise ValueError("Invalid or expired OAuth state parameter.")

        # Check state expiration (10 min lifetime)
        now_str = utcnow_str()
        if res.expires_at and res.expires_at < now_str:
            await session.delete(res)
            await session.commit()
            raise ValueError("OAuth transaction state has expired. Please restart the authorization flow.")

        auth_mode = getattr(res, "auth_mode", None) or "hosted"
        tenant_id = res.tenant_id or DEFAULT_TENANT_ID  # bound when the flow started, never from the callback request
        connection_name = res.connection_name
        code_verifier = res.code_verifier
        redirect_uri = res.return_uri

        # Atomically delete one-time state to prevent replay attacks
        await session.delete(res)
        await session.commit()

        # Retrieve client config for the active mode, falling back to any valid config
        config = await OAuthService.get_client_config(session, tenant_id, service, mode=auth_mode)
        if not config:
            config = await OAuthService.get_client_config(session, tenant_id, service)
        if not config:
            raise ValueError(f"OAuth configuration missing for service '{service}'.")

        provider_meta = OAUTH_PROVIDERS.get(service)
        if not provider_meta:
            raise ValueError(f"Unknown OAuth provider: '{service}'.")

        token_url = provider_meta["token_url"]
        subdomain = (config or {}).get("subdomain") or (config or {}).get("shopDomain") or (config or {}).get("shop") or ""
        if "{" in token_url and subdomain:
            token_url = token_url.replace("{subdomain}", subdomain).replace("{shopDomain}", subdomain)
        
        # Prepare token exchange payload
        auth_method = provider_meta.get("token_auth_method", "body")
        token_headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ConnectorHub/1.0 by ConnectorHubAgent"
        }
        token_payload = {
            "code": code,
            "grant_type": "authorization_code"
        }
        if code_verifier and provider_meta.get("pkce", True):
            token_payload["code_verifier"] = code_verifier
        token_payload["redirect_uri"] = OAuthService.callback_url(service)

        if auth_method == "basic":
            basic_bytes = f"{config['client_id']}:{config['client_secret']}".encode("utf-8")
            basic_b64 = base64.b64encode(basic_bytes).decode("utf-8")
            token_headers["Authorization"] = f"Basic {basic_b64}"
        else:
            token_payload["client_id"] = config["client_id"]
            token_payload["client_secret"] = config["client_secret"]

        if service == "notion":
            token_headers["Content-Type"] = "application/json"
            token_headers["Notion-Version"] = "2022-06-28"

        use_json = token_headers.get("Content-Type") == "application/json"
        client = await create_guarded_client()
        try:
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=token_url,
                data=token_payload if not use_json else None,
                json_body=token_payload if use_json else None,
                headers=token_headers
            )
            if resp.status_code != 200:
                raise ValueError(f"OAuth token exchange rejected by provider (status {resp.status_code}): {resp.text}")

            try:
                token_data = resp.json()
            except Exception:
                # Some providers return URL-encoded form data
                from urllib.parse import parse_qs
                parsed = parse_qs(resp.text)
                token_data = {k: v[0] for k, v in parsed.items()}

            if "error" in token_data:
                raise ValueError(f"Provider returned OAuth error: {token_data.get('error_description') or token_data['error']}")

            access_token = token_data.get("access_token") or (token_data.get("authed_user") or {}).get("access_token")
            if not access_token:
                raise ValueError("No access_token returned by provider.")

            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")
            expires_at = None
            if expires_in:
                expires_at = (datetime.utcnow() + timedelta(seconds=int(expires_in))).isoformat() + "Z"

            # Validate live with provider registry
            provider = registry.get_provider(service)
            if not provider:
                raise ValueError(f"Provider registry entry missing for '{service}'.")

            val_payload = {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "tokenType": token_data.get("token_type", "Bearer"),
                "authType": "oauth2",
                "authMode": auth_mode
            }
            if "api_domain" in token_data:
                val_payload["apiDomain"] = token_data["api_domain"]
            if "domain" in token_data:
                val_payload["domain"] = token_data["domain"]

            profile = await provider.validate_credentials(val_payload, client)

            # Build credential record
            credential_dict = {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "tokenType": token_data.get("token_type", "Bearer"),
                "scope": token_data.get("scope", ""),
                "authMode": auth_mode
            }
            if "api_domain" in token_data:
                credential_dict["apiDomain"] = token_data["api_domain"]

            # Merge provider-specific metadata (e.g. Mailchimp dc, serverPrefix, apiEndpoint)
            if isinstance(profile.get("metadata"), dict):
                for k, v in profile["metadata"].items():
                    if k not in credential_dict and v is not None:
                        credential_dict[k] = v

            encrypted_val = encrypt_secret(json.dumps(credential_dict))
            account_id = profile.get("account_id") or profile.get("accountId")
            display_name = profile.get("display_name") or profile.get("displayName")
            granted_scopes_json = json.dumps(profile.get("granted_scopes", []))

            # Upsert into connection model
            conn_stmt = select(Connection).where(
                and_(
                    Connection.tenant_id == tenant_id,
                    Connection.service == service,
                    Connection.connection_name == connection_name,
                )
            )
            existing_conn = (await session.execute(conn_stmt)).scalar_one_or_none()
            if existing_conn:
                existing_conn.auth_type = "oauth2"
                existing_conn.encrypted_value = encrypted_val
                existing_conn.account_id = account_id
                existing_conn.display_name = display_name
                existing_conn.granted_scopes = granted_scopes_json
                existing_conn.status = "active"
                existing_conn.status_message = None
                existing_conn.last_validated_at = utcnow_str()
                existing_conn.expires_at = expires_at
                existing_conn.updated_at = utcnow_str()
                conn_id = existing_conn.id
            else:
                new_conn = Connection(
                    tenant_id=tenant_id,
                    service=service,
                    connection_name=connection_name,
                    auth_type="oauth2",
                    encrypted_value=encrypted_val,
                    account_id=account_id,
                    display_name=display_name,
                    granted_scopes=granted_scopes_json,
                    status="active",
                    status_message=None,
                    last_validated_at=utcnow_str(),
                    expires_at=expires_at
                )
                session.add(new_conn)
                await session.flush()
                conn_id = new_conn.id

            await session.commit()

            return {
                "id": conn_id,
                "service": service,
                "connectionName": connection_name,
                "authType": "oauth2",
                "accountId": account_id,
                "displayName": display_name,
                "status": "active",
                "lastValidatedAt": utcnow_str(),
                "expiresAt": expires_at,
                "returnUri": redirect_uri
            }
        finally:
            await client.aclose()

    @staticmethod
    async def refresh_connection_if_needed(session: AsyncSession, connection: Connection) -> bool:
        """Concurrency-safe OAuth token refresh using connection lock. Returns True if active/refreshed, False if expired."""
        if connection.auth_type != "oauth2":
            return True

        # Decrypt credential
        try:
            creds = json.loads(decrypt_secret(connection.encrypted_value))
        except Exception:
            return False

        refresh_token = creds.get("refreshToken")
        expires_at = connection.expires_at

        # If token does not expire or has > 60s remaining, no refresh needed
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(exp_dt.tzinfo) + timedelta(seconds=60) < exp_dt:
                    return True
            except Exception:
                pass

        # If no refresh token is stored, token is permanently expired
        if not refresh_token:
            if expires_at and expires_at < utcnow_str():
                connection.status = "expired"
                connection.status_message = "Access token expired and no refresh token is available. Re-authentication required."
                await session.commit()
                return False
            return True

        # Acquire lock to ensure only one refresh request runs for this connection
        lock = OAuthService._get_lock(connection.id)
        async with lock:
            # Re-read connection inside lock to check if another worker already refreshed it
            await session.refresh(connection)
            try:
                re_creds = json.loads(decrypt_secret(connection.encrypted_value))
                if connection.expires_at:
                    exp_dt = datetime.fromisoformat(connection.expires_at.replace("Z", "+00:00"))
                    if datetime.now(exp_dt.tzinfo) + timedelta(seconds=60) < exp_dt:
                        return True
            except Exception:
                pass

            auth_mode = re_creds.get("authMode") if 're_creds' in locals() and isinstance(re_creds, dict) else None
            config = await OAuthService.get_client_config(session, connection.tenant_id, connection.service, mode=auth_mode)
            if not config:
                config = await OAuthService.get_client_config(session, connection.tenant_id, connection.service)
            provider_meta = OAUTH_PROVIDERS.get(connection.service)
            if not config or not provider_meta:
                connection.status = "expired"
                connection.status_message = "OAuth configuration unavailable for automatic refresh."
                await session.commit()
                return False

            client = await create_guarded_client()
            try:
                auth_method = provider_meta.get("token_auth_method", "body")
                refresh_headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                refresh_payload = {
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
                if auth_method == "basic":
                    basic_bytes = f"{config['client_id']}:{config['client_secret']}".encode("utf-8")
                    basic_b64 = base64.b64encode(basic_bytes).decode("utf-8")
                    refresh_headers["Authorization"] = f"Basic {basic_b64}"
                else:
                    refresh_payload["client_id"] = config["client_id"]
                    refresh_payload["client_secret"] = config["client_secret"]

                refresh_token_url = provider_meta["token_url"]
                subdomain = (config or {}).get("subdomain") or (config or {}).get("shopDomain") or (config or {}).get("shop") or ""
                if "{" in refresh_token_url and subdomain:
                    refresh_token_url = refresh_token_url.replace("{subdomain}", subdomain).replace("{shopDomain}", subdomain)

                resp = await execute_guarded_request(
                    client=client,
                    method="POST",
                    url=refresh_token_url,
                    data=refresh_payload,
                    headers=refresh_headers
                )

                if resp.status_code in (400, 401):
                    connection.status = "expired"
                    connection.status_message = "Refresh token expired or revoked. Please reconnect account."
                    await session.commit()
                    return False
                
                if resp.status_code != 200:
                    connection.status = "error"
                    connection.status_message = f"Token refresh failed upstream with status {resp.status_code}"
                    await session.commit()
                    return False

                token_data = resp.json()
                new_access_token = token_data.get("access_token")
                if not new_access_token:
                    return False

                # Update credentials
                creds["accessToken"] = new_access_token
                if "refresh_token" in token_data:
                    creds["refreshToken"] = token_data["refresh_token"]

                expires_in = token_data.get("expires_in")
                new_expires_at = None
                if expires_in:
                    new_expires_at = (datetime.utcnow() + timedelta(seconds=int(expires_in))).isoformat() + "Z"

                connection.encrypted_value = encrypt_secret(json.dumps(creds))
                connection.status = "active"
                connection.status_message = None
                connection.last_validated_at = utcnow_str()
                connection.expires_at = new_expires_at
                connection.updated_at = utcnow_str()
                await session.commit()
                return True
            except Exception as e:
                connection.status = "error"
                connection.status_message = safe_error_message(e)
                await session.commit()
                return False
            finally:
                await client.aclose()
