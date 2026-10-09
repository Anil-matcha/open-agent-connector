from typing import Dict, Any, Optional
import httpx
from app.providers.base import Provider, Action
from app.core.ssrf import assert_public_url

class GetTopStoriesAction(Action):
    def __init__(self):
        super().__init__(
            id="hackernews.get_top_stories",
            name="Get Top Stories",
            description="Fetch IDs of the top stories currently on Hacker News.",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of story IDs to return", "default": 20}
                }
            }
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        limit = int(input_data.get("limit", 20))
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        assert_public_url(url)
        resp = await client.get(url)
        resp.raise_for_status()
        ids = resp.json()[:limit]
        return {"story_ids": ids, "count": len(ids)}

class GetItemAction(Action):
    def __init__(self):
        super().__init__(
            id="hackernews.get_item",
            name="Get Item",
            description="Fetch full details of a Hacker News item (story, comment, job, poll) by ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer", "description": "Hacker News item ID"}
                },
                "required": ["item_id"]
            }
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        item_id = input_data.get("item_id")
        if not item_id:
            raise ValueError("item_id is required")
        url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        assert_public_url(url)
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json() or {}

class SearchStoriesAction(Action):
    def __init__(self):
        super().__init__(
            id="hackernews.search_stories",
            name="Search Stories",
            description="Search Hacker News stories using the Algolia search index.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keywords"},
                    "limit": {"type": "integer", "description": "Number of results to return", "default": 10}
                },
                "required": ["query"]
            }
        )

    async def execute(self, input_data: Dict[str, Any], credential: Optional[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        query = input_data.get("query", "")
        limit = int(input_data.get("limit", 10))
        url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage={limit}"
        assert_public_url(url)
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        hits = [
            {
                "id": hit.get("objectID"),
                "title": hit.get("title"),
                "url": hit.get("url"),
                "author": hit.get("author"),
                "points": hit.get("points"),
                "comments_count": hit.get("num_comments"),
                "created_at": hit.get("created_at")
            }
            for hit in data.get("hits", [])
        ]
        return {"hits": hits, "nbHits": data.get("nbHits", len(hits))}

class HackerNewsProvider(Provider):
    def __init__(self):
        super().__init__(
            service="hackernews",
            display_name="Hacker News",
            category="Social & Media",
            auth_types=["no_auth"],
            description="Public developer news and community discussions from Y Combinator.",
            homepage_url="https://news.ycombinator.com",
            base_url="https://hacker-news.firebaseio.com/v0",
            auth_configs=[
                {
                    "type": "no_auth",
                    "label": "Public Access (No Authentication)",
                    "description": "Public Hacker News Firebase & Algolia APIs. No credentials required.",
                    "docs_url": "https://github.com/HackerNews/API",
                    "docs_label": "Hacker News API Docs"
                }
            ]
        )
        self.register_action(GetTopStoriesAction())
        self.register_action(GetItemAction())
        self.register_action(SearchStoriesAction())
