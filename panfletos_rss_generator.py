#!/usr/bin/env python3
"""
Panfletos RSS Feed Generator
=============================
Generates an RSS/Podcast feed for the "Panfletos" program from Antena 1 (RTP).

The official RTP RSS feed stopped updating in 2021. This script scrapes the
RTP Play website to generate an up-to-date RSS feed.

Usage:
    python panfletos_rss_generator.py

    # Or with a custom output path:
    python panfletos_rss_generator.py --output /path/to/feed.xml

    # To run periodically (cron example - every 6 hours):
    # 0 */6 * * * /usr/bin/python3 /path/to/panfletos_rss_generator.py --output /var/www/feeds/panfletos.xml

Requirements:
    pip install requests beautifulsoup4
"""

import re
import sys
import argparse
from datetime import datetime

# --- Configuration ---
PROGRAM_ID = "p8339"
PROGRAM_SLUG = "panfletos"
PROGRAM_TITLE = "Panfletos"
PROGRAM_AUTHOR = "Pedro Tadeu"
PROGRAM_DESCRIPTION = (
    "As palavras-chave deste projeto são estas: música-política, canções-poder, "
    "criatividade-resistência, cultura-opressão, talento-censura, poesia-liberdade, "
    "arte-causas. Panfletos foi um programa de Ruben de Carvalho na antiga Telefonia "
    "de Lisboa. Recriado agora por Pedro Tadeu, na Antena 1, trata da relação íntima, "
    "ao longo dos tempos, da arte musical com a vida e a luta dos povos. "
    "Diariamente: uma canção na História."
)
PROGRAM_IMAGE = "https://cdn-images.rtp.pt/EPG/radio/imagens/7290_10886_10223.jpg"
PROGRAM_URL = f"https://www.rtp.pt/play/{PROGRAM_ID}/{PROGRAM_SLUG}"
PROGRAM_CATEGORY = "Music"
PROGRAM_LANGUAGE = "pt"
CHANNEL = "Antena1"

BASE_URL = "https://www.rtp.pt"
FEED_SELF_URL = "https://javiercubre.github.io/panfletos-rss/panfletos.xml"

# Month name mapping (Portuguese)
PT_MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
}


def parse_pt_date(date_str: str) -> datetime:
    """Parse Portuguese date strings like '11 fev. 2026' into datetime objects."""
    date_str = date_str.strip().replace(".", "").strip()
    parts = date_str.split()
    if len(parts) == 3:
        day = int(parts[0])
        month = PT_MONTHS.get(parts[1].lower(), 1)
        year = int(parts[2])
        return datetime(year, month, day, 12, 0, 0)
    return datetime.now()


def parse_duration(dur_str: str) -> int:
    """Parse duration string like '7min' into seconds."""
    dur_str = dur_str.strip().lower()
    match = re.search(r"(\d+)\s*min", dur_str)
    if match:
        return int(match.group(1)) * 60
    return 0


def format_rfc822(dt: datetime) -> str:
    """Format datetime as RFC 822 string for RSS."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return (f"{days[dt.weekday()]}, {dt.day:02d} {months[dt.month-1]} "
            f"{dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} +0000")


def format_itunes_duration(seconds: int) -> str:
    """Format seconds as HH:MM:SS for iTunes duration tag."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def extract_audio_url(episode_url: str) -> str | None:
    """Extract the direct audio stream URL from an RTP Play episode using yt-dlp."""
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best",
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(episode_url, download=False)
            if info and info.get("url"):
                return info["url"]
    except Exception as e:
        print(f"  yt-dlp failed for {episode_url}: {e}")
    return None


def scrape_episodes_from_html(html_content: str) -> list:
    """
    Extract episode data from the RTP Play HTML page.
    Returns a list of dicts with title, date, duration, url, episode_id.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    episodes = []

    # Find all episode links - they follow the pattern /play/p8339/eXXXXXX/panfletos
    ep_pattern = re.compile(rf"/play/{PROGRAM_ID}/e(\d+)/{PROGRAM_SLUG}")

    for link in soup.find_all("a", href=ep_pattern):
        href = link.get("href", "")
        match = ep_pattern.search(href)
        if not match:
            continue

        episode_id = match.group(1)

        # Extract title from the link text
        title_text = link.get_text(strip=True)

        # Try to split title and date/duration
        # The link content typically has title, then date, then duration
        parts = [t.strip() for t in link.stripped_strings]

        title = parts[0] if parts else title_text
        date_str = parts[1] if len(parts) > 1 else ""
        duration_str = parts[2] if len(parts) > 2 else ""

        ep_date = parse_pt_date(date_str) if date_str else datetime.now()
        duration_secs = parse_duration(duration_str) if duration_str else 0

        episodes.append({
            "title": title,
            "date": ep_date,
            "duration": duration_secs,
            "url": f"{BASE_URL}{href}",
            "episode_id": episode_id,
        })

    return episodes


def fetch_episodes_online() -> list:
    """Fetch and parse episodes from the RTP Play website."""
    import requests

    # Fetch the most recent episode page (which lists other episodes too)
    url = PROGRAM_URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    episodes = scrape_episodes_from_html(resp.text)
    print(f"Found {len(episodes)} episodes")

    # Extract audio URLs for each episode
    for i, ep in enumerate(episodes):
        print(f"  Extracting audio URL [{i+1}/{len(episodes)}]: {ep['title']}")
        ep["audio_url"] = extract_audio_url(ep["url"])
        if ep["audio_url"]:
            print(f"    OK")
        else:
            print(f"    No audio URL found")

    return episodes


def xml_escape(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def generate_rss(episodes: list) -> str:
    """Generate an RSS 2.0 XML feed with iTunes podcast extensions."""
    now = datetime.now()

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<rss version="2.0"')
    lines.append('  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"')
    lines.append('  xmlns:atom="http://www.w3.org/2005/Atom">')
    lines.append('  <channel>')
    lines.append(f'    <title>{xml_escape(PROGRAM_TITLE)}</title>')
    lines.append(f'    <link>{PROGRAM_URL}</link>')
    lines.append(f'    <description>{xml_escape(PROGRAM_DESCRIPTION)}</description>')
    lines.append(f'    <language>{PROGRAM_LANGUAGE}</language>')
    lines.append(f'    <copyright>© RTP - Rádio e Televisão de Portugal</copyright>')
    lines.append(f'    <lastBuildDate>{format_rfc822(now)}</lastBuildDate>')
    lines.append(f'    <generator>Panfletos RSS Generator</generator>')
    lines.append(f'    <atom:link href="{FEED_SELF_URL}" rel="self" type="application/rss+xml"/>')
    lines.append(f'    <itunes:author>{xml_escape(PROGRAM_AUTHOR)}</itunes:author>')
    lines.append(f'    <itunes:summary>{xml_escape(PROGRAM_DESCRIPTION)}</itunes:summary>')
    lines.append(f'    <itunes:type>episodic</itunes:type>')
    lines.append(f'    <itunes:explicit>false</itunes:explicit>')
    lines.append(f'    <itunes:owner>')
    lines.append(f'      <itunes:name>{xml_escape(PROGRAM_AUTHOR)}</itunes:name>')
    lines.append(f'    </itunes:owner>')
    lines.append(f'    <itunes:category text="{PROGRAM_CATEGORY}"/>')
    lines.append(f'    <image>')
    lines.append(f'      <url>{PROGRAM_IMAGE}</url>')
    lines.append(f'      <title>{xml_escape(PROGRAM_TITLE)}</title>')
    lines.append(f'      <link>{PROGRAM_URL}</link>')
    lines.append(f'    </image>')
    lines.append(f'    <itunes:image href="{PROGRAM_IMAGE}"/>')

    for ep in episodes:
        lines.append('    <item>')
        lines.append(f'      <title>{xml_escape(ep["title"])}</title>')
        lines.append(f'      <link>{ep["url"]}</link>')
        lines.append(f'      <guid isPermaLink="false">rtp-panfletos-e{ep["episode_id"]}</guid>')
        lines.append(f'      <pubDate>{format_rfc822(ep["date"])}</pubDate>')
        lines.append(f'      <description>{xml_escape(ep["title"])} - {xml_escape(PROGRAM_TITLE)} com {xml_escape(PROGRAM_AUTHOR)} na {CHANNEL}.</description>')
        audio_url = ep.get("audio_url")
        if audio_url:
            lines.append(f'      <enclosure url="{xml_escape(audio_url)}" length="0" type="audio/mpeg"/>')
        if ep["duration"] > 0:
            lines.append(f'      <itunes:duration>{format_itunes_duration(ep["duration"])}</itunes:duration>')
        lines.append(f'      <itunes:author>{xml_escape(PROGRAM_AUTHOR)}</itunes:author>')
        lines.append(f'      <itunes:summary>{xml_escape(ep["title"])} - Panfletos: música-política, canções-poder, criatividade-resistência.</itunes:summary>')
        lines.append('    </item>')

    lines.append('  </channel>')
    lines.append('</rss>')

    return '\n'.join(lines)


def generate_feed_from_hardcoded_data() -> str:
    """
    Generate RSS feed from hardcoded recent episode data.
    Use this when you can't make network requests.
    """
    episodes = [
        {"title": 'Cara de Espelho e "A Seita"', "date": datetime(2026, 2, 11, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e908229/{PROGRAM_SLUG}", "episode_id": "908229"},
        {"title": 'Bad Bunny e "DtMF"', "date": datetime(2026, 2, 10, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e907966/{PROGRAM_SLUG}", "episode_id": "907966"},
        {"title": 'Moonspell e "Desastre"', "date": datetime(2026, 2, 9, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e907751/{PROGRAM_SLUG}", "episode_id": "907751"},
        {"title": "Semana de 02 a 06 de Fevereiro de 2026", "date": datetime(2026, 2, 7, 12, 0), "duration": 1620, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e907740/{PROGRAM_SLUG}", "episode_id": "907740"},
        {"title": 'Carlos Paredes e "Verdes Anos"', "date": datetime(2026, 2, 6, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e907254/{PROGRAM_SLUG}", "episode_id": "907254"},
        {"title": "Verdi e o coro dos escravos hebreus", "date": datetime(2026, 2, 5, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e907010/{PROGRAM_SLUG}", "episode_id": "907010"},
        {"title": 'Billy Bragg e "City of Heroes"', "date": datetime(2026, 2, 4, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e906746/{PROGRAM_SLUG}", "episode_id": "906746"},
        {"title": 'Nicki Minaj e "Black Barbies"', "date": datetime(2026, 2, 3, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e906461/{PROGRAM_SLUG}", "episode_id": "906461"},
        {"title": 'Bruce Springsteen e "Streets of Minneapolis"', "date": datetime(2026, 2, 2, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e906203/{PROGRAM_SLUG}", "episode_id": "906203"},
        {"title": "Semana de 26 a 30 de Janeiro de 2026", "date": datetime(2026, 1, 31, 12, 0), "duration": 1920, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e905765/{PROGRAM_SLUG}", "episode_id": "905765"},
        {"title": 'Dino d\'Santiago e "Utopia"', "date": datetime(2026, 1, 30, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e905712/{PROGRAM_SLUG}", "episode_id": "905712"},
        {"title": 'Pedro Abrunhosa e "Oxalá o meu vestido ainda se lembre de mim"', "date": datetime(2026, 1, 29, 12, 0), "duration": 420, "url": f"{BASE_URL}/play/{PROGRAM_ID}/e905426/{PROGRAM_SLUG}", "episode_id": "905426"},
    ]
    return generate_rss(episodes)


def main():
    parser = argparse.ArgumentParser(
        description="Generate RSS feed for Panfletos (Antena 1 - RTP)"
    )
    parser.add_argument(
        "--output", "-o",
        default="panfletos_rss.xml",
        help="Output file path (default: panfletos_rss.xml)"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use hardcoded episode data (no network required)"
    )
    args = parser.parse_args()

    if args.offline:
        print("Generating feed from hardcoded data (offline mode)...")
        xml_content = generate_feed_from_hardcoded_data()
    else:
        try:
            episodes = fetch_episodes_online()
            if not episodes:
                print("No episodes found, falling back to hardcoded data")
                xml_content = generate_feed_from_hardcoded_data()
            else:
                xml_content = generate_rss(episodes)
        except Exception as e:
            print(f"Error fetching online data: {e}")
            print("Falling back to hardcoded data...")
            xml_content = generate_feed_from_hardcoded_data()

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print(f"RSS feed saved to: {args.output}")
    print(f"Feed URL for your reader: file://{args.output}")


if __name__ == "__main__":
    main()
