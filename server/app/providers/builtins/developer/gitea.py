"""
Gitea Provider for ConnectorHub.
Loads and registers 93 actions with exact route definitions and parameters.
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

DEFAULT_API_BASE = "{instanceUrl}/api/v1"

def _extract_token(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    for k in ["apiKey", "accessToken", "token", "key", "api_key", "access_token", "apiToken", "serverToken", "restToken", "writeKey"]:
        if cred.get(k):
            return str(cred[k]).strip()
    return ""

def _resolve_base_url(credential: Optional[Dict[str, Any]]) -> str:
    cred = credential or {}
    base = DEFAULT_API_BASE
    for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
        if "{" + key + "}" in base:
            val = str(cred.get(key) or "default").strip()
            base = base.replace("{" + key + "}", val)
    if base.startswith("{instanceUrl}"):
        inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
        base = base.replace("{instanceUrl}", inst)
    return base

def _build_headers(credential: Optional[Dict[str, Any]]) -> Dict[str, str]:
    cred = credential or {}
    token = _extract_token(cred)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ConnectorHub/1.0"
    }

    auth_mode = "gitea_token"
    if auth_mode == "Bearer":
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_mode == "gitea_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "zerotier_token":
        if token:
            headers["Authorization"] = f"token {token}"
    elif auth_mode == "n8n_header":
        if token:
            headers["X-N8N-API-KEY"] = token
    elif auth_mode == "readme_basic":
        if token:
            pair = f"{token}:"
            headers["Authorization"] = f"Basic {base64.b64encode(pair.encode()).decode()}"
    elif auth_mode == "mingdao_auth":
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if cred.get("appKey"):
            headers["X-App-Key"] = str(cred["appKey"])
        if cred.get("sign"):
            headers["X-Sign"] = str(cred["sign"])

    return headers

ROUTES: Dict[str, List[Any]] = {
    "add_collaborator": [
        "POST",
        "/collaborator",
        [],
        [
            "owner",
            "repo",
            "collaborator",
            "permission"
        ]
    ],
    "add_issue_labels": [
        "POST",
        "/issue_labels",
        [],
        [
            "owner",
            "repo",
            "issueNumber",
            "labels"
        ]
    ],
    "check_pull_request_merged": [
        "GET",
        "/check_pull_request_merged",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber"
        ]
    ],
    "clear_issue_labels": [
        "GET",
        "/clear_issue_labels",
        [],
        [
            "owner",
            "repo",
            "issueNumber"
        ]
    ],
    "create_branch": [
        "POST",
        "/branch",
        [],
        [
            "owner",
            "repo",
            "newBranchName",
            "oldRefName"
        ]
    ],
    "create_commit_status": [
        "POST",
        "/commit_status",
        [],
        [
            "owner",
            "repo",
            "sha",
            "state",
            "context",
            "description",
            "targetUrl"
        ]
    ],
    "create_file": [
        "POST",
        "/file",
        [],
        [
            "owner",
            "repo",
            "filePath",
            "content",
            "message",
            "branch",
            "newBranch",
            "authorName",
            "authorEmail",
            "committerName",
            "committerEmail",
            "signoff",
            "forcePush"
        ]
    ],
    "create_issue": [
        "POST",
        "/issue",
        [],
        [
            "owner",
            "repo",
            "title",
            "body",
            "assignees",
            "labelIds",
            "milestoneId",
            "ref",
            "dueDate",
            "closed"
        ]
    ],
    "create_issue_comment": [
        "POST",
        "/issue_comment",
        [],
        [
            "owner",
            "repo",
            "issueNumber",
            "body"
        ]
    ],
    "create_label": [
        "POST",
        "/label",
        [],
        [
            "owner",
            "repo",
            "name",
            "color",
            "description",
            "exclusive",
            "isArchived"
        ]
    ],
    "create_milestone": [
        "POST",
        "/milestone",
        [],
        [
            "owner",
            "repo",
            "title",
            "description",
            "state",
            "dueOn"
        ]
    ],
    "create_pull_request": [
        "POST",
        "/pull_request",
        [],
        [
            "owner",
            "repo",
            "title",
            "body",
            "base",
            "head",
            "assignees",
            "labelIds",
            "milestoneId",
            "reviewers",
            "teamReviewers",
            "allowMaintainerEdit",
            "dueDate"
        ]
    ],
    "create_pull_request_review": [
        "POST",
        "/pull_request_review",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "body",
            "event",
            "commitId"
        ]
    ],
    "create_release": [
        "POST",
        "/release",
        [],
        [
            "owner",
            "repo",
            "tagName",
            "name",
            "body",
            "targetCommitish",
            "draft",
            "prerelease",
            "tagMessage"
        ]
    ],
    "create_repository": [
        "POST",
        "/repository",
        [],
        [
            "name",
            "description",
            "private",
            "autoInit",
            "defaultBranch",
            "gitignores",
            "license",
            "readme",
            "issueLabels",
            "template",
            "objectFormatName",
            "trustModel"
        ]
    ],
    "create_repository_hook": [
        "POST",
        "/repository_hook",
        [],
        [
            "owner",
            "repo",
            "type",
            "config",
            "events",
            "active",
            "branchFilter",
            "authorizationHeader"
        ]
    ],
    "create_repository_key": [
        "POST",
        "/repository_key",
        [],
        [
            "owner",
            "repo",
            "title",
            "key",
            "readOnly"
        ]
    ],
    "create_tag": [
        "POST",
        "/tag",
        [],
        [
            "owner",
            "repo",
            "tagName",
            "target",
            "message"
        ]
    ],
    "delete_branch": [
        "DELETE",
        "/branch",
        [],
        [
            "owner",
            "repo",
            "branch"
        ]
    ],
    "delete_file": [
        "DELETE",
        "/file",
        [],
        [
            "owner",
            "repo",
            "filePath",
            "sha",
            "message",
            "branch",
            "newBranch",
            "authorName",
            "authorEmail",
            "committerName",
            "committerEmail",
            "signoff"
        ]
    ],
    "delete_issue_comment": [
        "DELETE",
        "/issue_comment",
        [],
        [
            "owner",
            "repo",
            "commentId"
        ]
    ],
    "delete_label": [
        "DELETE",
        "/label",
        [],
        [
            "owner",
            "repo",
            "labelId"
        ]
    ],
    "delete_milestone": [
        "DELETE",
        "/milestone",
        [],
        [
            "owner",
            "repo",
            "milestoneId"
        ]
    ],
    "delete_pull_request_review": [
        "DELETE",
        "/pull_request_review",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "reviewId"
        ]
    ],
    "delete_release": [
        "DELETE",
        "/release",
        [],
        [
            "owner",
            "repo",
            "releaseId"
        ]
    ],
    "delete_repository": [
        "DELETE",
        "/repository",
        [],
        [
            "owner",
            "repo"
        ]
    ],
    "delete_repository_hook": [
        "DELETE",
        "/repository_hook",
        [],
        [
            "owner",
            "repo",
            "hookId"
        ]
    ],
    "delete_repository_key": [
        "DELETE",
        "/repository_key",
        [],
        [
            "owner",
            "repo",
            "keyId"
        ]
    ],
    "delete_tag": [
        "DELETE",
        "/tag",
        [],
        [
            "owner",
            "repo",
            "tag"
        ]
    ],
    "dismiss_pull_request_review": [
        "GET",
        "/dismiss_pull_request_review",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "reviewId",
            "message",
            "priors"
        ]
    ],
    "fork_repository": [
        "GET",
        "/fork_repository",
        [],
        [
            "owner",
            "repo",
            "name",
            "organization"
        ]
    ],
    "get_branch": [
        "GET",
        "/branch",
        [],
        [
            "owner",
            "repo",
            "branch"
        ]
    ],
    "get_collaborator_permission": [
        "GET",
        "/collaborator_permission",
        [],
        [
            "owner",
            "repo",
            "collaborator"
        ]
    ],
    "get_commit": [
        "GET",
        "/commit",
        [],
        [
            "owner",
            "repo",
            "sha"
        ]
    ],
    "get_current_user": [
        "GET",
        "/current_user",
        [],
        []
    ],
    "get_issue": [
        "GET",
        "/issue",
        [],
        [
            "owner",
            "repo",
            "issueNumber"
        ]
    ],
    "get_label": [
        "GET",
        "/label",
        [],
        [
            "owner",
            "repo",
            "labelId"
        ]
    ],
    "get_milestone": [
        "GET",
        "/milestone",
        [],
        [
            "owner",
            "repo",
            "milestoneId"
        ]
    ],
    "get_organization": [
        "GET",
        "/organization",
        [],
        [
            "org"
        ]
    ],
    "get_pull_request": [
        "GET",
        "/pull_request",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber"
        ]
    ],
    "get_release": [
        "GET",
        "/release",
        [],
        [
            "owner",
            "repo",
            "releaseId"
        ]
    ],
    "get_repository": [
        "GET",
        "/repository",
        [],
        [
            "owner",
            "repo"
        ]
    ],
    "get_repository_contents": [
        "GET",
        "/repository_contents",
        [],
        [
            "owner",
            "repo",
            "filePath",
            "ref"
        ]
    ],
    "get_repository_hook": [
        "GET",
        "/repository_hook",
        [],
        [
            "owner",
            "repo",
            "hookId"
        ]
    ],
    "get_repository_key": [
        "GET",
        "/repository_key",
        [],
        [
            "owner",
            "repo",
            "keyId"
        ]
    ],
    "get_tag": [
        "GET",
        "/tag",
        [],
        [
            "owner",
            "repo",
            "tag"
        ]
    ],
    "list_branches": [
        "GET",
        "/branches",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "list_collaborators": [
        "GET",
        "/collaborators",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "list_commit_statuses": [
        "GET",
        "/commit_statuses",
        [],
        [
            "owner",
            "repo",
            "ref",
            "page",
            "limit"
        ]
    ],
    "list_commits": [
        "GET",
        "/commits",
        [],
        [
            "owner",
            "repo",
            "sha",
            "path",
            "since",
            "until",
            "page",
            "limit"
        ]
    ],
    "list_issue_assignees": [
        "GET",
        "/issue_assignees",
        [],
        [
            "owner",
            "repo"
        ]
    ],
    "list_issue_comments": [
        "GET",
        "/issue_comments",
        [],
        [
            "owner",
            "repo",
            "issueNumber",
            "since",
            "before"
        ]
    ],
    "list_issue_labels": [
        "GET",
        "/issue_labels",
        [],
        [
            "owner",
            "repo",
            "issueNumber"
        ]
    ],
    "list_milestones": [
        "GET",
        "/milestones",
        [],
        [
            "owner",
            "repo",
            "state",
            "name",
            "page",
            "limit"
        ]
    ],
    "list_my_organizations": [
        "GET",
        "/my_organizations",
        [],
        [
            "page",
            "limit"
        ]
    ],
    "list_my_repositories": [
        "GET",
        "/my_repositories",
        [],
        [
            "page",
            "limit"
        ]
    ],
    "list_organization_members": [
        "GET",
        "/organization_members",
        [],
        [
            "org",
            "page",
            "limit"
        ]
    ],
    "list_organization_repositories": [
        "GET",
        "/organization_repositories",
        [],
        [
            "org",
            "page",
            "limit"
        ]
    ],
    "list_pull_request_commits": [
        "GET",
        "/pull_request_commits",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "page",
            "limit"
        ]
    ],
    "list_pull_request_files": [
        "GET",
        "/pull_request_files",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "page",
            "limit"
        ]
    ],
    "list_pull_request_review_comments": [
        "GET",
        "/pull_request_review_comments",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "reviewId"
        ]
    ],
    "list_pull_request_reviews": [
        "GET",
        "/pull_request_reviews",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "page",
            "limit"
        ]
    ],
    "list_pull_requests": [
        "GET",
        "/pull_requests",
        [],
        [
            "owner",
            "repo",
            "state",
            "baseBranch",
            "sort",
            "milestone",
            "labels",
            "poster",
            "page",
            "limit"
        ]
    ],
    "list_releases": [
        "GET",
        "/releases",
        [],
        [
            "owner",
            "repo",
            "draft",
            "prerelease",
            "page",
            "limit"
        ]
    ],
    "list_repository_hooks": [
        "GET",
        "/repository_hooks",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "list_repository_issues": [
        "GET",
        "/repository_issues",
        [],
        [
            "owner",
            "repo",
            "state",
            "labels",
            "query",
            "milestones",
            "since",
            "before",
            "createdBy",
            "assignedBy",
            "mentionedBy",
            "page",
            "limit"
        ]
    ],
    "list_repository_keys": [
        "GET",
        "/repository_keys",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "list_repository_labels": [
        "GET",
        "/repository_labels",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "list_repository_stargazers": [
        "GET",
        "/repository_stargazers",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "list_repository_topics": [
        "GET",
        "/repository_topics",
        [],
        [
            "owner",
            "repo"
        ]
    ],
    "list_repository_watchers": [
        "GET",
        "/repository_watchers",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "list_tags": [
        "GET",
        "/tags",
        [],
        [
            "owner",
            "repo",
            "page",
            "limit"
        ]
    ],
    "merge_pull_request": [
        "GET",
        "/merge_pull_request",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "do",
            "mergeTitle",
            "mergeMessage",
            "deleteBranchAfterMerge",
            "forceMerge",
            "mergeWhenChecksSucceed",
            "headCommitId"
        ]
    ],
    "remove_collaborator": [
        "DELETE",
        "/collaborator",
        [],
        [
            "owner",
            "repo",
            "collaborator"
        ]
    ],
    "remove_issue_label": [
        "DELETE",
        "/issue_label",
        [],
        [
            "owner",
            "repo",
            "issueNumber",
            "labelId"
        ]
    ],
    "remove_pull_request_reviewers": [
        "DELETE",
        "/pull_request_reviewers",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "reviewers",
            "teamReviewers"
        ]
    ],
    "replace_issue_labels": [
        "GET",
        "/replace_issue_labels",
        [],
        [
            "owner",
            "repo",
            "issueNumber",
            "labels"
        ]
    ],
    "request_pull_request_reviewers": [
        "GET",
        "/request_pull_request_reviewers",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "reviewers",
            "teamReviewers"
        ]
    ],
    "search_repositories": [
        "GET",
        "/search_repositories",
        [],
        [
            "query",
            "topic",
            "includeDescription",
            "ownerId",
            "priorityOwnerId",
            "teamId",
            "starredByUserId",
            "private",
            "template",
            "archived",
            "mode",
            "exclusive",
            "sort",
            "order",
            "page",
            "limit"
        ]
    ],
    "star_repository": [
        "GET",
        "/star_repository",
        [],
        [
            "owner",
            "repo"
        ]
    ],
    "submit_pull_request_review": [
        "GET",
        "/submit_pull_request_review",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "reviewId",
            "body",
            "event"
        ]
    ],
    "unstar_repository": [
        "GET",
        "/unstar_repository",
        [],
        [
            "owner",
            "repo"
        ]
    ],
    "update_file": [
        "PATCH",
        "/file",
        [],
        [
            "owner",
            "repo",
            "filePath",
            "content",
            "sha",
            "message",
            "branch",
            "newBranch",
            "fromPath",
            "authorName",
            "authorEmail",
            "committerName",
            "committerEmail",
            "signoff",
            "forcePush"
        ]
    ],
    "update_issue": [
        "PATCH",
        "/issue",
        [],
        [
            "owner",
            "repo",
            "issueNumber",
            "title",
            "body",
            "state",
            "assignees",
            "milestoneId",
            "ref",
            "dueDate",
            "unsetDueDate"
        ]
    ],
    "update_issue_comment": [
        "PATCH",
        "/issue_comment",
        [],
        [
            "owner",
            "repo",
            "commentId",
            "body"
        ]
    ],
    "update_label": [
        "PATCH",
        "/label",
        [],
        [
            "owner",
            "repo",
            "labelId",
            "name",
            "color",
            "description",
            "exclusive",
            "isArchived"
        ]
    ],
    "update_milestone": [
        "PATCH",
        "/milestone",
        [],
        [
            "owner",
            "repo",
            "milestoneId",
            "title",
            "description",
            "state",
            "dueOn"
        ]
    ],
    "update_pull_request": [
        "PATCH",
        "/pull_request",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "title",
            "body",
            "state",
            "base",
            "assignees",
            "labelIds",
            "milestoneId",
            "allowMaintainerEdit",
            "unsetDueDate",
            "dueDate"
        ]
    ],
    "update_pull_request_branch": [
        "PATCH",
        "/pull_request_branch",
        [],
        [
            "owner",
            "repo",
            "pullRequestNumber",
            "style"
        ]
    ],
    "update_release": [
        "PATCH",
        "/release",
        [],
        [
            "owner",
            "repo",
            "releaseId",
            "tagName",
            "name",
            "body",
            "targetCommitish",
            "draft",
            "prerelease"
        ]
    ],
    "update_repository": [
        "PATCH",
        "/repository",
        [],
        [
            "owner",
            "repo",
            "name",
            "description",
            "website",
            "private",
            "template",
            "archived",
            "defaultBranch",
            "defaultMergeStyle",
            "defaultDeleteBranchAfterMerge",
            "defaultAllowMaintainerEdit",
            "hasIssues",
            "hasPullRequests",
            "hasProjects",
            "hasWiki",
            "hasActions",
            "hasPackages",
            "hasReleases",
            "allowMergeCommits",
            "allowRebase",
            "allowRebaseExplicit",
            "allowRebaseUpdate",
            "allowSquashMerge",
            "allowFastForwardOnlyMerge",
            "allowManualMerge",
            "autodetectManualMerge",
            "ignoreWhitespaceConflicts",
            "enablePrune",
            "mirrorInterval"
        ]
    ],
    "update_repository_hook": [
        "PATCH",
        "/repository_hook",
        [],
        [
            "owner",
            "repo",
            "hookId",
            "config",
            "events",
            "active",
            "branchFilter",
            "authorizationHeader"
        ]
    ],
    "update_repository_topics": [
        "PATCH",
        "/repository_topics",
        [],
        [
            "owner",
            "repo",
            "topics"
        ]
    ]
}

class GiteaDynamicAction(Action):
    def __init__(self, action_dict: Dict[str, Any]):
        super().__init__(
            id=action_dict["id"],
            name=action_dict["name"],
            description=action_dict.get("description", ""),
            input_schema=action_dict.get("inputSchema") or action_dict.get("input_schema") or {"type": "object", "properties": {}},
            output_schema=action_dict.get("outputSchema") or action_dict.get("output_schema") or {"type": "object", "properties": {}},
            required_scopes=action_dict.get("requiredScopes") or action_dict.get("required_scopes") or []
        )
        self.raw_dict = action_dict

    async def execute(self, credential: Dict[str, Any], params: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        action_name = self.name
        route_meta = ROUTES.get(action_name, ["GET", f"/{action_name}", [], []])
        method = route_meta[0]
        path_template = route_meta[1]
        path_param_names = route_meta[2]
        body_param_names = route_meta[3]

        url_path = path_template
        for p in path_param_names:
            if p in params:
                val = str(params[p])
                url_path = url_path.replace("{" + p + "}", urllib.parse.quote(val, safe=""))

        url_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "default", url_path)

        base_url = _resolve_base_url(cred)
        if base_url.endswith("/") and url_path.startswith("/"):
            full_url = base_url + url_path[1:]
        elif not base_url.endswith("/") and not url_path.startswith("/"):
            full_url = base_url + "/" + url_path
        else:
            full_url = base_url + url_path

        assert_public_url(full_url)
        headers = _build_headers(cred)

        req_params: Dict[str, Any] = {}
        req_json: Optional[Dict[str, Any]] = None

        if method in ["GET", "DELETE"]:
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_params[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_params:
                    req_params[k] = v
        else:
            req_json = {}
            for k in body_param_names:
                if k in params and params[k] is not None:
                    req_json[k] = params[k]
            for k, v in params.items():
                if k not in path_param_names and k not in req_json:
                    req_json[k] = v

        resp = await execute_guarded_request(
            client=client,
            method=method,
            url=full_url,
            headers=headers,
            params=req_params if req_params else None,
            json=req_json if req_json else None
        )

        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if resp.status_code >= 400:
            err_msg = data.get("message") or data.get("error") or data.get("error_summary") or resp.text
            raise ValueError(f"Gitea API error ({resp.status_code}): {err_msg}")

        return {"status": resp.status_code, "data": data}


class GiteaProvider(Provider):
    def __init__(self):
        super().__init__(
            service="gitea",
            display_name="Gitea",
            category="Developer Tools",
            auth_types=["api_key"],
            description="Gitea self-hosted Git service, repositories, issues, pull requests, and releases with 93 actions."
        )
        for act in get_provider_actions("gitea"):
            self.register_action(GiteaDynamicAction(act))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        cred = credential or {}
        val_url = "{instanceUrl}/api/v1/user"
        for key in ["instanceUrl", "domain", "subdomain", "host", "tenant", "restUrl", "siteUrl", "apiUrl", "region"]:
            if "{" + key + "}" in val_url:
                val_url = val_url.replace("{" + key + "}", str(cred.get(key) or "default"))
        if val_url.startswith("{instanceUrl}"):
            inst = str(cred.get("instanceUrl") or cred.get("host") or cred.get("url") or "https://example.com").strip()
            val_url = val_url.replace("{instanceUrl}", inst)

        assert_public_url(val_url)
        headers = _build_headers(cred)

        try:
            resp = await execute_guarded_request(
                client=client,
                method="GET",
                url=val_url,
                headers=headers
            )
        except Exception as e:
            raise ValueError(f"Gitea connection error during validation: {e}")

        if resp.status_code in [401, 403]:
            raise ValueError(f"Invalid Gitea credentials: {resp.status_code} {resp.text}")
        elif resp.status_code >= 400:
            raise ValueError(f"Gitea validation failed: {resp.status_code} {resp.text}")

        token = _extract_token(cred)
        return {
            "account_id": token[:8] + "..." if token else "verified",
            "display_name": f"Gitea Account"
        }
