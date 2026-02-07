#!/usr/bin/env python3
"""
Podcast Transcriber - Extract audio from Overcast links and transcribe with Whisper

Usage: python podcast_transcriber.py <overcast_url>
Example: python podcast_transcriber.py https://overcast.fm/+AAbggn-BZtw

Requirements (install with uv):
    uv add requests mlx-whisper

The transcript will be saved as a .txt file in the current directory.
"""

import re
import sys
import tempfile
from pathlib import Path

import requests


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
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text


def extract_audio_url(html: str) -> str | None:
    """Extract the audio source URL from the page HTML."""
    patterns = [
        r'<source\s+src="([^"]+)"',
        r'<audio[^>]+src="([^"]+)"',
        r'"audio_url"\s*:\s*"([^"]+)"',
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
            # Remove " — Overcast" suffix if present
            title = re.sub(r"\s*—\s*Overcast$", "", title)
            return title
    return None


def sanitize_filename(title: str) -> str:
    """Convert title to a safe filename."""
    # Remove or replace characters that aren't safe for filenames
    safe = re.sub(r'[<>:"/\\|?*]', "", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    # Truncate if too long
    if len(safe) > 100:
        safe = safe[:100].rsplit(" ", 1)[0]
    return safe


def download_audio(url: str, output_path: Path) -> None:
    """Download the audio file with progress indication."""
    print(f"Downloading audio...")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                pct = (downloaded / total_size) * 100
                print(f"\r  {downloaded / 1_000_000:.1f} MB / {total_size / 1_000_000:.1f} MB ({pct:.0f}%)", end="")
    
    print(f"\n  Saved to: {output_path}")


def transcribe_audio(audio_path: Path, output_path: Path) -> str:
    """Transcribe audio using MLX Whisper."""
    print(f"Transcribing with MLX Whisper (this may take a few minutes)...")
    
    import mlx_whisper
    
    # Use the large-v3-turbo model for good balance of speed and accuracy
    # Other options: "mlx-community/whisper-tiny-mlx" (fastest, less accurate)
    #                "mlx-community/whisper-large-v3-mlx" (most accurate, slower)
    result = mlx_whisper.transcribe(
        str(audio_path),
#         path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
        path_or_hf_repo="mlx-community/whisper-large-v3-mlx",
#         condition_on_previous_text=False,
        verbose=True,
    )
    
    transcript = result["text"]
    
    # Save transcript
    output_path.write_text(transcript)
    print(f"  Transcript saved to: {output_path}")
    
    return transcript


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <overcast_url>")
        print(f"Example: {sys.argv[0]} https://overcast.fm/+AAbggn-BZtw")
        sys.exit(1)
    
    overcast_url = sys.argv[1]
    
    # Step 1: Fetch and parse the Overcast page
    print(f"Fetching: {overcast_url}")
    html = fetch_page(overcast_url)
    
    title = extract_title(html)
    audio_url = extract_audio_url(html)
    
    if not audio_url:
        print("❌ Could not find audio URL")
        sys.exit(1)
    
    print(f"Title: {title or 'Unknown'}")
    print(f"Audio URL: {audio_url}")
    
    # Step 2: Download the audio
    safe_title = sanitize_filename(title) if title else "podcast"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "episode.mp3"
        download_audio(audio_url, audio_path)
        
        # Step 3: Transcribe
        output_path = Path.cwd() / f"{safe_title}.txt"
        transcript = transcribe_audio(audio_path, output_path)
    
    print(f"\n✅ Done! Transcript saved to: {output_path}")
    
    # Print first 500 chars as preview
    print(f"\n--- Preview ---\n{transcript[:500]}...")


if __name__ == "__main__":
    main()
