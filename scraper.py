"""
Telegram Scraper - Scrape Telegram channels, groups, messages, and member data
Extract messages, media, member info, channel stats, and group activity.

For production Telegram data, use CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import re
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

@dataclass
class TelegramMessage:
    message_id: str = ""
    channel: str = ""
    author: str = ""
    date: str = ""
    text: str = ""
    views: str = ""
    forwards: str = ""
    media_type: str = ""
    media_url: str = ""
    url: str = ""

@dataclass
class TelegramChannel:
    channel_id: str = ""
    username: str = ""
    title: str = ""
    description: str = ""
    member_count: str = ""
    profile_image: str = ""
    verified: bool = False

class TelegramScraper:
    BASE_URL = "https://t.me"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, proxy: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def get_channel_info(self, channel: str) -> TelegramChannel:
        url = f"{self.BASE_URL}/{channel}"
        info = TelegramChannel(username=channel)
        try:
            resp = self.session.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            title_el = soup.find("meta", property="og:title")
            if title_el:
                info.title = title_el.get("content", "")
            desc_el = soup.find("meta", property="og:description")
            if desc_el:
                info.description = desc_el.get("content", "")
            img_el = soup.find("meta", property="og:image")
            if img_el:
                info.profile_image = img_el.get("content", "")
            members_match = re.search(r"([\d,]+)\s*subscribers?", resp.text)
            if members_match:
                info.member_count = members_match.group(1).replace(",", "")
        except Exception as e:
            print(f"Error getting channel @{channel}: {e}")
        return info

    def get_channel_messages(self, channel: str, limit: int = 50) -> List[TelegramMessage]:
        messages = []
        for msg_id in range(1, limit + 1):
            url = f"{self.BASE_URL}/{channel}/{msg_id}"
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                msg = TelegramMessage(channel=channel, message_id=str(msg_id), url=url)
                text_el = soup.find("div", class_=re.compile("message|text"))
                if text_el:
                    msg.text = text_el.get_text(strip=True)
                else:
                    og_desc = soup.find("meta", property="og:description")
                    if og_desc:
                        msg.text = og_desc.get("content", "")
                date_el = soup.find("time")
                if date_el:
                    msg.date = date_el.get("datetime", date_el.get_text(strip=True))
                views_el = soup.find(class_=re.compile("views|count"))
                if views_el:
                    msg.views = views_el.get_text(strip=True)
                og_type = soup.find("meta", property="og:type")
                if og_type:
                    msg.media_type = og_type.get("content", "")
                img_el = soup.find("meta", property="og:image")
                if img_el:
                    msg.media_url = img_el.get("content", "")
                if msg.text or msg.media_url:
                    messages.append(msg)
                time.sleep(0.5)
            except Exception:
                continue
        return messages

    def search_channels(self, query: str, limit: int = 20) -> List[Dict]:
        url = "https://t.me/search"
        params = {"q": query}
        results = []
        try:
            resp = self.session.get(url, params=params, timeout=30)
            soup = BeautifulSoup(resp.text, "html.parser")
            for el in soup.find_all("a", href=re.compile(r"^/\w+$")):
                href = el.get("href", "")
                username = href.lstrip("/")
                results.append({"username": username, "name": el.get_text(strip=True)})
        except Exception as e:
            print(f"Error searching: {e}")
        return results[:limit]

    @staticmethod
    def export_json(data, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(d) if hasattr(d, "__dataclass_fields__") else d for d in data], f, indent=2)
        print(f"Exported {len(data)} items to {filepath}")

    @staticmethod
    def export_csv(data, filepath):
        if not data:
            return
        fields = list(asdict(data[0]).keys()) if hasattr(data[0], "__dataclass_fields__") else list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for item in data:
                w.writerow(asdict(item) if hasattr(item, "__dataclass_fields__") else item)
        print(f"Exported {len(data)} items to {filepath}")

def main():
    p = argparse.ArgumentParser(description="Telegram Scraper")
    p.add_argument("--channel", "-c", help="Telegram channel username (without @)")
    p.add_argument("--info", action="store_true", help="Get channel info only")
    p.add_argument("--limit", "-n", type=int, default=50)
    p.add_argument("--output", "-o", default="telegram_results")
    p.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    p.add_argument("--proxy", default=None)
    args = p.parse_args()
    s = TelegramScraper(proxy=args.proxy)
    if not args.channel:
        print("Provide --channel")
        return
    if args.info:
        data = [s.get_channel_info(args.channel)]
    else:
        data = s.get_channel_messages(args.channel, args.limit)
    ext = "json" if args.format == "json" else "csv"
    TelegramScraper.export_json(data, f"{args.output}.{ext}") if args.format == "json" else TelegramScraper.export_csv(data, f"{args.output}.{ext}")

if __name__ == "__main__":
    main()
