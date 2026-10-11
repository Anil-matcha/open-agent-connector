"""
Linear Provider for ConnectorHub.
Loads and registers 34 actions from 'actions_catalog.json'.
Full support for issues, projects, cycles, teams, and GraphQL queries via Linear API.
"""
from typing import Dict, Any, Optional
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

def _linear_headers(token: str) -> Dict[str, str]:
    auth = token if token.startswith("Bearer ") or token.startswith("lin_api_") else f"Bearer {token}"
    return {
        "Authorization": auth,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    token = (credential or {}).get("accessToken") or (credential or {}).get("apiKey")
    if not token or not str(token).strip():
        raise ValueError("Linear Personal API Key or OAuth Access Token required. Please connect your Linear account first.")
    return str(token).strip()

# Canonical GraphQL operations for standard Linear actions
LINEAR_QUERY_TEMPLATES = {
    "get_current_user": "query { viewer { id name email displayName avatarUrl } }",
    "get_all_linear_teams": "query { teams { nodes { id name key description } } }",
    "list_linear_teams": "query { teams { nodes { id name key description } } }",
    "list_linear_issues": "query ListIssues($first: Int) { issues(first: $first) { nodes { id identifier title description priority state { id name } assignee { id name } } } }",
    "get_linear_issue": "query GetIssue($id: String!) { issue(id: $id) { id identifier title description priority url state { id name } assignee { id name } project { id name } } }",
    "search_issues": "query SearchIssues($term: String!) { issueSearch(query: $term) { nodes { id identifier title state { name } } } }",
    "list_linear_projects": "query { projects { nodes { id name state description progress targetDate } } }",
    "get_linear_project": "query GetProject($id: String!) { project(id: $id) { id name state description progress targetDate } }",
    "list_linear_cycles": "query { cycles { nodes { id number name startsAt endsAt progress } } }",
    "list_linear_labels": "query { issueLabels { nodes { id name color description } } }",
    "list_linear_states": "query { workflowStates { nodes { id name type color } } }",
    "list_linear_users": "query { users { nodes { id name displayName email active } } }",
    "create_linear_issue": "mutation CreateIssue($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id identifier title url } } }",
    "update_issue": "mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) { issueUpdate(id: $id, input: $input) { success issue { id identifier title } } }",
    "delete_linear_issue": "mutation DeleteIssue($id: String!) { issueDelete(id: $id) { success } }",
    "create_linear_comment": "mutation CreateComment($input: CommentCreateInput!) { commentCreate(input: $input) { success comment { id body } } }",
    "create_linear_project": "mutation CreateProject($input: ProjectCreateInput!) { projectCreate(input: $input) { success project { id name } } }",
}

class LinearDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "General"),
            required_scopes=action_meta.get("required_scopes", []),
            input_schema=action_meta.get("input_schema", {"type": "object", "properties": {}})
        )
        self.raw_name = action_meta["id"].replace("linear.", "")

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        token = _extract_token(credential)
        inputs = dict(input_data or {})
        headers = _linear_headers(token)
        assert_public_url(LINEAR_GRAPHQL_URL)

        # Support direct run_query and run_mutation
        if self.raw_name in ["run_query", "run_mutation"]:
            query_str = inputs.get("query") or inputs.get("mutation")
            if not query_str:
                raise ValueError(f"Linear {self.raw_name} requires a 'query' or 'mutation' string parameter.")
            variables = inputs.get("variables", {})
            graphql_payload = {"query": query_str, "variables": variables}
        elif self.raw_name in LINEAR_QUERY_TEMPLATES:
            query_str = LINEAR_QUERY_TEMPLATES[self.raw_name]
            # Match variables
            variables = {}
            if "$input:" in query_str:
                variables["input"] = inputs
            else:
                for k in ["id", "term", "first"]:
                    if k in inputs:
                        variables[k] = inputs[k]
                if "issue_id" in inputs and "id" not in variables:
                    variables["id"] = inputs["issue_id"]
                if "project_id" in inputs and "id" not in variables:
                    variables["id"] = inputs["project_id"]
            graphql_payload = {"query": query_str, "variables": variables}
        else:
            # Fallback GraphQL generic executor
            query_str = inputs.get("query")
            if query_str:
                graphql_payload = {"query": query_str, "variables": inputs.get("variables", {})}
            else:
                # Run introspection or generic wrapper
                graphql_payload = {
                    "query": "query ViewerInfo { viewer { id name email } }",
                    "variables": {}
                }

        resp = await execute_guarded_request(
            client=client,
            method="POST",
            url=LINEAR_GRAPHQL_URL,
            headers=headers,
            json_body=graphql_payload
        )

        try:
            data = resp.json()
        except Exception:
            data = resp.text

        if resp.status_code >= 400:
            msg = data.get("errors") if isinstance(data, dict) else str(data)
            raise ValueError(f"Linear GraphQL error ({resp.status_code}): {msg}")

        if isinstance(data, dict) and data.get("errors"):
            errors = data.get("errors", [])
            err_msg = "; ".join(e.get("message", "Unknown error") for e in errors)
            raise ValueError(f"Linear GraphQL error: {err_msg}")

        return {"status": resp.status_code, "data": data.get("data", data)}

class LinearProvider(Provider):
    def __init__(self):
        super().__init__(
            service="linear",
            display_name="Linear",
            category="Project Management",
            auth_types=["api_key", "oauth2"],
            description="Purpose-built project management tool for modern software teams and issue tracking.",
            homepage_url="https://linear.app",
            base_url=LINEAR_GRAPHQL_URL,
            auth_configs=[
                {
                    "type": "api_key",
                    "label": "Linear Personal API Key",
                    "placeholder": "lin_api_...",
                    "description": "Personal API key generated from your Linear account settings.",
                    "docs_url": "https://linear.app/docs/api-and-webhooks",
                    "docs_label": "Linear API Docs",
                    "setup_guide": {
                        "title": "Linear API Key Setup Guide",
                        "docs_url": "https://linear.app/settings/account/security",
                        "docs_label": "Linear Security & Access Settings",
                        "instructions": [
                            "1. Open Linear (linear.app) and navigate to Settings > Account > Security & Access.",
                            "2. Under 'Personal API keys', click 'Create new key'.",
                            "3. Give your key a name (e.g., 'ConnectorHub') and copy the generated key.",
                            "4. Paste your key below (starts with 'lin_api_')."
                        ],
                        "scopes": ["read", "write", "issues:create", "comments:create"]
                    },
                    "fields": [
                        {
                            "key": "apiKey",
                            "label": "Personal API Key",
                            "type": "password",
                            "required": True,
                            "placeholder": "lin_api_...",
                            "description": "Linear personal access token."
                        }
                    ]
                },
                {
                    "type": "oauth2",
                    "label": "Linear OAuth 2.0",
                    "placeholder": "lin_oauth_...",
                    "description": "Connect via Linear OAuth 2.0 application authorization flow.",
                    "docs_url": "https://developers.linear.app/docs/oauth/authentication",
                    "docs_label": "Linear OAuth Guide",
                    "setup_guide": {
                        "title": "Linear OAuth Application Setup",
                        "docs_url": "https://linear.app/settings/api/applications/new",
                        "docs_label": "Linear Application Portal",
                        "instructions": [
                            "1. In Linear, go to Settings > Workspace > API > Applications > Create Application.",
                            "2. Set your application name and configure the OAuth Redirect URL.",
                            "3. Copy Client ID and Client Secret into ConnectorHub settings.",
                            "4. Complete the authorization flow."
                        ],
                        "scopes": ["read", "write", "issues:create", "comments:create"]
                    },
                    "fields": [
                        {
                            "key": "accessToken",
                            "label": "OAuth Access Token",
                            "type": "password",
                            "required": True,
                            "placeholder": "lin_...",
                            "description": "Linear OAuth access token."
                        }
                    ]
                }
            ]
        )

        for meta in get_provider_actions("linear"):
            self.register_action(LinearDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Linear credentials via GraphQL viewer query."""
        token = _extract_token(credential)
        headers = _linear_headers(token)
        assert_public_url(LINEAR_GRAPHQL_URL)

        payload = {
            "query": "query { viewer { id name email displayName avatarUrl } }"
        }

        try:
            resp = await execute_guarded_request(
                client=client,
                method="POST",
                url=LINEAR_GRAPHQL_URL,
                headers=headers,
                json_body=payload
            )
        except Exception as e:
            raise ValueError(f"Unable to reach Linear API: {str(e)}")

        if resp.status_code == 401 or resp.status_code == 403:
            raise ValueError("Invalid Linear credentials. Linear returned unauthorized.")
        elif resp.status_code != 200:
            raise ValueError(f"Linear credential validation failed with status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        if "errors" in data:
            err_msg = data["errors"][0].get("message", "Unknown GraphQL error")
            raise ValueError(f"Linear validation failed: {err_msg}")

        viewer = (data.get("data") or {}).get("viewer") or {}
        account_id = viewer.get("id") or "linear-viewer"
        name = viewer.get("name") or viewer.get("displayName") or viewer.get("email") or "Linear User"
        email = viewer.get("email")

        display_name = f"Linear ({name})" if name else "Linear"
        avatar_url = viewer.get("avatarUrl")

        return {
            "account_id": account_id,
            "display_name": display_name,
            "granted_scopes": ["read", "write", "issues:create", "comments:create"],
            "avatar_url": avatar_url
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
        """SSRF-guarded proxy forwarder for Linear GraphQL API."""
        token = _extract_token(credential)
        assert_public_url(LINEAR_GRAPHQL_URL)

        req_headers = dict(headers or {})
        req_headers.update(_linear_headers(token))

        resp = await execute_guarded_request(
            client=client,
            method="POST",
            url=LINEAR_GRAPHQL_URL,
            headers=req_headers,
            json_body=body if body else {"query": "query { viewer { id name } }"}
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
