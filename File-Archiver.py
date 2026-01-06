import os
import time
import zipfile
import logging
from datetime import datetime

LOG_FILE = "/var/sftp/archiver.log"

# Setup logging once
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def archive_old_logs(target_dir, archive_dir, age_days):
    logging.info(f"Starting archive process for: {target_dir} (older than {age_days} days)")
    now = time.time()
    cutoff = now - (age_days * 86400)
    old_files = []

    # Walk through the target directory and collect old files
    for root, _, files in os.walk(target_dir):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                stat_info = os.stat(filepath)
                mtime = stat_info.st_mtime
                logging.info(f"FILE: {filepath}")
                logging.info(f"  Size     : {stat_info.st_size} bytes")
                logging.info(f"  Modified : {datetime.fromtimestamp(mtime)}")
                logging.info(f"  Mode     : {oct(stat_info.st_mode)}")
                logging.info(f"  UID/GID  : {stat_info.st_uid}/{stat_info.st_gid}")

                if mtime < cutoff:
                    old_files.append(filepath)
                    logging.info("  → Selected for archive.")
                else:
                    logging.info("  → Skipped (too new).")

            except Exception as e:
                logging.warning(f"Error reading file: {filepath} - {e}")

    logging.info(f"Total files selected for archive: {len(old_files)}")

    if not old_files:
        logging.info("No files to archive. Exiting.")
        return

    # Create archive
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"logs_archive_{timestamp}.zip"
    archive_path = os.path.join(archive_dir, archive_name)

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in old_files:
            try:
                arcname = os.path.relpath(f, start=target_dir)
                zipf.write(f, arcname)
                logging.info(f"✔ Archived: {f}")
                os.remove(f)
                logging.info(f"🗑️  Deleted: {f}")
            except Exception as e:
                logging.error(f"✘ Failed to archive or delete: {f} - {e}")

    logging.info(f"✅ Archive created: {archive_path} with {len(old_files)} file(s)")

# Example usage
if __name__ == "__main__":
    #Get them logs
    archive_old_logs(
        #can variable these
        target_dir="/admin/log/",
        archive_dir="/admin/log_archive/",
        age_days=60
    )

