"""
CRM, Helpdesk & Marketing Provider Suite.
Provides integrations for HubSpot, Pipedrive, Zendesk, Intercom, Mailchimp, Brevo, and Customer.io.
"""
from app.providers.builtins.crm.hubspot import HubSpotProvider
from app.providers.builtins.crm.pipedrive import PipedriveProvider
from app.providers.builtins.crm.zendesk import ZendeskProvider
from app.providers.builtins.crm.intercom import IntercomProvider
from app.providers.builtins.crm.mailchimp import MailchimpProvider
from app.providers.builtins.crm.brevo import BrevoProvider
from app.providers.builtins.crm.customerio import CustomerIOProvider
from app.providers.builtins.crm.close import CloseProvider
from app.providers.builtins.crm.salesloft import SalesloftProvider
from app.providers.builtins.crm.gong import GongProvider
from app.providers.builtins.crm.helpscout import HelpScoutProvider
from app.providers.builtins.crm.klaviyo import KlaviyoProvider
from app.providers.builtins.crm.activecampaign import ActiveCampaignProvider
from app.providers.builtins.crm.apple_ads import AppleAdsProvider
from app.providers.builtins.crm.fastmoss_mcp import FastmossMcpProvider
from app.providers.builtins.crm.bing_webmaster import BingWebmasterProvider
from app.providers.builtins.crm.patsnap_mcp import PatsnapMcpProvider
from app.providers.builtins.crm.sellersprite_mcp import SellerspriteMcpProvider
from app.providers.builtins.crm.twitterapi_io import TwitterapiIoProvider
from app.providers.builtins.crm.apollo import ApolloProvider

__all__ = [
    "HubSpotProvider",
    "PipedriveProvider",
    "ZendeskProvider",
    "IntercomProvider",
    "MailchimpProvider",
    "BrevoProvider",
    "CustomerIOProvider",
    "CloseProvider",
    "SalesloftProvider",
    "GongProvider",
    "HelpScoutProvider",
    "KlaviyoProvider",
    "ActiveCampaignProvider",
    "AppleAdsProvider",
    "FastmossMcpProvider",
    "BingWebmasterProvider",
    "PatsnapMcpProvider",
    "SellerspriteMcpProvider",
    "TwitterapiIoProvider",
    "ApolloProvider",
]
