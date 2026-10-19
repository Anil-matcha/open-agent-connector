"""
Cal.com Provider for ConnectorHub.
Loads and registers 47 actions with exact route definitions and parameters.
"""
import base64
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

DEFAULT_API_BASE = "https://api.cal.com"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    # Replace any custom domains/subdomains/tenants in base template
    for key in ["domain", "subdomain", "host", "tenant"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    return base

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "Bearer"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "basic_key":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "basic_key_secret":
        k = str(cred.get("accessKey") or cred.get("key") or token).strip()
        s = str(cred.get("accessKeySecret") or cred.get("secret") or "").strip()
        pair = f"{k}:{s}"
        headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "ssws":
        if token:
            headers["Authorization"] = f"SSWS {token}"
    elif auth_mode == "bamboo_basic":
        if token:
            pair = f"{token}:x"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "api_key_or_bearer":
        if token:
            headers["Authorization"] = f"API-Key {token}"

    return headers

ROUTES: Dict[str, List[Any]] = {
    "add_attendee": [
        "POST",
        "/v2/add_attendee",
        [
            "bookingUid"
        ],
        [
            "name",
            "email",
            "timeZone",
            "phoneNumber",
            "language"
        ]
    ],
    "cancel_booking": [
        "POST",
        "/v2/bookings/{bookingUid}/cancel",
        [
            "bookingUid",
            "seatUid"
        ],
        [
            "cancellationReason",
            "cancelSubsequentBookings"
        ]
    ],
    "cancel_booking_via_uid": [
        "POST",
        "/v2/bookings/{bookingUid}/cancel",
        [
            "bookingUid",
            "seatUid"
        ],
        [
            "cancellationReason",
            "cancelSubsequentBookings"
        ]
    ],
    "confirm_booking_by_uid": [
        "POST",
        "/v2/bookings/{bookingUid}/confirm",
        [
            "bookingUid"
        ],
        []
    ],
    "create_booking": [
        "POST",
        "/v2/bookings",
        [
            "eventTypeId"
        ],
        [
            "start",
            "attendee",
            "eventTypeSlug",
            "username",
            "teamSlug",
            "organizationSlug",
            "bookingFieldsResponses",
            "guests",
            "meetingUrl",
            "location",
            "metadata",
            "lengthInMinutes",
            "routing",
            "emailVerificationCode",
            "instant"
        ]
    ],
    "create_event_type": [
        "POST",
        "/v2/event-types",
        [],
        [
            "title",
            "slug",
            "lengthInMinutes",
            "description"
        ]
    ],
    "create_schedule": [
        "POST",
        "/v2/schedules",
        [],
        [
            "name",
            "timeZone",
            "isDefault",
            "availability",
            "overrides"
        ]
    ],
    "create_user_availability_schedule": [
        "POST",
        "/v2/schedules",
        [],
        [
            "name",
            "timeZone",
            "isDefault",
            "availability",
            "overrides"
        ]
    ],
    "decline_booking_with_reason": [
        "POST",
        "/v2/bookings/{bookingUid}/decline",
        [
            "bookingUid"
        ],
        [
            "reason"
        ]
    ],
    "delete_event_type": [
        "DELETE",
        "/v2/event-types/{eventTypeId}",
        [
            "eventTypeId"
        ],
        []
    ],
    "delete_event_type_by_id": [
        "DELETE",
        "/v2/event-types/{eventTypeId}",
        [
            "eventTypeId"
        ],
        []
    ],
    "delete_schedule": [
        "DELETE",
        "/v2/schedules/{scheduleId}",
        [
            "scheduleId"
        ],
        []
    ],
    "delete_schedule_by_id": [
        "DELETE",
        "/v2/schedules/{scheduleId}",
        [
            "scheduleId"
        ],
        []
    ],
    "fetch_all_bookings": [
        "GET",
        "/v2/bookings",
        [
            "teamId",
            "eventTypeId"
        ],
        [
            "skip",
            "take",
            "status",
            "teamsIds",
            "sortStart",
            "sortEnd",
            "sortCreated",
            "afterStart",
            "beforeEnd",
            "attendeeName",
            "attendeeEmail",
            "eventTypeIds"
        ]
    ],
    "fetch_event_type_details": [
        "GET",
        "/v2/event-types/{eventTypeId}",
        [
            "eventTypeId",
            "teamId"
        ],
        [
            "username"
        ]
    ],
    "fetch_schedule_by_id": [
        "GET",
        "/v2/schedules/{scheduleId}",
        [
            "scheduleId"
        ],
        []
    ],
    "get_available_slots_info": [
        "GET",
        "/v2/slots/available",
        [
            "eventTypeId"
        ],
        [
            "eventTypeSlug",
            "username",
            "usernames",
            "teamSlug",
            "organizationSlug",
            "start",
            "end",
            "timeZone",
            "duration",
            "format",
            "bookingUidToReschedule"
        ]
    ],
    "get_booking": [
        "GET",
        "/v2/bookings/{bookingUid}",
        [
            "bookingUid"
        ],
        []
    ],
    "get_booking_references": [
        "GET",
        "/v2/bookings/{bookingUid}/references",
        [
            "bookingUid"
        ],
        [
            "type"
        ]
    ],
    "get_default_schedule": [
        "GET",
        "/v2/schedules",
        [],
        []
    ],
    "get_default_schedule_details": [
        "GET",
        "/v2/schedules",
        [],
        []
    ],
    "get_event_type": [
        "GET",
        "/v2/event-types/{eventTypeId}",
        [
            "eventTypeId",
            "teamId"
        ],
        [
            "username"
        ]
    ],
    "get_event_type_private_links": [
        "GET",
        "/v2/event-types/{eventTypeId}",
        [
            "eventTypeId"
        ],
        []
    ],
    "get_my_profile": [
        "GET",
        "/v2/me",
        [],
        []
    ],
    "get_schedule": [
        "GET",
        "/v2/schedules/{scheduleId}",
        [
            "scheduleId"
        ],
        []
    ],
    "list_attendees": [
        "GET",
        "/v2/list_attendees",
        [
            "bookingUid"
        ],
        []
    ],
    "list_booking_references": [
        "GET",
        "/v2/bookings/{bookingUid}/references",
        [
            "bookingUid"
        ],
        [
            "type"
        ]
    ],
    "list_bookings": [
        "GET",
        "/v2/bookings",
        [
            "eventTypeId"
        ],
        [
            "status",
            "attendeeEmail",
            "eventTypeSlug",
            "sortStart",
            "sortEnd",
            "afterStart",
            "beforeStart",
            "afterEnd",
            "beforeEnd",
            "limit",
            "cursor"
        ]
    ],
    "list_event_types": [
        "GET",
        "/v2/event-types",
        [
            "teamId"
        ],
        [
            "limit",
            "cursor",
            "username",
            "status",
            "schedulingType",
            "onlyActive"
        ]
    ],
    "list_schedules": [
        "GET",
        "/v2/schedules",
        [],
        [
            "limit",
            "cursor"
        ]
    ],
    "mark_booking_absent_for_uid": [
        "GET",
        "/v2/bookings/{bookingUid}",
        [
            "bookingUid"
        ],
        [
            "host",
            "attendees"
        ]
    ],
    "post_new_booking_request": [
        "POST",
        "/v2/bookings",
        [
            "eventTypeId"
        ],
        [
            "start",
            "attendee",
            "eventTypeSlug",
            "username",
            "teamSlug",
            "organizationSlug",
            "bookingFieldsResponses",
            "guests",
            "meetingUrl",
            "location",
            "metadata",
            "lengthInMinutes",
            "routing",
            "emailVerificationCode",
            "instant"
        ]
    ],
    "reassign_booking_with_uid": [
        "GET",
        "/v2/bookings/{bookingUid}",
        [
            "bookingUid",
            "userId"
        ],
        [
            "reason"
        ]
    ],
    "reschedule_booking": [
        "POST",
        "/v2/bookings/{bookingUid}/reschedule",
        [
            "bookingUid"
        ],
        [
            "start",
            "rescheduledBy",
            "reason",
            "reschedulingReason",
            "emailVerificationCode"
        ]
    ],
    "reschedule_booking_by_uid": [
        "POST",
        "/v2/bookings/{bookingUid}/reschedule",
        [
            "bookingUid"
        ],
        [
            "start",
            "rescheduledBy",
            "reason",
            "reschedulingReason",
            "emailVerificationCode"
        ]
    ],
    "retrieve_booking_details_by_uid": [
        "GET",
        "/v2/bookings/{bookingUid}",
        [
            "bookingUid"
        ],
        []
    ],
    "retrieve_calendar_busy_times": [
        "GET",
        "/v2/retrieve_calendar_busy_times",
        [],
        [
            "timeZone",
            "loggedInUsersTz",
            "dateFrom",
            "dateTo",
            "calendarsToLoad"
        ]
    ],
    "retrieve_calendar_list": [
        "GET",
        "/v2/retrieve_calendar_list",
        [],
        []
    ],
    "retrieve_event_type_by_id": [
        "GET",
        "/v2/event-types/{eventTypeId}",
        [
            "eventTypeId",
            "teamId"
        ],
        [
            "username"
        ]
    ],
    "retrieve_my_information": [
        "GET",
        "/v2/me",
        [],
        []
    ],
    "retrieve_schedules_list": [
        "GET",
        "/v2/schedules",
        [],
        []
    ],
    "update_destination_calendar_integration": [
        "PATCH",
        "/v2/update_destination_calendar_integration",
        [
            "externalId",
            "delegationCredentialId"
        ],
        [
            "integration"
        ]
    ],
    "update_event_type": [
        "PATCH",
        "/v2/event-types/{eventTypeId}",
        [
            "eventTypeId"
        ],
        []
    ],
    "update_my_profile": [
        "PATCH",
        "/v2/me",
        [
            "defaultScheduleId"
        ],
        [
            "name",
            "bio",
            "avatarUrl",
            "brandColor",
            "darkBrandColor",
            "theme",
            "timeZone",
            "weekStart",
            "timeFormat",
            "locale",
            "email"
        ]
    ],
    "update_schedule": [
        "PATCH",
        "/v2/schedules/{scheduleId}",
        [
            "scheduleId"
        ],
        [
            "name",
            "timeZone",
            "isDefault",
            "availability",
            "overrides"
        ]
    ],
    "update_schedule_by_id": [
        "PATCH",
        "/v2/schedules/{scheduleId}",
        [
            "scheduleId"
        ],
        [
            "name",
            "timeZone",
            "isDefault",
            "availability",
            "overrides"
        ]
    ],
    "update_user_profile_details": [
        "PATCH",
        "/v2/me",
        [
            "defaultScheduleId"
        ],
        [
            "name",
            "bio",
            "avatarUrl",
            "brandColor",
            "darkBrandColor",
            "theme",
            "timeZone",
            "weekStart",
            "timeFormat",
            "locale",
            "email"
        ]
    ]
}

class CalDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Project Management"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        base_url = _resolve_base_url(cred)
        headers = _build_headers(cred)

        req_method, path_template, path_vars, query_keys = self.route_info
        path = path_template

        for var in path_vars:
            val = input_data.get(var)
            if val is None:
                alt = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                val = input_data.get(alt)
            if val is not None:
                path = path.replace("{" + var + "}", urllib.parse.quote(str(val), safe=""))

        path = re.sub(r"/\{[^}]+\}", "", path)

        target_url = f"{base_url}{path}" if not path.startswith("http") else path
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

        # For Trello, append key & token to params
        if "cal" == "trello":
            if cred.get("apiKey") or cred.get("key"):
                params["key"] = str(cred.get("apiKey") or cred.get("key"))
            if cred.get("token"):
                params["token"] = str(cred.get("token"))

        for k, v in input_data.items():
            if k in path_vars:
                continue
            if k in query_keys or (req_method == "GET"):
                params[k] = v
            else:
                body[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=req_method,
            url=target_url,
            headers=headers,
            params=params if params else None,
            json_body=body if (req_method in ["POST", "PUT", "PATCH"] and body) else None
        )

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("error_summary") or resp.text
            raise ValueError(f"Cal.com API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class CalProvider(Provider):
    def __init__(self):
        super().__init__(
            service="cal",
            display_name="Cal.com",
            category="Project Management",
            auth_types=["oauth2", "api_key"],
            description="Cal.com scheduling infrastructure and bookings management with 47 actions."
        )
        for act in get_provider_actions("cal"):
            self.register_action(CalDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.cal.com/v2/me"
        for key in ["domain", "subdomain", "host", "tenant"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        params = {}
        if "cal" == "trello":
            if cred.get("apiKey") or cred.get("key"):
                params["key"] = str(cred.get("apiKey") or cred.get("key"))
            if cred.get("token"):
                params["token"] = str(cred.get("token"))

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=headers,
            params=params if params else None
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Cal.com credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Cal.com validation failed: {resp.status_code} {resp.text}")

        body = resp.json() if isinstance(resp.text, str) and resp.text.startswith("{") else {}
        user_data = body.get("data", {}) if isinstance(body.get("data"), dict) else body
        token = _extract_token(cred)
        account_id = str(user_data.get("id") or user_data.get("username") or (token[:8] + "..." if token else "verified"))
        display_name = user_data.get("name") or user_data.get("username") or user_data.get("email") or "Cal.com Account"
        return {
            "valid": True,
            "accountId": account_id,
            "displayName": display_name,
            "metadata": {
                "email": user_data.get("email"),
                "username": user_data.get("username"),
                "name": user_data.get("name"),
                "timeZone": user_data.get("timeZone")
            }
        }
