"""
GitHub Provider for ConnectorHub.
Loads and registers actions from 'actions_catalog.json'.
Aligned with the provider action specifications.
"""
import json
import base64
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url

def _github_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("apiKey") or (credential or {}).get("accessToken")
    if not token or not str(token).strip():
        raise ValueError("GitHub credentials required. Please connect your GitHub account first.")
    return str(token).strip()

class GitHubDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Repositories"),
            required_scopes=action_meta.get("requiredScopes", ["repo"]),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.method = action_meta.get("method", "GET")
        self.endpoint_template = action_meta.get("endpoint_template", "/user")
        self.query_params = set(action_meta.get("query_params", []))
        self.body_params = set(action_meta.get("body_params", []))
        self.special = action_meta.get("special")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        headers = _github_headers(token)
        inputs = dict(input_data or {})
        
        # 1. Path variables substitution
        path_params = {}
        template = self.endpoint_template
        for var in [
            "owner", "repo", "username", "org", "branch", "ref", "sha",
            "commitSha", "issueNumber", "pullNumber", "commentId", "reviewId",
            "runId", "jobId", "releaseId", "assetId", "workflowId",
            "checkRunId", "checkSuiteId", "milestoneNumber", "name", "tag",
            "basehead", "artifactId"
        ]:
            placeholder = "{" + var + "}"
            if placeholder in template:
                val = inputs.pop(var, None)
                if val is None:
                    snake = "".join(["_" + c.lower() if c.isupper() else c for c in var]).lstrip("_")
                    val = inputs.pop(snake, None)
                if val is None:
                    raise ValueError(f"Missing required parameter '{var}' for action '{self.id}'")
                path_params[var] = urllib.parse.quote(str(val), safe="")
        
        if "{path}" in template:
            file_path = str(inputs.pop("path", "")).strip().lstrip("/")
            template = template.replace("{path}", urllib.parse.quote(file_path, safe="/"))
        
        path = template.format(**path_params) if path_params else template
        url = f"https://api.github.com{path}"
        assert_public_url(url)
        
        # 2. Query vs Body parameters separation
        params = {}
        body = {}
        for k, v in inputs.items():
            if v is None or v == "":
                continue
            if self.method in ["GET", "DELETE"] or k in self.query_params or k in ["per_page", "perPage", "page", "sort", "direction", "state", "ref"]:
                qkey = "per_page" if k in ["perPage", "per_page"] else k
                params[qkey] = v
            else:
                body[k] = v
        
        # 3. Special file content encoding
        if self.special == "write_file" and "content" in body:
            raw_c = str(body["content"])
            try:
                base64.b64decode(raw_c, validate=True)
            except Exception:
                body["content"] = base64.b64encode(raw_c.encode("utf-8")).decode("utf-8")
        
        req_payload = body if (self.method in ["POST", "PUT", "PATCH"] and body) else None
        resp = await client.request(self.method, url, headers=headers, params=params or None, json=req_payload)
        
        if resp.status_code == 204:
            return {"status": 204, "success": True, "message": "Operation completed successfully."}
        if resp.status_code == 401:
            raise ValueError("GitHub authentication failed: invalid token or expired credentials (401 Unauthorized).")
        if resp.status_code == 404:
            raise ValueError(f"GitHub resource not found at '{url}' (404 Not Found).")
        if resp.status_code >= 400:
            err_text = resp.text[:400]
            raise ValueError(f"GitHub API error ({resp.status_code}): {err_text}")
        
        try:
            data = resp.json()
        except Exception:
            return {"status": resp.status_code, "text": resp.text}
        
        # 4. Special file content decoding
        if self.special in ["file", "readme"] and isinstance(data, dict):
            if data.get("encoding") == "base64" and data.get("content"):
                try:
                    data["decoded_content"] = base64.b64decode(data["content"]).decode("utf-8")
                except Exception:
                    data["decoded_content"] = "[Binary or unparseable text]"
        
        return data

class GitHubProvider(Provider):
    def __init__(self):
        super().__init__(
            service="github",
            display_name="GitHub",
            category="Developer Tools",
            auth_types=["api_key", "oauth2"],
            description="GitHub REST API for managing repositories, code, issues, pull requests, and workflows.",
            homepage_url="https://github.com",
            base_url="https://api.github.com",
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Personal Access Token (PAT)",
                    "placeholder": "github_pat_... or ghp_...",
                    "description": "Create a Personal Access Token with 'repo' and 'read:user' permissions.",
                    "docs_url": "https://github.com/settings/tokens",
                    "docs_label": "Create token on GitHub",
                    "setup_guide": {
                        "title": "GitHub Token Setup Guide",
                        "docs_url": "https://github.com/settings/tokens",
                        "docs_label": "Create token on GitHub",
                        "instructions": [
                            "1. Go to GitHub Settings > Developer settings > Personal access tokens.",
                            "2. Click 'Generate new token' (Tokens classic or Fine-grained).",
                            "3. Select the 'repo' scope for repository and code access.",
                            "4. Select the 'read:user' scope for profile verification, then copy the token."
                        ],
                        "scopes": ["repo", "read:user"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "github_pat_... or ghp_...",
                            "description": "Your GitHub Personal Access Token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "OAuth 2.0 Access Token",
                    "placeholder": "gho_...",
                    "description": "Authenticate via OAuth 2.0 application access token.",
                    "docs_url": "https://docs.github.com/en/apps/oauth-apps",
                    "docs_label": "GitHub OAuth Docs",
                    "setup_guide": {
                        "title": "GitHub OAuth Setup Guide",
                        "docs_url": "https://docs.github.com/en/apps/oauth-apps",
                        "docs_label": "GitHub OAuth Docs",
                        "instructions": [
                            "Authorize directly using OAuth 2.0 PKCE, or enter an issued OAuth access token (gho_...)."
                        ],
                        "scopes": ["repo", "read:user"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "gho_...",
                            "description": "OAuth access token issued by GitHub."
                        }
                    ]
                }
            ]
        )
        
        # Load all actions cleanly from the centralized actions catalog
        for meta in get_provider_actions("github"):
            self.register_action(GitHubDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = credential.get("apiKey") or credential.get("accessToken")
        if not token or not str(token).strip():
            raise ValueError("GitHub personal access token or OAuth token is required.")
        
        token = str(token).strip()
        headers = _github_headers(token)
        url = "https://api.github.com/user"
        assert_public_url(url)
        
        try:
            resp = await client.get(url, headers=headers)
        except Exception as e:
            raise ValueError(f"Unable to reach GitHub API: {str(e)}")
            
        if resp.status_code == 401:
            raise ValueError("Invalid GitHub credentials. GitHub API returned 401 Unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"GitHub credential validation failed with status {resp.status_code}: {resp.text}")

        user = resp.json()
        scopes_header = resp.headers.get("x-oauth-scopes", "")
        scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]
        
        return {
            "account_id": user.get("login") or str(user.get("id")),
            "display_name": user.get("name") or user.get("login") or "GitHub User",
            "avatar_url": user.get("avatar_url"),
            "granted_scopes": scopes
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
        token = _extract_token(credential)
        clean_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        target_url = f"https://api.github.com{clean_endpoint}"
        assert_public_url(target_url)
        
        req_headers = dict(headers or {})
        req_headers.update(_github_headers(token))

        resp = await client.request(method=method, url=target_url, json=body if body else None, headers=req_headers)
        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "data": resp_data
        }
