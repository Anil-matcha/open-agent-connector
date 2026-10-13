"""Mailchimp credentials must only ever be sent to *.api.mailchimp.com."""
import pytest

from app.providers.builtins.crm.mailchimp import _resolve_mailchimp_base


@pytest.mark.parametrize("cred,expected", [
    ({"apiKey": "abc-us21"}, "https://us21.api.mailchimp.com/3.0"),
    ({"serverPrefix": "us6", "accessToken": "tok"}, "https://us6.api.mailchimp.com/3.0"),
    ({"apiEndpoint": "https://us14.api.mailchimp.com"}, "https://us14.api.mailchimp.com/3.0"),
    ({"apiEndpoint": "https://us14.api.mailchimp.com/3.0/"}, "https://us14.api.mailchimp.com/3.0"),
    ({}, "https://us1.api.mailchimp.com/3.0"),
])
def test_valid_endpoints(cred, expected):
    assert _resolve_mailchimp_base(cred) == expected


@pytest.mark.parametrize("cred", [
    {"apiEndpoint": "https://evil.example.com"},
    {"apiEndpoint": "http://us1.api.mailchimp.com"},
    {"apiEndpoint": "https://us1.api.mailchimp.com.evil.com"},
    {"apiEndpoint": "https://evil.com/.api.mailchimp.com"},
    {"apiEndpoint": "https://user:pw@us1.api.mailchimp.com"},
    {"apiEndpoint": "https://us1.api.mailchimp.com:8443"},
    {"serverPrefix": "evil.com#"},
    {"dc": "x.evil.com/"},
    {"apiKey": "abc-evil.com#"},
])
def test_rejects_non_mailchimp_hosts(cred):
    with pytest.raises(ValueError):
        _resolve_mailchimp_base(cred)
