"""
Webex Provider for ConnectorHub.
Loads and registers 40 actions with exact route definitions and parameters.
"""
import json
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

WEBEX_API_BASE = "https://webexapis.com/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["accessToken", "token", "access_token", "apiKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    raise ValueError("Webex OAuth access token required. Please connect your Webex account first.")

def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

ROUTES: Dict[str, List[Any]] = {
    "create_meeting": [
        "POST",
        "/meetings",
        [],
        []
    ],
    "create_membership": [
        "POST",
        "/memberships",
        [],
        []
    ],
    "create_message": [
        "POST",
        "/messages",
        [],
        []
    ],
    "create_room": [
        "POST",
        "/rooms",
        [],
        []
    ],
    "create_team": [
        "POST",
        "/teams",
        [],
        []
    ],
    "create_team_membership": [
        "POST",
        "/team/memberships",
        [],
        []
    ],
    "delete_meeting": [
        "DELETE",
        "/meetings/{meetingId}",
        [
            "meetingId"
        ],
        [
            "sendEmail"
        ]
    ],
    "delete_membership": [
        "DELETE",
        "/memberships/{membershipId}",
        [
            "membershipId"
        ],
        []
    ],
    "delete_message": [
        "DELETE",
        "/messages/{messageId}",
        [
            "messageId"
        ],
        []
    ],
    "delete_room": [
        "DELETE",
        "/rooms/{roomId}",
        [
            "roomId"
        ],
        []
    ],
    "delete_team": [
        "DELETE",
        "/teams/{teamId}",
        [
            "teamId"
        ],
        []
    ],
    "delete_team_membership": [
        "DELETE",
        "/team/memberships/{membershipId}",
        [
            "membershipId"
        ],
        []
    ],
    "download_meeting_transcript": [
        "GET",
        "/meetingTranscripts/{transcriptId}/download",
        [
            "transcriptId"
        ],
        [
            "format"
        ]
    ],
    "get_meeting": [
        "GET",
        "/meetings/{meetingId}",
        [
            "meetingId"
        ],
        []
    ],
    "get_meeting_participant": [
        "GET",
        "/get_meeting_participant",
        [],
        []
    ],
    "get_meeting_summary": [
        "GET",
        "/meetingSummaries",
        [],
        [
            "meetingId"
        ]
    ],
    "get_membership": [
        "GET",
        "/memberships/{membershipId}",
        [
            "membershipId"
        ],
        []
    ],
    "get_message": [
        "GET",
        "/messages/{messageId}",
        [
            "messageId"
        ],
        []
    ],
    "get_person": [
        "GET",
        "/people/{personId}",
        [
            "personId"
        ],
        [
            "callingData"
        ]
    ],
    "get_recording": [
        "GET",
        "/recordings/{recordingId}",
        [
            "recordingId"
        ],
        []
    ],
    "get_room": [
        "GET",
        "/rooms/{roomId}",
        [
            "roomId"
        ],
        []
    ],
    "get_team": [
        "GET",
        "/teams/{teamId}",
        [
            "teamId"
        ],
        []
    ],
    "get_team_membership": [
        "GET",
        "/team/memberships/{membershipId}",
        [
            "membershipId"
        ],
        []
    ],
    "list_direct_messages": [
        "GET",
        "/messages/direct",
        [],
        [
            "parentId",
            "personId",
            "personEmail"
        ]
    ],
    "list_meeting_participants": [
        "GET",
        "/meetingParticipants",
        [],
        [
            "meetingId",
            "hostEmail",
            "max"
        ]
    ],
    "list_meeting_transcripts": [
        "GET",
        "/meetingTranscripts",
        [],
        [
            "meetingId",
            "max"
        ]
    ],
    "list_meetings": [
        "GET",
        "/meetings",
        [],
        [
            "meetingType",
            "state",
            "from",
            "to",
            "max"
        ]
    ],
    "list_memberships": [
        "GET",
        "/memberships",
        [],
        [
            "roomId",
            "personId",
            "personEmail",
            "max"
        ]
    ],
    "list_messages": [
        "GET",
        "/messages",
        [],
        [
            "roomId",
            "parentId",
            "mentionedPeople",
            "before",
            "beforeMessage",
            "max"
        ]
    ],
    "list_people": [
        "GET",
        "/people",
        [],
        [
            "email",
            "displayName",
            "id",
            "roles",
            "callingData",
            "locationId",
            "max"
        ]
    ],
    "list_recordings": [
        "GET",
        "/recordings",
        [],
        [
            "meetingId",
            "from",
            "to",
            "max"
        ]
    ],
    "list_rooms": [
        "GET",
        "/rooms",
        [],
        [
            "teamId",
            "type",
            "orgPublicSpaces",
            "from",
            "to",
            "sortBy",
            "max"
        ]
    ],
    "list_team_memberships": [
        "GET",
        "/team/memberships",
        [],
        [
            "teamId",
            "max"
        ]
    ],
    "list_teams": [
        "GET",
        "/teams",
        [],
        [
            "max"
        ]
    ],
    "update_meeting": [
        "PATCH",
        "/meetings/{meetingId}",
        [
            "meetingId"
        ],
        []
    ],
    "update_membership": [
        "PUT",
        "/memberships/{membershipId}",
        [
            "membershipId"
        ],
        []
    ],
    "update_message": [
        "PUT",
        "/messages/{messageId}",
        [
            "messageId"
        ],
        []
    ],
    "update_room": [
        "PUT",
        "/rooms/{roomId}",
        [
            "roomId"
        ],
        []
    ],
    "update_team": [
        "PUT",
        "/teams/{teamId}",
        [
            "teamId"
        ],
        []
    ],
    "update_team_membership": [
        "PUT",
        "/team/memberships/{membershipId}",
        [
            "membershipId"
        ],
        []
    ]
}

class WebexDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Communication"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.action_name = action_meta["name"]
        self.route_info = ROUTES.get(self.action_name, [action_meta.get("method", "GET"), action_meta.get("endpoint", f"/{self.action_name}"), [], []])

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _headers(token)

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

        target_url = f"{WEBEX_API_BASE}{path}"
        assert_public_url(target_url)

        params: Dict[str, Any] = {}
        body: Dict[str, Any] = {}

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
            err_msg = data.get("message") or data.get("error") or resp.text
            raise ValueError(f"Webex API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class WebexProvider(Provider):
    def __init__(self):
        super().__init__(
            service="webex",
            display_name="Webex",
            category="Communication",
            auth_types=["oauth2"],
            description="Cisco Webex messaging, meetings, and team collaboration suite with 40 actions."
        )
        for act in get_provider_actions("webex"):
            self.register_action(WebexDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        val_url = f"{WEBEX_API_BASE}/people/me"
        assert_public_url(val_url)

        resp = await execute_guarded_request(
            client=client,
            method="GET",
            url=val_url,
            headers=_headers(token)
        )

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Webex credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Webex validation failed: {resp.status_code} {resp.text}")

        try:
            me = resp.json()
            p_id = str(me.get("id", "verified"))
            p_name = me.get("displayName") or me.get("nickName") or me.get("emails", [""])[0] or p_id
        except Exception:
            p_id = "verified"
            p_name = "Webex User"

        return {
            "account_id": p_id,
            "display_name": f"Webex ({p_name})"
        }
