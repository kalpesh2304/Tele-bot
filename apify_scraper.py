from apify_client import ApifyClient
import logging

logger = logging.getLogger(__name__)

def scrape_twitter_content(handle: str, api_key: str) -> list:
    """Scrape recent tweets using Apify"""
    try:
        client = ApifyClient(api_key)
        
        run_input = {
            "handles": [handle],
            "tweetsDesired": 10,
            "language": "en",
            "maxRequestRetries": 3
        }
        
        run = client.actor("quacker/twitter-scraper").call(run_input=run_input)
        tweets = [
            item["full_text"] 
            for item in client.dataset(run["defaultDatasetId"]).iterate_items()
            if not item["isRetweet"]
        ][:5]  # Get top 5 original tweets
        
        return tweets
        
    except Exception as e:
        logger.error(f"Apify Error: {str(e)}")
        raise Exception("Failed to scrape Twitter content")