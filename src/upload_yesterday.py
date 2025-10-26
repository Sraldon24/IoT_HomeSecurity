#!/usr/bin/env python3
"""
upload_yesterday.py
Zips yesterday’s DomiSafe logs and captured images for archival or cloud upload.
Add to crontab for daily automation.
"""
import os
import zipfile
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Uploader")

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_DIR, "logs")
IMAGES_DIR = os.path.join(PROJECT_DIR, "captured_images")
BACKUP_DIR = os.path.join(PROJECT_DIR, "backups")

os.makedirs(BACKUP_DIR, exist_ok=True)

def zip_yesterday():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    zip_name = os.path.join(BACKUP_DIR, f"domisafe_backup_{yesterday}.zip")

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        count = 0

        for folder in [LOGS_DIR, IMAGES_DIR]:
            if not os.path.exists(folder):
                continue
            for fname in os.listdir(folder):
                if yesterday in fname:
                    fpath = os.path.join(folder, fname)
                    zipf.write(fpath, os.path.relpath(fpath, PROJECT_DIR))
                    count += 1

        logger.info(f"✅ Created backup: {zip_name} ({count} files)")
        if count == 0:
            logger.warning("No files matched yesterday’s date.")
    return zip_name

if __name__ == "__main__":
    try:
        zip_yesterday()
    except Exception as e:
        logger.error(f"Backup failed: {e}", exc_info=True)
