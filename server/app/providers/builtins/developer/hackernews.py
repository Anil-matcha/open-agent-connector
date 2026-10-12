"""
Hacker News Provider for ConnectorHub.
Loads and registers all 14 actions from 'actions_catalog.json'.
Public developer news and community discussions from Y Combinator via Firebase & Algolia APIs.
Zero credentials required (no_auth).
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import urllib.parse
import httpx

from app.providers.base import Provider, Action
from app.providers.catalog import get_provider_actions
from app.core.ssrf import assert_public_url, execute_guarded_request

FIREBASE_BASE_URL = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_BASE_URL = "https://hn.algolia.com/api/v1"
MAX_TRUNCATED_TEXT_LENGTH = 500

def _truncate_text(text: Optional[str], truncate: bool) -> Optional[str]:
    if not text or not truncate or len(text) <= MAX_TRUNCATED_TEXT_LENGTH:
        return text
    return text[:MAX_TRUNCATED_TEXT_LENGTH]

class HackerNewsDynamicAction(Action):
    def __init__(self, action_meta: Dict[str, Any]):
        super().__init__(
            id=action_meta["id"],
            name=action_meta["name"],
            description=action_meta["description"],
            category=action_meta.get("category", "Social"),
            required_scopes=action_meta.get("required_scopes") or action_meta.get("requiredScopes", []),
            input_schema=action_meta.get("input_schema") or action_meta.get("inputSchema", {"type": "object", "properties": {}}),
            output_schema=action_meta.get("output_schema") or action_meta.get("outputSchema", {"type": "object"})
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        inputs = dict(input_data or {})
        aid = self.id

        # 1. Story Feed ID Lists
        if aid == "hackernews.get_ask_stories":
            url = f"{FIREBASE_BASE_URL}/askstories.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            ids = resp.json() or []
            if "limit" in inputs:
                ids = ids[:int(inputs["limit"])]
            return {"story_ids": ids}

        elif aid == "hackernews.get_best_stories":
            url = f"{FIREBASE_BASE_URL}/beststories.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            ids = resp.json() or []
            if "limit" in inputs:
                ids = ids[:int(inputs["limit"])]
            return {"story_ids": ids, "count": len(ids)}

        elif aid == "hackernews.get_job_stories":
            url = f"{FIREBASE_BASE_URL}/jobstories.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            ids = resp.json() or []
            if "limit" in inputs:
                ids = ids[:int(inputs["limit"])]
            return {"story_ids": ids}

        elif aid == "hackernews.get_new_stories":
            url = f"{FIREBASE_BASE_URL}/newstories.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            ids = resp.json() or []
            if "limit" in inputs:
                ids = ids[:int(inputs["limit"])]
            return {"story_ids": ids, "count": len(ids)}

        elif aid == "hackernews.get_show_stories":
            url = f"{FIREBASE_BASE_URL}/showstories.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            ids = resp.json() or []
            if "limit" in inputs:
                ids = ids[:int(inputs["limit"])]
            return {"story_ids": ids}

        elif aid == "hackernews.get_top_stories":
            url = f"{FIREBASE_BASE_URL}/topstories.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            ids = resp.json() or []
            if "limit" in inputs:
                ids = ids[:int(inputs["limit"])]
            return {"story_ids": ids, "count": len(ids)}

        # 2. System status & Updates
        elif aid == "hackernews.get_max_item_id":
            url = f"{FIREBASE_BASE_URL}/maxitem.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            return {"max_item_id": resp.json()}

        elif aid == "hackernews.get_updates":
            url = f"{FIREBASE_BASE_URL}/updates.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            return resp.json() or {"items": [], "profiles": []}

        # 3. Item retrieval
        elif aid == "hackernews.get_item":
            raw_id = inputs.get("id") or inputs.get("item_id")
            if not raw_id:
                raise ValueError("Item ID ('id' or 'item_id') is required.")
            item_id = int(raw_id)
            url = f"{FIREBASE_BASE_URL}/item/{item_id}.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            return resp.json() or {}

        elif aid == "hackernews.get_item_with_id":
            raw_id = inputs.get("item_id") or inputs.get("id")
            if not raw_id:
                raise ValueError("Item ID ('item_id') is required.")
            item_id = int(raw_id)
            max_depth = int(inputs.get("max_depth", 2))
            max_children = int(inputs.get("max_children", 10))
            truncate_text = bool(inputs.get("truncate_text", True))

            root_url = f"{FIREBASE_BASE_URL}/item/{item_id}.json"
            assert_public_url(root_url)
            resp = await execute_guarded_request(client=client, method="GET", url=root_url)
            resp.raise_for_status()
            root_item = resp.json()
            if not root_item:
                return {
                    "found": False,
                    "error_message": f"item not found: {item_id}"
                }

            async def _fetch_firebase_item(iid: int) -> Optional[Dict[str, Any]]:
                i_url = f"{FIREBASE_BASE_URL}/item/{iid}.json"
                try:
                    assert_public_url(i_url)
                    r = await execute_guarded_request(client=client, method="GET", url=i_url)
                    if r.status_code == 200:
                        return r.json()
                except Exception:
                    pass
                return None

            async def _resolve_story_id(item: Dict[str, Any]) -> Optional[int]:
                itype = item.get("type")
                if itype in ("story", "poll"):
                    return item.get("id")
                if itype != "comment" or not isinstance(item.get("parent"), int):
                    return None
                curr_parent = item.get("parent")
                for _ in range(32):
                    parent = await _fetch_firebase_item(curr_parent)
                    if not parent:
                        return None
                    if parent.get("type") in ("story", "poll"):
                        return parent.get("id")
                    if parent.get("type") != "comment" or not isinstance(parent.get("parent"), int):
                        return None
                    curr_parent = parent.get("parent")
                return None

            story_id = await _resolve_story_id(root_item)

            async def _build_tree(item: Dict[str, Any], depth: int) -> Dict[str, Any]:
                child_ids = [cid for cid in item.get("kids", []) if isinstance(cid, int)]
                t_val = item.get("time")
                created_at_iso = datetime.fromtimestamp(t_val, tz=timezone.utc).isoformat() if isinstance(t_val, (int, float)) else None

                base_tree = {
                    "id": item.get("id"),
                    "type": item.get("type"),
                    "url": item.get("url"),
                    "text": _truncate_text(item.get("text"), truncate_text),
                    "title": item.get("title"),
                    "author": item.get("by"),
                    "points": item.get("score"),
                    "options": item.get("parts"),
                    "story_id": story_id or (item.get("id") if item.get("type") in ("story", "poll") else None),
                    "parent_id": item.get("parent"),
                    "created_at": created_at_iso,
                    "created_at_i": t_val
                }

                if not child_ids:
                    return base_tree

                if depth <= 0:
                    base_tree.update({
                        "children": [],
                        "children_shown": 0,
                        "max_depth_reached": True,
                        "children_truncated": False,
                        "total_children_count": len(child_ids)
                    })
                    return base_tree

                limited_ids = child_ids[:max_children]
                child_items_raw = await asyncio.gather(*[_fetch_firebase_item(cid) for cid in limited_ids])
                child_trees = await asyncio.gather(*[
                    _build_tree(c, depth - 1) for c in child_items_raw if c
                ])

                base_tree.update({
                    "children": list(child_trees),
                    "children_shown": len(child_trees),
                    "max_depth_reached": False,
                    "children_truncated": len(child_ids) > len(limited_ids),
                    "total_children_count": len(child_ids)
                })
                return base_tree

            tree_result = await _build_tree(root_item, max_depth)
            return {
                "found": True,
                "item": tree_result
            }

        # 4. User Profiles
        elif aid == "hackernews.get_user":
            username = str(inputs.get("username", "")).strip()
            if not username:
                raise ValueError("username is required.")
            url = f"{FIREBASE_BASE_URL}/user/{urllib.parse.quote(username, safe='')}.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            user = resp.json()
            if not user:
                return {}
            return {
                "username": user.get("id"),
                "karma": user.get("karma"),
                "about": user.get("about")
            }

        elif aid == "hackernews.get_user_by_username":
            username = str(inputs.get("username", "")).strip()
            if not username:
                raise ValueError("username is required.")
            url = f"{FIREBASE_BASE_URL}/user/{urllib.parse.quote(username, safe='')}.json"
            assert_public_url(url)
            params = {"print": "pretty"} if inputs.get("print") == "pretty" else None
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            return resp.json() or {}

        # 5. Algolia Search & Latest Posts
        elif aid in ("hackernews.search_posts", "hackernews.search_stories"):
            query = inputs.get("query", "")
            page = inputs.get("page", 0)
            hits_per_page = inputs.get("size") or inputs.get("limit") or inputs.get("hitsPerPage") or 5
            tags = inputs.get("tags")
            if isinstance(tags, list):
                tags = ",".join(str(t) for t in tags if t)

            params = {
                "query": str(query),
                "page": str(page),
                "hitsPerPage": str(hits_per_page)
            }
            if tags:
                params["tags"] = str(tags)

            url = f"{ALGOLIA_BASE_URL}/search"
            assert_public_url(url)
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            data = resp.json() or {}
            # Normalize hits for compatibility
            return data

        elif aid == "hackernews.get_latest_posts":
            page = inputs.get("page", 0)
            hits_per_page = inputs.get("size") or inputs.get("limit") or inputs.get("hitsPerPage") or 5
            tags = inputs.get("tags")
            if isinstance(tags, list):
                tags = ",".join(str(t) for t in tags if t)

            params = {
                "page": str(page),
                "hitsPerPage": str(hits_per_page)
            }
            if tags:
                params["tags"] = str(tags)

            url = f"{ALGOLIA_BASE_URL}/search_by_date"
            assert_public_url(url)
            resp = await execute_guarded_request(client=client, method="GET", url=url, params=params)
            resp.raise_for_status()
            return resp.json() or {}

        else:
            raise NotImplementedError(f"Action '{aid}' is not implemented by HackerNewsProvider.")

class HackerNewsProvider(Provider):
    def __init__(self):
        super().__init__(
            service="hackernews",
            display_name="Hacker News",
            category="Social",
            auth_types=["no_auth"],
            description="Public developer news, stories, and community discussions from Y Combinator.",
            homepage_url="https://news.ycombinator.com",
            base_url=FIREBASE_BASE_URL,
            auth_configs=[
                {
                    "type": "no_auth",
                    "label": "Public Access (No Authentication)",
                    "description": "Public Hacker News Firebase and Algolia search APIs. No credentials required.",
                    "docs_url": "https://github.com/HackerNews/API",
                    "docs_label": "Hacker News API Documentation",
                    "setup_guide": {
                        "title": "Hacker News Public API",
                        "docs_url": "https://github.com/HackerNews/API",
                        "docs_label": "Hacker News GitHub",
                        "instructions": [
                            "1. Hacker News requires no credentials or API keys.",
                            "2. Direct access to all Firebase endpoints (top, new, best, ask, show, job stories, items, users).",
                            "3. Direct access to Algolia full-text search and latest posts.",
                            "4. Click 'Connect' to enable Hacker News tools in your agent runtime."
                        ],
                        "scopes": []
                    }
                }
            ]
        )

        for meta in get_provider_actions("hackernews"):
            self.register_action(HackerNewsDynamicAction(meta))

    async def validate_credentials(self, credential: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Validate Hacker News connectivity by checking GET /maxitem.json."""
        url = f"{FIREBASE_BASE_URL}/maxitem.json"
        assert_public_url(url)

        try:
            resp = await execute_guarded_request(client=client, method="GET", url=url)
        except Exception as e:
            raise ValueError(f"Unable to reach Hacker News API: {str(e)}")

        if resp.status_code != 200:
            raise ValueError(f"Hacker News connectivity check failed with status {resp.status_code}")

        max_id = resp.json()
        return {
            "valid": True,
            "accountId": "hackernews_public",
            "displayName": "Hacker News (Public)",
            "metadata": {
                "validationEndpoint": "/maxitem.json",
                "maxItemId": max_id,
                "status": "connected"
            }
        }
