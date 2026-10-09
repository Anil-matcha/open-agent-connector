"""
Google Calendar Provider for ConnectorHub.
Loads and registers actions from the centralized 'actions_catalog.json'.
Aligned with official Google Calendar REST API v3 specifications.
"""
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

GCAL_API_BASE = "https://www.googleapis.com/calendar/v3"

def _gcal_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Google Calendar OAuth Access Token or Bearer Token required. Please connect your Google Calendar account first.")
    return str(token).strip()

class GoogleCalendarDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "GET").upper()
        self.endpoint_template = action_meta.get("endpoint_template", "/calendars/{calendarId}/events")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _gcal_headers(token)
        inputs = dict(input_data or {})

        # Default calendarId to 'primary' if omitted or empty
        calendar_id = str(inputs.pop("calendarId", "primary") or "primary")

        # 1. Path variables substitution
        path = self.endpoint_template.replace("{calendarId}", urllib.parse.quote(calendar_id, safe=""))
        for var in ["eventId", "ruleId", "settingId", "id"]:
            placeholder = "{" + var + "}"
            if placeholder in path:
                val = inputs.pop(var, None)
                if val is None and var == "eventId":
                    val = inputs.pop("id", None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path = path.replace(placeholder, urllib.parse.quote(str(val), safe=""))

        # 2. Specialized composite handlers
        if self.id == "googlecalendar.add_attendee":
            return await self._handle_add_attendee(calendar_id, inputs, headers, client)

        if self.id == "googlecalendar.remove_attendee":
            return await self._handle_remove_attendee(calendar_id, inputs, headers, client)

        if self.id == "googlecalendar.quick_add_event":
            return await self._handle_quick_add(calendar_id, inputs, headers, client)

        # 3. Standard REST handling
        url = f"{GCAL_API_BASE}{path}"
        assert_public_url(url)

        body = None
        params = {}

        # Optional sendUpdates query param on write operations
        if "sendUpdates" in inputs:
            params["sendUpdates"] = str(inputs.pop("sendUpdates"))

        if self.method in ["POST", "PUT", "PATCH"]:
            # Check for structured inner objects matching schema patterns
            if "event" in inputs and isinstance(inputs["event"], dict):
                body = inputs.pop("event")
            elif "calendar" in inputs and isinstance(inputs["calendar"], dict):
                body = inputs.pop("calendar")
            elif "rule" in inputs and isinstance(inputs["rule"], dict):
                body = inputs.pop("rule")
            elif "entry" in inputs and isinstance(inputs["entry"], dict):
                body = inputs.pop("entry")
            elif self.id == "googlecalendar.add_calendar_to_list":
                body = {"id": calendar_id}
            else:
                body = inputs
        else:
            # GET / DELETE query parameters
            for k, v in inputs.items():
                if v is not None:
                    if isinstance(v, bool):
                        params[k] = "true" if v else "false"
                    elif isinstance(v, (list, tuple)):
                        params[k] = ",".join(str(item) for item in v)
                    else:
                        params[k] = str(v)

        resp = await execute_guarded_request(
            client=client,
            method=self.method,
            url=url,
            headers=headers,
            params=params if params else None,
            json_body=body if body is not None and self.method in ["POST", "PUT", "PATCH"] else None
        )

        if resp.status_code >= 400:
            err_text = resp.text
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message") or str(err_json)
            except Exception:
                msg = err_text[:300]
            raise ValueError(f"Google Calendar API error ({resp.status_code}): {msg}")

        if resp.status_code == 204 or not resp.content:
            return {"success": True, "message": "Operation completed successfully"}

        try:
            return resp.json()
        except Exception:
            return {"success": True, "raw": resp.text}

    async def _handle_add_attendee(
        self,
        calendar_id: str,
        inputs: Dict[str, Any],
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        event_id = str(inputs.get("eventId") or inputs.get("id") or "")
        if not event_id:
            raise ValueError("eventId is required to add an attendee.")

        attendee_email = str(inputs.get("attendeeEmail") or inputs.get("email") or "").strip()
        if not attendee_email:
            raise ValueError("attendeeEmail is required.")

        # 1. Fetch current event
        get_url = f"{GCAL_API_BASE}/calendars/{urllib.parse.quote(calendar_id, safe='')}/events/{urllib.parse.quote(event_id, safe='')}"
        assert_public_url(get_url)
        get_resp = await execute_guarded_request(client=client, method="GET", url=get_url, headers=headers)
        if get_resp.status_code != 200:
            raise ValueError(f"Failed to fetch event '{event_id}': {get_resp.text[:200]}")

        event_data = get_resp.json()
        attendees = list(event_data.get("attendees") or [])

        # Check if already present
        if not any(a.get("email", "").lower() == attendee_email.lower() for a in attendees):
            new_attendee: Dict[str, Any] = {"email": attendee_email}
            if inputs.get("displayName"):
                new_attendee["displayName"] = inputs["displayName"]
            if "optional" in inputs:
                new_attendee["optional"] = bool(inputs["optional"])
            attendees.append(new_attendee)

        # 2. Patch event with updated attendees
        patch_url = get_url
        send_updates = inputs.get("sendUpdates", "all")
        patch_resp = await execute_guarded_request(
            client=client,
            method="PATCH",
            url=patch_url,
            headers=headers,
            params={"sendUpdates": send_updates},
            json_body={"attendees": attendees}
        )
        if patch_resp.status_code >= 400:
            raise ValueError(f"Failed to update attendees: {patch_resp.text[:200]}")
        return patch_resp.json()

    async def _handle_remove_attendee(
        self,
        calendar_id: str,
        inputs: Dict[str, Any],
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        event_id = str(inputs.get("eventId") or inputs.get("id") or "")
        if not event_id:
            raise ValueError("eventId is required to remove an attendee.")

        attendee_email = str(inputs.get("attendeeEmail") or inputs.get("email") or "").strip()
        if not attendee_email:
            raise ValueError("attendeeEmail is required.")

        # 1. Fetch current event
        get_url = f"{GCAL_API_BASE}/calendars/{urllib.parse.quote(calendar_id, safe='')}/events/{urllib.parse.quote(event_id, safe='')}"
        assert_public_url(get_url)
        get_resp = await execute_guarded_request(client=client, method="GET", url=get_url, headers=headers)
        if get_resp.status_code != 200:
            raise ValueError(f"Failed to fetch event '{event_id}': {get_resp.text[:200]}")

        event_data = get_resp.json()
        attendees = [a for a in (event_data.get("attendees") or []) if a.get("email", "").lower() != attendee_email.lower()]

        # 2. Patch event
        send_updates = inputs.get("sendUpdates", "all")
        patch_resp = await execute_guarded_request(
            client=client,
            method="PATCH",
            url=get_url,
            headers=headers,
            params={"sendUpdates": send_updates},
            json_body={"attendees": attendees}
        )
        if patch_resp.status_code >= 400:
            raise ValueError(f"Failed to update attendees: {patch_resp.text[:200]}")
        return patch_resp.json()

    async def _handle_quick_add(
        self,
        calendar_id: str,
        inputs: Dict[str, Any],
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        text = str(inputs.get("text") or "").strip()
        if not text:
            raise ValueError("text is required for quickAddEvent (e.g. 'Lunch with Sarah at noon tomorrow').")

        url = f"{GCAL_API_BASE}/calendars/{urllib.parse.quote(calendar_id, safe='')}/events/quickAdd"
        assert_public_url(url)
        params = {"text": text}
        if "sendUpdates" in inputs:
            params["sendUpdates"] = str(inputs["sendUpdates"])

        resp = await execute_guarded_request(
            client=client,
            method="POST",
            url=url,
            headers=headers,
            params=params
        )
        if resp.status_code >= 400:
            raise ValueError(f"Failed to quick add event: {resp.text[:200]}")
        return resp.json()

class GoogleCalendarProvider(Provider):
    def __init__(self):
        super().__init__(
            service="googlecalendar",
            display_name="Google Calendar",
            category="Productivity",
            auth_types=["oauth2", "api_key"],
            description="Google Calendar REST API for scheduling meetings, managing events, checking availability, and viewing calendar lists.",
            homepage_url="https://calendar.google.com",
            base_url=GCAL_API_BASE,
            auth_configs=[
                {
                    "type": "oauth2",
                    "label": "Google OAuth 2.0 Access Token",
                    "placeholder": "ya29.a0...",
                    "description": "Authenticate via Google OAuth 2.0 application access token with Calendar scopes.",
                    "docs_url": "https://developers.google.com/calendar/api/guides/overview",
                    "docs_label": "Google Calendar API Documentation",
                    "setup_guide": {
                        "title": "Google Calendar Access Token Setup Guide",
                        "docs_url": "https://developers.google.com/oauthplayground",
                        "docs_label": "Google OAuth Playground",
                        "instructions": [
                            "1. Open Google OAuth Playground (developers.google.com/oauthplayground).",
                            "2. In the API list, scroll to 'Google Calendar API v3' and select the required scopes (e.g. calendar.events, calendar.readonly).",
                            "3. Click 'Authorize APIs' and log in with your Google account.",
                            "4. Click 'Exchange authorization code for tokens', then copy the Access token (starts with ya29...)."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/calendar.events",
                            "https://www.googleapis.com/auth/calendar.readonly",
                            "https://www.googleapis.com/auth/calendar",
                            "https://www.googleapis.com/auth/calendar.calendars",
                            "https://www.googleapis.com/auth/calendar.calendarlist"
                        ]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0...",
                            "description": "Google OAuth 2.0 access token issued with Calendar scopes."
                        }
                    ]
                },
                {
                    "type": "api_key",
                    "label": "Google Bearer Token / Service Account Token",
                    "placeholder": "ya29.a0... or Service Account Token",
                    "description": "Authenticate via Google OAuth Bearer token or service account credentials.",
                    "docs_url": "https://developers.google.com/calendar/api/quickstart/python",
                    "docs_label": "Google Calendar Quickstart Guide",
                    "setup_guide": {
                        "title": "Google Calendar Bearer Token Setup Guide",
                        "docs_url": "https://developers.google.com/calendar/api/quickstart/python",
                        "docs_label": "Google Calendar Quickstart Guide",
                        "instructions": [
                            "1. Obtain a valid Google OAuth Bearer access token or Service Account Token.",
                            "2. Ensure the token has the necessary Calendar scopes (calendar.events, calendar.readonly).",
                            "3. Enter the token below to connect."
                        ],
                        "scopes": [
                            "https://www.googleapis.com/auth/calendar.events",
                            "https://www.googleapis.com/auth/calendar.readonly",
                            "https://www.googleapis.com/auth/calendar"
                        ]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Bearer Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "ya29.a0...",
                            "description": "Google OAuth Bearer token."
                        }
                    ]
                }
            ]
        )

        # Load all actions cleanly from the centralized actions catalog
        for meta in get_provider_actions("googlecalendar"):
            self.register_action(GoogleCalendarDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate credentials against live Google Calendar API list endpoint."""
        token = _extract_token(credential)
        headers = _gcal_headers(token)
        url = f"{GCAL_API_BASE}/users/me/calendarList?maxResults=1"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Unable to reach Google Calendar API: {str(e)}")

        if resp.status_code == 401:
            raise ValueError("Invalid Google Calendar credentials. Google API returned 401 Unauthorized.")
        elif resp.status_code == 403:
            raise ValueError("Google Calendar permission denied (403 Forbidden). Verify Google Calendar API is enabled and scopes are granted.")
        elif resp.status_code != 200:
            raise ValueError(f"Google Calendar credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        items = data.get("items") or []
        primary_cal = next((c for c in items if c.get("primary")), items[0] if items else {})
        account_id = primary_cal.get("id") or "primary"
        summary = primary_cal.get("summary") or account_id

        return {
            "account_id": account_id,
            "display_name": f"Google Calendar ({summary})",
            "granted_scopes": [
                "https://www.googleapis.com/auth/calendar.events",
                "https://www.googleapis.com/auth/calendar.readonly",
                "https://www.googleapis.com/auth/calendar"
            ],
            "avatar_url": None
        }

    async def proxy(
        self,
        endpoint: str,
        method: str,
        credential: Optional[Dict[str, Any]],
        body: Any,
        headers: Dict[str, str],
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """SSRF-guarded proxy forwarder for Google Calendar API."""
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"{GCAL_API_BASE}{clean_endpoint}"
        assert_public_url(target_url)

        req_headers = dict(headers or {})
        req_headers.update(_gcal_headers(token))

        resp = await execute_guarded_request(
            client=client,
            method=method.upper(),
            url=target_url,
            headers=req_headers,
            json_body=body if body and method.upper() in ["POST", "PUT", "PATCH"] else None
        )

        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }
