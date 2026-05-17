"""X / Twitter API — post a tweet via OAuth 1.0a (free tier write access)."""
import tweepy

from pipeline.settings import get_settings


def _client() -> tweepy.Client:
    s = get_settings()
    return tweepy.Client(
        consumer_key=s.x_api_key,
        consumer_secret=s.x_api_secret,
        access_token=s.x_access_token,
        access_token_secret=s.x_access_token_secret,
    )


async def post(text: str) -> str:
    """Post a tweet and return the tweet ID."""
    client = _client()
    # tweepy.Client.create_tweet is synchronous; run in thread to avoid blocking
    import asyncio
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: client.create_tweet(text=text)
    )
    return str(response.data["id"])
