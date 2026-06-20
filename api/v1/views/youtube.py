import json
import urllib.parse
import urllib.request

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from core.rate_limit import youtube_search_limit


class YouTubeSearchView(APIView):
    @youtube_search_limit
    def get(self, request):
        query = request.GET.get("q", "").strip()[:100]
        if len(query) < 3:
            return Response({"results": []})

        api_key = getattr(settings, "YOUTUBE_API_KEY", "")
        if not api_key:
            return Response({"error": "YouTube API key not configured"}, status=503)

        params = urllib.parse.urlencode({
            "part": "snippet",
            "type": "video",
            "maxResults": 5,
            "q": query,
            "key": api_key,
        })
        url = f"https://www.googleapis.com/youtube/v3/search?{params}"

        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
        except Exception:
            return Response({"error": "Search failed"}, status=502)

        results = [
            {
                "id": item["id"].get("videoId"),
                "title": item["snippet"].get("title", ""),
                "channel": item["snippet"].get("channelTitle", ""),
                "thumbnail": item["snippet"].get("thumbnails", {}).get("default", {}).get("url", ""),
            }
            for item in data.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

        return Response({"results": results})
