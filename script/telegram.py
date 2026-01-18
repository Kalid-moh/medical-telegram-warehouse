"""
Telegram Scraper for Ethiopian Medical Channels
================================================
This script scrapes public Telegram channels and stores:
- Raw messages as JSON (partitioned by date): data/raw/telegram_messages/YYYY-MM-DD/channel.json
- Images: data/raw/images/{channel_name}/{message_id}.jpg
- CSV backup: data/raw/csv/YYYY-MM-DD/telegram_data.csv
- Logs: logs/scrape_YYYY-MM-DD.log

Usage:
    python scripts/telegram.py --path data --limit 500
Required environment variables in .env:
    Tg_API_ID=your_api_id
    Tg_API_HASH=your_api_hash
"""

import os
import csv
import json
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaPhoto

# Allow running this file directly: `python scripts/telegram.py`
# by adding the project root to PYTHONPATH so `import src.*` works.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.datalake import write_channel_messages_json, write_manifest

# =============================================================================
# CONFIGURATION
# =============================================================================

load_dotenv()

# Validate required environment variables before proceeding
api_id_str = os.getenv("Tg_API_ID")
api_hash = os.getenv("Tg_API_HASH")

if not api_id_str or not api_hash:
    print("ERROR: Missing Tg_API_ID or Tg_API_HASH in .env file")
    print("Create a .env file with:")
    print("  Tg_API_ID=your_api_id")
    print("  Tg_API_HASH=your_api_hash")
    sys.exit(1)

api_id = int(api_id_str)

# Date string for partitioning output files
TODAY = datetime.today().strftime("%Y-%m-%d")

# Default throttling (seconds). You can override these via CLI args.
DEFAULT_CHANNEL_DELAY = 3.0
DEFAULT_MESSAGE_DELAY = 1.0

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging to both file and console
logger = logging.getLogger("telegram_scraper")
logger.setLevel(logging.INFO)

# File handler - logs everything to file
file_handler = logging.FileHandler(
    os.path.join(LOG_DIR, f"scrape_{TODAY}.log"),
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Console handler - shows progress in terminal
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# =============================================================================
# SCRAPING FUNCTIONS
# =============================================================================

async def scrape_channel(
    client: TelegramClient,
    channel: str,
    writer: csv.writer,
    base_path: str,
    date_str: str,
    limit: int = 100,
    message_delay: float = DEFAULT_MESSAGE_DELAY,
    channel_delay: float = DEFAULT_CHANNEL_DELAY,
    max_retries: int = 3,
) -> int:
    """
    Scrape a single Telegram channel and save messages + images.
    
    Args:
        client: Authenticated TelegramClient instance
        channel: Channel username (e.g., '@lobelia4cosmetics')
        writer: CSV writer to append rows
        image_dir: Directory to save downloaded images
        json_save_dir: Directory to save JSON output
        limit: Maximum number of messages to scrape (default 100)
    
    Returns:
        Number of messages scraped
    """
    channel_name = channel.strip('@')
    
    retries = 0
    while True:
        try:
            # Get channel entity (validates channel exists and is accessible)
            entity = await client.get_entity(channel)
            channel_title = entity.title
            messages = []

            # Create image directory for this channel
            # Path format: data/raw/images/{channel_name}/
            channel_image_dir = os.path.join(base_path, "raw", "images", channel_name)
            os.makedirs(channel_image_dir, exist_ok=True)

            logger.info(f"Starting scrape of {channel} (limit={limit})")

            # Iterate through channel messages (newest first by default)
            async for message in client.iter_messages(entity, limit=limit):
                image_path: Optional[str] = None
                has_media = message.media is not None

                # Download photo if present
                # Challenge requires: data/raw/images/{channel_name}/{message_id}.jpg
                if has_media and isinstance(message.media, MessageMediaPhoto):
                    filename = f"{message.id}.jpg"
                    image_path = os.path.join(channel_image_dir, filename)
                    try:
                        await client.download_media(message.media, image_path)
                    except Exception as e:
                        logger.warning(f"Failed to download image for message {message.id}: {e}")
                        image_path = None

                # Build message dict with all required fields
                message_dict = {
                    "message_id": message.id,
                    "channel_name": channel_name,
                    "channel_title": channel_title,
                    "message_date": message.date.isoformat(),  # ISO format for consistency
                    "message_text": message.message or "",     # Handle None text
                    "has_media": has_media,
                    "image_path": image_path,
                    "views": message.views or 0,               # Some messages may not have views
                    "forwards": message.forwards or 0,
                }

                # Write to CSV (backup/alternative format)
                writer.writerow([
                    message_dict["message_id"],
                    message_dict["channel_name"],
                    message_dict["channel_title"],
                    message_dict["message_date"],
                    message_dict["message_text"],
                    message_dict["has_media"],
                    message_dict["image_path"],
                    message_dict["views"],
                    message_dict["forwards"],
                ])

                messages.append(message_dict)

                # Optional delay between messages (reduces risk of rate limiting).
                if message_delay and message_delay > 0:
                    await asyncio.sleep(message_delay)

            write_channel_messages_json(
                base_path=base_path,
                date_str=date_str,
                channel_name=channel_name,
                messages=messages,
            )

            logger.info(f"Finished scraping {channel}: {len(messages)} messages saved")

            # Delay between channels (recommended).
            if channel_delay and channel_delay > 0:
                await asyncio.sleep(channel_delay)

            return len(messages)

        except FloodWaitError as e:
            # Telegram explicitly asks you to wait e.seconds
            wait_seconds = int(getattr(e, "seconds", 0) or 0)
            wait_seconds = max(wait_seconds, 1)
            logger.warning(f"FloodWaitError for {channel}: sleeping {wait_seconds}s")
            await asyncio.sleep(wait_seconds)
            retries += 1
            if retries > max_retries:
                logger.error(f"Too many FloodWait retries for {channel}. Skipping.")
                return 0
        except Exception as e:
            logger.error(f"Error scraping {channel}: {e}")
            return 0


async def scrape_all_channels(
    client: TelegramClient,
    channels: List[str],
    base_path: str,
    limit: int = 100,
    message_delay: float = DEFAULT_MESSAGE_DELAY,
    channel_delay: float = DEFAULT_CHANNEL_DELAY,
) -> dict:
    """
    Scrape multiple Telegram channels and organize output.
    
    Args:
        client: TelegramClient instance (will be started if not already)
        channels: List of channel usernames to scrape
        base_path: Base directory for all output (e.g., 'data')
        limit: Max messages per channel
    
    Returns:
        Dict with scraping statistics per channel
    """
    await client.start()
    logger.info(f"Client authenticated. Scraping {len(channels)} channels...")
    
    # Setup output directories following challenge spec
    csv_dir = os.path.join(base_path, "raw", "csv", TODAY)
    json_dir = os.path.join(base_path, "raw", "telegram_messages", TODAY)
    image_dir = os.path.join(base_path, "raw", "images")
    
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(image_dir, exist_ok=True)
    
    # CSV file with all messages (useful for quick inspection)
    csv_file_path = os.path.join(csv_dir, "telegram_data.csv")
    stats = {}
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header row matching challenge required fields
        writer.writerow([
            'message_id',
            'channel_name', 
            'channel_title',
            'message_date',
            'message_text',
            'has_media',
            'image_path',
            'views',
            'forwards'
        ])
        
        channel_counts = {}

        for channel in channels:
            logger.info(f"Scraping {channel}...")
            count = await scrape_channel(
                client=client,
                channel=channel,
                writer=writer,
                base_path=base_path,
                date_str=TODAY,
                limit=limit,
                message_delay=message_delay,
                channel_delay=channel_delay,
            )
            stats[channel] = count
            channel_counts[channel.strip("@")] = count

        write_manifest(
            base_path=base_path,
            date_str=TODAY,
            channel_message_counts=channel_counts,
        )
    
    # Log summary
    total = sum(stats.values())
    logger.info(f"Scraping complete. Total messages: {total}")
    for ch, count in stats.items():
        logger.info(f"  {ch}: {count} messages")
    
    return stats


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Telegram Scraper for Ethiopian Medical Channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/telegram.py --path data --limit 500
    python scripts/telegram.py  # Uses defaults: data/, 1000 messages
        """
    )
    parser.add_argument(
        "--path", 
        type=str, 
        default="data", 
        help="Base data directory (default: data)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max messages to scrape per channel (default: 100)"
    )
    parser.add_argument(
        "--message-delay",
        type=float,
        default=DEFAULT_MESSAGE_DELAY,
        help="Pause (seconds) between processing messages (default: 0)"
    )
    parser.add_argument(
        "--channel-delay",
        type=float,
        default=DEFAULT_CHANNEL_DELAY,
        help="Pause (seconds) after finishing a channel (default: 3)"
    )
    args = parser.parse_args()
    
    # Initialize Telegram client
    # Session file stores auth so you don't need to re-login each time
    client = TelegramClient("telegram_scraper_session", api_id, api_hash)
    logger.info("Telegram client initialized")
    
    # Target channels from challenge document
    target_channels = [
        #'@cheMed123',           # CheMed - Medical products
        #'@lobelia4cosmetics',   # Lobelia - Cosmetics and health products  
        '@tikvahpharma',
        '@tenamereja'       # Tikvah Pharma - Pharmaceuticals
        # Add more channels from https://et.tgstat.com/medicine as needed
    ]
    
    async def main() -> None:
        # Python 3.14: prefer asyncio.run() with an async TelegramClient context.
        async with client:
            await scrape_all_channels(
                client,
                target_channels,
                args.path,
                args.limit,
                message_delay=args.message_delay,
                channel_delay=args.channel_delay,
            )

    asyncio.run(main())