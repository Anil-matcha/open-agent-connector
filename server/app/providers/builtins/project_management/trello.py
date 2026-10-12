"""
Trello Provider for ConnectorHub.
Loads and registers 28 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "https://api.trello.com/1"

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

    auth_mode = "custom"
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
    "add_card_attachment_url": [
        "POST",
        "/cards/{cardId}/attachments",
        [
            "cardId"
        ],
        [
            "url",
            "name"
        ]
    ],
    "add_card_comment": [
        "POST",
        "/cards/{cardId}/actions/comments",
        [
            "cardId"
        ],
        [
            "text"
        ]
    ],
    "add_card_label": [
        "POST",
        "/cards/{cardId}/idLabels",
        [
            "cardId",
            "labelId"
        ],
        []
    ],
    "add_card_member": [
        "POST",
        "/members/me",
        [
            "cardId",
            "memberId"
        ],
        []
    ],
    "add_checkitem": [
        "POST",
        "/add_checkitem",
        [
            "checklistId"
        ],
        [
            "name",
            "position",
            "checked"
        ]
    ],
    "archive_card": [
        "PUT",
        "/cards/{cardId}/closed",
        [
            "cardId"
        ],
        []
    ],
    "archive_list": [
        "PUT",
        "/lists/{listId}/closed",
        [
            "listId"
        ],
        []
    ],
    "create_board": [
        "POST",
        "/boards",
        [],
        [
            "name",
            "description",
            "defaultLists",
            "permissionLevel"
        ]
    ],
    "create_card": [
        "POST",
        "/cards",
        [
            "listId"
        ],
        [
            "name",
            "description",
            "due",
            "position",
            "memberIds",
            "labelIds"
        ]
    ],
    "create_checklist": [
        "POST",
        "/lists",
        [
            "cardId"
        ],
        [
            "name"
        ]
    ],
    "create_list": [
        "POST",
        "/lists",
        [
            "boardId"
        ],
        [
            "name",
            "position"
        ]
    ],
    "get_board": [
        "GET",
        "/boards/{boardId}",
        [
            "boardId"
        ],
        [
            "fields"
        ]
    ],
    "get_card": [
        "GET",
        "/cards/{cardId}",
        [
            "cardId"
        ],
        [
            "fields"
        ]
    ],
    "get_member": [
        "GET",
        "/members/me",
        [
            "memberId"
        ],
        [
            "fields"
        ]
    ],
    "list_board_cards": [
        "GET",
        "/boards/{boardId}/lists",
        [
            "boardId"
        ],
        [
            "filter",
            "fields"
        ]
    ],
    "list_board_labels": [
        "GET",
        "/boards/{boardId}/lists",
        [
            "boardId"
        ],
        []
    ],
    "list_board_lists": [
        "GET",
        "/boards/{boardId}/lists",
        [
            "boardId"
        ],
        [
            "filter"
        ]
    ],
    "list_board_members": [
        "GET",
        "/members/{id}/boards",
        [
            "boardId"
        ],
        [
            "fields"
        ]
    ],
    "list_card_checklists": [
        "GET",
        "/lists/{listId}/cards",
        [
            "cardId"
        ],
        []
    ],
    "list_card_comments": [
        "GET",
        "/lists/{listId}/cards",
        [
            "cardId"
        ],
        [
            "limit"
        ]
    ],
    "list_member_boards": [
        "GET",
        "/members/{id}/boards",
        [
            "memberId"
        ],
        [
            "fields",
            "filter"
        ]
    ],
    "move_card": [
        "GET",
        "/cards/{cardId}",
        [
            "cardId",
            "listId"
        ],
        [
            "position"
        ]
    ],
    "remove_card_label": [
        "GET",
        "/cards/{cardId}/idLabels",
        [
            "cardId",
            "labelId"
        ],
        []
    ],
    "remove_card_member": [
        "GET",
        "/members/me",
        [
            "cardId",
            "memberId"
        ],
        []
    ],
    "search": [
        "GET",
        "/search",
        [],
        [
            "query",
            "modelTypes",
            "cardsLimit",
            "boardsLimit",
            "membersLimit"
        ]
    ],
    "update_card": [
        "PUT",
        "/cards/{cardId}",
        [
            "cardId",
            "listId"
        ],
        [
            "name",
            "description",
            "due",
            "position",
            "memberIds",
            "labelIds",
            "closed",
            "dueComplete"
        ]
    ],
    "update_checkitem_state": [
        "PUT",
        "/update_checkitem_state",
        [
            "cardId",
            "checkItemId"
        ],
        [
            "state"
        ]
    ],
    "update_list": [
        "PUT",
        "/lists/{listId}",
        [
            "listId"
        ],
        [
            "name",
            "position"
        ]
    ]
}

class TrelloDynamicAction(Action):
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
        if "trello" == "trello":
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
            raise ValueError(f"Trello API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class TrelloProvider(Provider):
    def __init__(self):
        super().__init__(
            service="trello",
            display_name="Trello",
            category="Project Management",
            auth_types=["custom_credential"],
            description="Trello visual work management boards, lists, cards, and checklists with 28 actions."
        )
        for act in get_provider_actions("trello"):
            self.register_action(TrelloDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "https://api.trello.com/1/members/me"
        for key in ["domain", "subdomain", "host", "tenant"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))

        assert_public_url(val_url)
        headers = _build_headers(cred)

        params = {}
        if "trello" == "trello":
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
            raise ValueError(f"Invalid Trello credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Trello validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Trello Account"
        }
