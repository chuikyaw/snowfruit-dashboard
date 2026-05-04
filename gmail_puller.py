"""
gmail_puller.py
───────────────
Automatically checks Gmail for the weekly SnowFruit sales email,
downloads the .xlsx attachment, and saves it as latest_sales.xlsx
so the Streamlit app picks it up on next load.

Setup (one-time):
  1. Go to https://console.cloud.google.com
  2. Create a project → Enable Gmail API
  3. Create OAuth 2.0 credentials (Desktop app) → download as credentials.json
  4. Place credentials.json in this same folder
  5. Run: python gmail_puller.py --setup
     (opens a browser, asks you to log in once, saves token.json)
  6. After that, just run: python gmail_puller.py
     (or schedule it with cron / GitHub Actions)

Usage:
  python gmail_puller.py               # Check inbox and download latest
  python gmail_puller.py --setup       # First-time auth flow
  python gmail_puller.py --dry-run     # Preview matching emails without downloading
  python gmail_puller.py --query "subject:SFT Weekly"   # Custom search
"""

import os
import sys
import base64
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# ── Third-party (installed via requirements.txt) ──────────────────────────────
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(
        "Missing Google libraries. Run:\n"
        "  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
    )
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
SCOPES             = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE   = "credentials.json"
TOKEN_FILE         = "token.json"
OUTPUT_FILE        = "latest_sales.xlsx"

# Edit these to match your actual email subject / sender
DEFAULT_QUERY      = "subject:weekly sales has:attachment filename:xlsx"
# Example more specific query:
# DEFAULT_QUERY    = "from:reports@snowfruit.com subject:SFT Weekly has:attachment filename:xlsx"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Auth ──────────────────────────────────────────────────────────────────────
def get_gmail_service():
    """Authenticate and return a Gmail API service object."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing access token…")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                log.error(
                    f"'{CREDENTIALS_FILE}' not found.\n"
                    "Download it from Google Cloud Console (OAuth 2.0 → Desktop App)\n"
                    "and place it in this folder, then run: python gmail_puller.py --setup"
                )
                sys.exit(1)
            log.info("Starting OAuth flow — your browser will open…")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        log.info(f"Token saved to {TOKEN_FILE}")

    return build("gmail", "v1", credentials=creds)


# ── Gmail helpers ─────────────────────────────────────────────────────────────
def search_messages(service, query: str, max_results: int = 10):
    """Return a list of message metadata dicts matching the query."""
    try:
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        return result.get("messages", [])
    except HttpError as e:
        log.error(f"Gmail search failed: {e}")
        return []


def get_message(service, msg_id: str):
    """Fetch full message by ID."""
    return service.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()


def extract_subject(msg) -> str:
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "subject":
            return h["value"]
    return "(no subject)"


def extract_date(msg) -> str:
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "date":
            return h["value"]
    return "(no date)"


def find_xlsx_attachments(msg):
    """Yield (filename, attachment_id) for every xlsx attachment in a message."""
    parts = msg.get("payload", {}).get("parts", [])
    for part in parts:
        fname = part.get("filename", "")
        mime  = part.get("mimeType", "")
        if fname.lower().endswith(".xlsx") or "spreadsheet" in mime or "excel" in mime:
            att_id = part.get("body", {}).get("attachmentId")
            if att_id:
                yield fname, att_id


def download_attachment(service, msg_id: str, att_id: str) -> bytes:
    """Download and decode an attachment, return raw bytes."""
    att = service.users().messages().attachments().get(
        userId="me", messageId=msg_id, id=att_id
    ).execute()
    data = att.get("data", "")
    # Gmail uses URL-safe base64
    return base64.urlsafe_b64decode(data + "==")


# ── Core logic ────────────────────────────────────────────────────────────────
def pull_latest(query: str = DEFAULT_QUERY, dry_run: bool = False) -> bool:
    """
    Find the most recent email matching `query`, download its xlsx attachment.
    Returns True if a file was saved, False otherwise.
    """
    log.info("Connecting to Gmail…")
    service = get_gmail_service()

    log.info(f"Searching: {query}")
    messages = search_messages(service, query, max_results=5)

    if not messages:
        log.warning("No matching emails found.")
        return False

    log.info(f"Found {len(messages)} matching email(s). Checking the most recent…")

    for msg_meta in messages:
        msg = get_message(service, msg_meta["id"])
        subject = extract_subject(msg)
        date    = extract_date(msg)
        log.info(f"  Email: '{subject}' | {date}")

        attachments = list(find_xlsx_attachments(msg))
        if not attachments:
            log.info("  → No xlsx attachments, skipping.")
            continue

        for fname, att_id in attachments:
            log.info(f"  → Attachment found: {fname}")
            if dry_run:
                log.info("  → DRY RUN: skipping download.")
                return True

            raw = download_attachment(service, msg_meta["id"], att_id)
            out_path = Path(OUTPUT_FILE)
            out_path.write_bytes(raw)

            size_kb = len(raw) / 1024
            log.info(f"  ✅ Saved {fname} → {OUTPUT_FILE} ({size_kb:.1f} KB)")
            return True

    log.warning("No xlsx attachment found in any matching email.")
    return False


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Pull weekly sales xlsx from Gmail for the SnowFruit dashboard."
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Run the one-time OAuth login flow."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List matching emails without downloading anything."
    )
    parser.add_argument(
        "--query", default=DEFAULT_QUERY,
        help=f"Gmail search query (default: '{DEFAULT_QUERY}')"
    )
    args = parser.parse_args()

    if args.setup:
        log.info("Running one-time authentication setup…")
        get_gmail_service()
        log.info("✅ Setup complete! You can now run 'python gmail_puller.py' without --setup.")
        return

    success = pull_latest(query=args.query, dry_run=args.dry_run)

    if success and not args.dry_run:
        log.info(f"\n✅ Done. Open the Streamlit app — it will load '{OUTPUT_FILE}' automatically.")
    elif not success:
        log.warning(
            "\n⚠️  No file was downloaded. Check that:\n"
            "  1. The email exists in your inbox\n"
            "  2. Your --query matches the email subject/sender\n"
            "  3. The email has an .xlsx attachment\n"
            "  Try: python gmail_puller.py --dry-run"
        )


if __name__ == "__main__":
    main()
