# SnowFruit Sales Dashboard — Setup Guide
**From zero to a shareable URL in ~20 minutes**

---

## What You're Building

A web app anyone can open with a link. You drop in a weekly `.xlsx` file and instantly get:
- A sales chart (revenue + units by day)
- Top & bottom items per day and for the full week
- A weekly rankings table

---

## Files in This Folder

| File | What it does |
|------|-------------|
| `app.py` | The dashboard app itself |
| `gmail_puller.py` | Auto-downloads your weekly xlsx from Gmail |
| `requirements.txt` | List of packages the app needs |
| `.gitignore` | Tells GitHub what NOT to upload (keeps tokens safe) |
| `SETUP_GUIDE.md` | This file |

---

## Phase 1 — GitHub (5 min)

**Step 1 — Create a free account**
1. Go to [github.com](https://github.com)
2. Click **Sign up** → fill in username, email, password
3. Verify your email

**Step 2 — Create a repository**
1. Click the **+** icon (top right) → **New repository**
2. Name it: `snowfruit-dashboard`
3. Keep it **Public** ✅
4. Check **Add a README file** ✅
5. Click **Create repository**

**Step 3 — Upload your files**
1. Click **Add file** → **Upload files**
2. Drag and drop ALL files from this folder:
   - `app.py`
   - `gmail_puller.py`
   - `requirements.txt`
   - `.gitignore` ← rename from `gitignore.txt` if needed
3. Click **Commit changes**

> ⚠️ Do NOT upload `credentials.json` or `token.json` — those are secret!

---

## Phase 2 — Streamlit Cloud (10 min)

**Step 1 — Create a Streamlit account**
1. Go to [streamlit.io](https://streamlit.io) → click **Get started free**
2. Sign in with GitHub (so they're connected automatically)

**Step 2 — Deploy your app**
1. Click **New app**
2. Select your repository: `snowfruit-dashboard`
3. Branch: `main`
4. Main file path: `app.py`
5. Click **Deploy!**

Streamlit will install your packages and build the app. Takes about 2–3 minutes.

**Step 3 — Get your URL**
Your app is live at something like:
```
https://pinshichuy-snowfruit-dashboard.streamlit.app
```
Share this link with anyone — they don't need an account to view it.

---

## Phase 3 — Gmail Automation (optional, 10 min)

This lets the app automatically pick up new files from your email.

**Step 1 — Enable Gmail API**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **Select a project** → **New Project** → name it `SnowFruit`
3. Go to **APIs & Services** → **Library**
4. Search **Gmail API** → click it → click **Enable**

**Step 2 — Create credentials**
1. Go to **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `gmail-puller`
5. Click **Create** → **Download JSON**
6. Rename the file to `credentials.json` and put it in this folder

**Step 3 — One-time login**
Open a terminal in this folder and run:
```bash
pip install -r requirements.txt
python gmail_puller.py --setup
```
Your browser opens → log in with your Gmail account → click Allow.
A `token.json` file is saved. You only do this once.

**Step 4 — Test it**
```bash
python gmail_puller.py --dry-run
```
This previews which emails match without downloading anything.

If it finds the right email, run for real:
```bash
python gmail_puller.py
```
It saves the attachment as `latest_sales.xlsx`. Next time you open the app, it loads automatically.

**Step 5 — Customize the email search**
Open `gmail_puller.py` and edit line ~42:
```python
DEFAULT_QUERY = "subject:weekly sales has:attachment filename:xlsx"
```
Change it to match your actual email subject. Examples:
```python
DEFAULT_QUERY = "from:store327@snowfruit.com subject:Weekly Report"
DEFAULT_QUERY = "subject:SFT 327 Week has:attachment"
```

---

## Running Weekly

**Option A — Manual (easiest)**
Each week: open the app URL → click **Browse files** → upload the new xlsx.

**Option B — Run the puller script**
When your weekly email arrives:
```bash
python gmail_puller.py
```
Then refresh the app — it auto-loads the new file.

**Option C — Schedule it (fully automatic)**
On Mac/Linux, open Terminal and run `crontab -e`, then add:
```
0 9 * * MON cd /path/to/this/folder && python gmail_puller.py
```
This runs every Monday at 9 AM automatically.

On Windows, use Task Scheduler:
1. Open **Task Scheduler** → **Create Basic Task**
2. Trigger: **Weekly**, Monday
3. Action: **Start a program** → `python`
4. Arguments: `gmail_puller.py`
5. Start in: the path to this folder

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App shows "No data found" | Check your xlsx has a sheet named `Transactions` |
| Column not detected | Open the xlsx — note the exact column names, tell Claude |
| `credentials.json` not found | Re-download from Google Cloud Console |
| `token.json` expired | Delete it, run `python gmail_puller.py --setup` again |
| Streamlit shows import error | Make sure `requirements.txt` is uploaded to GitHub |
| Gmail search finds wrong email | Adjust `DEFAULT_QUERY` in `gmail_puller.py` |
| App URL not working | Check Streamlit Cloud logs (click **Manage app** bottom-right) |

---

## Updating the App

Any time you upload a new version of `app.py` to GitHub, Streamlit Cloud redeploys automatically — usually within 30 seconds. No action needed.

---

*Built for Store 327 · SnowFruit · Updated May 2026*
