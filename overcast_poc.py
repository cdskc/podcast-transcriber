#!/usr/bin/env python3
"""
Proof of concept: Extract MP3 URL from Overcast share links

Usage: python overcast_poc.py <overcast_url>
Example: python overcast_poc.py https://overcast.fm/+AAbggn-BZtw

Requirements: pip install requests (or use uv)
"""

import re
import sys

try:
    import requests
    USE_REQUESTS = True
except ImportError:
    from urllib.request import Request, urlopen
    USE_REQUESTS = False


def fetch_page(url: str) -> str:
    """Fetch the Overcast page with browser-like headers."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    if USE_REQUESTS:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    else:
        req = Request(url, headers=headers)
        with urlopen(req) as response:
            return response.read().decode("utf-8")


def extract_audio_url(html: str) -> str | None:
    """Extract the audio source URL from the page HTML."""
    # Look for <source src="..."> or <audio src="...">
    patterns = [
        r'<source\s+src="([^"]+)"',
        r'<audio[^>]+src="([^"]+)"',
        r'"audio_url"\s*:\s*"([^"]+)"',  # JSON format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            url = match.group(1)
            # Strip any timestamp fragment (e.g., #t=0)
            if "#" in url:
                url = url.split("#")[0]
            return url
    return None


def extract_title(html: str) -> str | None:
    """Extract episode title from meta tags."""
    patterns = [
        r'<meta\s+name="og:title"\s+content="([^"]+)"',
        r'<meta\s+property="og:title"\s+content="([^"]+)"',
        r"<title>([^<]+)</title>",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            title = match.group(1)
            # Clean up HTML entities
            title = title.replace("&mdash;", "—")
            title = title.replace("&amp;", "&")
            title = title.replace("&#39;", "'")
            return title
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <overcast_url>")
        print(f"Example: {sys.argv[0]} https://overcast.fm/+AAbggn-BZtw")
        sys.exit(1)
    
    overcast_url = sys.argv[1]
    
    print(f"Fetching: {overcast_url}")
    html = fetch_page(overcast_url)
    
    title = extract_title(html)
    audio_url = extract_audio_url(html)
    
    print(f"\nTitle: {title or 'Not found'}")
    print(f"Audio URL: {audio_url or 'Not found'}")
    
    if audio_url:
        print("\n✅ Success! You can download with:")
        print(f"   curl -L -o episode.mp3 '{audio_url}'")
    else:
        print("\n❌ Could not find audio URL")
        print("The page might load audio dynamically via JavaScript.")
        # Debug: show a snippet of the HTML
        print("\nHTML snippet (first 2000 chars):")
        print(html[:2000])


if __name__ == "__main__":
    main()
