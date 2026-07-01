# ArthSaathi Setup Guide

This guide assumes an empty Windows laptop and walks you through everything needed to get ArthSaathi running, in the order you should actually do it. Follow it top to bottom — do not skip steps even if something looks optional.

Commands are given for both **Git Bash** and **PowerShell**. Pick one terminal and stick with it for the whole session (mixing the two mid-task is a common source of confusion, since path separators differ: `/c/arthsaathi` vs `C:\arthsaathi`).

## The Big Picture

```text
Telegram user
  -> Telegram bot (bot/app.py)            long-polls Telegram, no public URL needed
  -> FastAPI backend (backend/app.py)     http://localhost:3000
  -> MongoDB                              stores users, transactions, conversations
  -> LLM API (Groq / Bedrock / HF)        routing + agent replies
  -> Sarvam AI                            voice transcription + Indian-language translation
  -> data.gov.in / Google Safe Browsing   mandi prices + scam link checks (optional)
```

You will run **two terminals side by side**: one for the backend, one for the bot.

## What You'll Need Before Starting

Have these ready (accounts are free to create):

- [ ] A GitHub account with access to this repo
- [ ] A MongoDB Atlas account (free tier)
- [ ] A Groq account (or another LLM provider — see Step 9)
- [ ] A Sarvam AI account (voice + translation)
- [ ] A Telegram account + the Telegram desktop or mobile app
- [ ] (Optional) A Google Cloud account for Safe Browsing / data.gov.in key for mandi prices

If the hackathon organizers are providing an LLM (e.g. AWS Bedrock), you don't need the Groq account — see Step 9 for swapping providers.

## Project Folder Structure

```text
arthsaathi/
  backend/
    app.py                    FastAPI backend entry point
    db.py                     MongoDB connection, collections, indexes
    users.py                  User lookup / creation
    onboarding.py             First-time user profile setup
    menu.py                   /menu command handling
    language.py               Translate to/from English (Sarvam)
    voice.py                  Voice note transcription (Sarvam Saarika)
    goals.py                  Savings goal storage
    requirements.txt          Backend Python packages
    data/
      schemes.json            Government scheme data (loaded directly, no DB import needed)
      persona_schemes.json    Which schemes map to which occupation
      rbi_registered.csv      RBI registered entity data for scam checks
    ai/
      graph.py                Routes user messages to the right agent
      schemes.py               Scheme lookup + reply formatting
      profile_update.py       Profile edits via chat
      mandi_prices.py         Crop/commodity price lookup
      config/
        llm.py                 LLM API configuration (swap providers here)
      agents/
        tracker_agent.py       Parses bank/UPI SMS into transactions
        insights_agent.py      Spending summaries
        jargon_agent.py        Explains financial terms
        scam_agent.py          Fraud/scam link detection
        planner_agent.py       Savings goal planning
    uploads/                  Temporary voice uploads (created at runtime)
    charts/                   Generated chart images (created at runtime)
  bot/
    app.py                    Telegram bot entry point (long polling)
    requirements.txt          Bot Python packages
  .venv/                      Local Python virtual environment (you create this)
  .gitignore
  SETUP.md                    This guide
```

Files you create locally and never commit:

```text
backend/.env               Backend secrets and API keys
bot/.env                   Telegram bot token and backend URL
```

`.env` files are already listed in `.gitignore` — do not remove that entry.

---

## Step 1: Install VS Code

1. Go to https://code.visualstudio.com/
2. Download the Windows installer and run it.
3. During install, tick:
   - Add to PATH
   - Open with Code (both checkboxes)
   - Register Code as an editor for supported file types

## Step 2: Install VS Code Extensions

Open VS Code → Extensions panel (`Ctrl+Shift+X`) → install:

- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Python Debugger** (Microsoft)
- **DotENV** (for `.env` file syntax highlighting)

Optional but useful:

- **GitLens** — richer git history/blame in the editor
- **MongoDB for VS Code** — browse your Atlas collections without leaving the editor

**Do not install any AI coding assistant extension** — no GitHub Copilot, Copilot Chat, Continue, Codeium, Cursor, Amazon Q, Tabnine, CodeGPT, Claude for VS Code, or similar. The hackathon organizers provide their own AI tool; installing another one can violate hackathon rules and may conflict with the provided one.

## Step 3: Install Git (and Git Bash)

1. Go to https://git-scm.com/download/win
2. Run the installer with default options. This installs **Git Bash** automatically — there is nothing extra to install in VS Code for it.
3. Verify:

```bash
git --version
```

To use Git Bash *inside* VS Code's integrated terminal (recommended if you're more comfortable with Unix-style commands):

1. Open VS Code, open the integrated terminal (`` Ctrl+` ``).
2. Click the dropdown arrow next to the `+` icon in the terminal panel.
3. Select **Git Bash** from the list. If it's not listed, click "Select Default Profile" and choose it there, or restart VS Code — it auto-detects Git Bash once Git for Windows is installed.

No VS Code extension is required for this — it's a built-in terminal profile, Git Bash just needs to be installed on the machine first.

## Step 4: Install Python

1. Go to https://www.python.org/downloads/windows/
2. Download Python 3.11.
3. On the first installer screen, tick **Add python.exe to PATH** before clicking Install.
4. Verify (either terminal):

```bash
python --version
python -m pip --version
```

Expected: `Python 3.11.x` and a `pip ...` version line.

---

## Step 5: Get the Project on Your Computer

If starting fresh from GitHub:

Git Bash:

```bash
cd ~/Desktop
git clone <YOUR_GITHUB_REPO_URL> arthsaathi
cd arthsaathi
code .
```

PowerShell:

```powershell
cd Desktop
git clone <YOUR_GITHUB_REPO_URL> arthsaathi
cd arthsaathi
code .
```

Replace `<YOUR_GITHUB_REPO_URL>` with the real repo URL.

If you already have the folder, just open it:

Git Bash:

```bash
cd /c/arthsaathi
code .
```

PowerShell:

```powershell
cd C:\arthsaathi
code .
```

## Step 6: Create a Python Virtual Environment

From the project root:

Git Bash:

```bash
cd /c/arthsaathi
python -m venv .venv
source .venv/Scripts/activate
```

PowerShell:

```powershell
cd C:\arthsaathi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation with an execution-policy error, run this once, then re-activate:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

When active, your prompt should show `(.venv)` at the start of the line. Do this every time you open a new terminal for this project.

## Step 7: Install Python Packages

With the virtual environment active:

Git Bash:

```bash
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
python -m pip install -r bot/requirements.txt
```

PowerShell:

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m pip install -r bot\requirements.txt
```

This installs:

- `fastapi` + `uvicorn` — backend server
- `pymongo` + `dnspython` — MongoDB
- `python-dotenv` — reads `.env` files
- `sarvamai` — voice transcription (Saarika) and translation (Mayura)
- `matplotlib` — generated charts for insights
- `python-whois` + `rapidfuzz` — scam/link checks
- `python-telegram-bot` (bot only) — Telegram polling
- `requests` — HTTP calls to the LLM and other APIs

---

## Step 8: Set Up MongoDB Atlas

1. Go to https://www.mongodb.com/products/platform/atlas-database
2. Create an account and a free (M0) cluster.
3. Under **Database Access**, create a database user — choose a username and a strong password, and save both somewhere safe.
4. Under **Network Access**, add your current IP. For a hackathon on shared/venue wifi where your IP may change, you can temporarily allow `0.0.0.0/0` (less secure, fine for a short event — remove it afterward).
5. Click **Connect** → **Drivers** → copy the connection string. It looks like:

```text
mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/?retryWrites=true&w=majority
```

6. Add a database name into the URI (this project uses `arthsaathi`):

```text
mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/arthsaathi?retryWrites=true&w=majority
```

If your password has special characters like `@ / # %`, either URL-encode them or regenerate a simpler password — this is the most common cause of connection failures.

You do not need to create collections manually — `backend/db.py` creates `users`, `transactions`, `merchant_categories`, and `conversations` (with indexes) automatically on first run. Scheme data comes from `backend/data/schemes.json` directly, not from Mongo, so there's no import step needed.

---

## Step 9: Get an LLM API Key

`backend/ai/config/llm.py` calls any OpenAI-compatible chat-completions endpoint — you only ever change three env vars to swap providers, never the code.

### Option A: Groq (default, fast, free tier)

1. Go to https://console.groq.com/
2. Sign up, then go to **API Keys** and create a new key.
3. You'll use it as:

```env
LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
LLM_API_KEY=your_groq_api_key
LLM_MODEL=qwen/qwen3-32b
```

### Option B: AWS Bedrock (if the hackathon provides it)

Bedrock's native API is not OpenAI-compatible, so ask the organizers if they're giving you a Bedrock **Access Gateway** or **OpenAI-compatible proxy URL** — if so, just drop that URL + key into the same three env vars. If you're given raw AWS credentials instead, that requires a small code change in `llm.py` to use `boto3`'s `bedrock-runtime` client — ask if you want that done when the time comes.

### Option C: Hugging Face — free Gemma 2B / Llama 3.2 (no code changes needed)

Hugging Face's Inference Providers router exposes an OpenAI-compatible endpoint, so it drops straight into the existing `llm.py` the same way Groq does.

1. Go to https://huggingface.co/ and create a free account.
2. Go to https://huggingface.co/settings/tokens and create a new **Access Token** (read access is enough).
3. If you want to use **Llama 3.2**, its model page (e.g. https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) requires you to click "request access" and accept Meta's license first — this is usually approved instantly, but do it a few minutes before you need it. Gemma models (e.g. `google/gemma-2-2b-it`) are ungated and work immediately.
4. Set the env vars:

```env
LLM_API_URL=https://router.huggingface.co/v1/chat/completions
LLM_API_KEY=your_huggingface_token
LLM_MODEL=google/gemma-2-2b-it
```

or for Llama 3.2:

```env
LLM_API_URL=https://router.huggingface.co/v1/chat/completions
LLM_API_KEY=your_huggingface_token
LLM_MODEL=meta-llama/Llama-3.2-3B-Instruct
```

Note: small models like these (2B–3B parameters) are noticeably weaker at following the strict JSON routing format `graph.py` expects (see `ROUTER_PROMPT` in `backend/ai/graph.py`). If you switch to one of these, test the intent router carefully — you may see more messages falling back to the `schemes` route than with Groq's larger model.

---

## Step 10: Get a Sarvam AI Key (Voice + Translation)

Used for transcribing Telegram voice notes and translating between English and Indian languages (`backend/voice.py`, `backend/language.py`).

1. Go to https://dashboard.sarvam.ai/
2. Sign up (new accounts get free credits).
3. Go to the API Keys section and create a key.
4. Save it as:

```env
SARVAM_API_KEY=your_sarvam_api_key
```

## Step 11: Optional API Keys

These enable extra features but the app runs fine without them.

**Mandi (crop price) lookups** — `backend/ai/mandi_prices.py`:

1. Go to https://data.gov.in/ and register for an account.
2. Search for a mandi/commodity price API resource and note its resource ID.
3. Go to your profile → generate an API key.

```env
DATA_GOV_MANDI_URL=https://api.data.gov.in/resource/<resource-id>
DATA_GOV_API_KEY=your_data_gov_api_key
```

**Scam link checking** — `backend/ai/agents/scam_agent.py`:

1. Go to https://console.cloud.google.com/
2. Create a project, enable the **Safe Browsing API**, and create an API key under Credentials.

```env
GOOGLE_SAFE_BROWSING_KEY=your_google_safe_browsing_key
```

**YouTube video links** (reserved for future use — not currently read by any agent, but kept here for when scheme videos are pulled live instead of from `schemes.json`):

1. Go to https://console.cloud.google.com/
2. Enable the **YouTube Data API v3** on your project and create an API key under Credentials.

```env
YOUTUBE_API_KEY=your_youtube_api_key
```

---

## Step 12: Create the Backend `.env`

Create the file:

```text
C:\arthsaathi\backend\.env
```

Minimum required to run:

```env
PORT=3000
MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/arthsaathi?retryWrites=true&w=majority
LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
LLM_API_KEY=your_llm_api_key
LLM_MODEL=qwen/qwen3-32b
SARVAM_API_KEY=your_sarvam_api_key
```

Full file with optional features:

```env
PORT=3000

MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/arthsaathi?retryWrites=true&w=majority

LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
LLM_API_KEY=your_llm_api_key
LLM_MODEL=qwen/qwen3-32b

SARVAM_API_KEY=your_sarvam_api_key

DATA_GOV_MANDI_URL=https://api.data.gov.in/resource/<resource-id>
DATA_GOV_API_KEY=your_data_gov_api_key

GOOGLE_SAFE_BROWSING_KEY=your_google_safe_browsing_key

YOUTUBE_API_KEY=your_youtube_api_key
```

## Step 13: Create the Telegram Bot

1. Open Telegram, search for `@BotFather`.
2. Send `/start`, then `/newbot`.
3. Give it a display name (e.g. `ArthSaathi`) and a username ending in `bot` (e.g. `arthsaathi_test_bot`).
4. BotFather replies with a token like `1234567890:AAExampleTokenHere`. Keep it private.

## Step 14: Create the Bot `.env`

Create the file:

```text
C:\arthsaathi\bot\.env
```

```env
BOT_TOKEN=your_telegram_bot_token
BACKEND_URL=http://localhost:3000
VOICE_TIMEOUT=600
```

---

## Step 15: Run the Backend

Terminal 1:

Git Bash:

```bash
cd /c/arthsaathi
source .venv/Scripts/activate
cd backend
python app.py
```

PowerShell:

```powershell
cd C:\arthsaathi
.\.venv\Scripts\Activate.ps1
cd backend
python app.py
```

It should print that it's serving on `http://0.0.0.0:3000`. Test it from another terminal:

Git Bash:

```bash
curl -X POST http://localhost:3000/chat \
  -H "Content-Type: application/json" \
  -d '{"telegramId":"test-user","username":"test","firstName":"Test","message":"/start"}'
```

PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:3000/chat -ContentType "application/json" -Body '{"telegramId":"test-user","username":"test","firstName":"Test","message":"/start"}'
```

A JSON reply means the backend, Mongo, and LLM key are all working.

## Step 16: Run the Telegram Bot

Terminal 2 (keep Terminal 1 running):

Git Bash:

```bash
cd /c/arthsaathi
source .venv/Scripts/activate
cd bot
python app.py
```

PowerShell:

```powershell
cd C:\arthsaathi
.\.venv\Scripts\Activate.ps1
cd bot
python app.py
```

Expected: `[BOT] ArthSaathi bot is running...`

Open Telegram, search for your bot's username, and send `/start`.

---

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Required | Purpose |
| --- | --- | --- |
| `PORT` | No | Backend port. Defaults to `3000`. |
| `MONGODB_URI` | Yes | MongoDB connection string, must include `/arthsaathi`. |
| `LLM_API_URL` | No | OpenAI-compatible chat completions URL. Defaults to Groq. |
| `LLM_API_KEY` | Yes for AI replies | API key for the LLM provider. |
| `LLM_MODEL` | No | Model name. Defaults to `qwen/qwen3-32b`. |
| `SARVAM_API_KEY` | Yes for voice + non-English chat | Sarvam AI key — powers voice transcription and translation. |
| `DATA_GOV_MANDI_URL` | For mandi prices | Data.gov.in mandi API endpoint. |
| `DATA_GOV_API_KEY` | For mandi prices | Data.gov.in API key. |
| `GOOGLE_SAFE_BROWSING_KEY` | Optional | Improves scam URL checking. |
| `YOUTUBE_API_KEY` | Optional | Not read by any agent yet — reserved for pulling scheme videos live instead of from `schemes.json`. |

### Bot (`bot/.env`)

| Variable | Required | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Telegram bot token from BotFather. |
| `BACKEND_URL` | Yes | Backend URL, usually `http://localhost:3000`. |
| `VOICE_TIMEOUT` | No | Timeout (seconds) for voice note processing. Defaults to `600`. |

---

## Common Problems

### `ModuleNotFoundError`

The virtual environment isn't active, or packages weren't installed into it.

Git Bash:

```bash
cd /c/arthsaathi
source .venv/Scripts/activate
python -m pip install -r backend/requirements.txt
python -m pip install -r bot/requirements.txt
```

PowerShell:

```powershell
cd C:\arthsaathi
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pip install -r bot\requirements.txt
```

Also make sure you `cd` into `backend` (or `bot`) before running `python app.py` — both scripts assume they're run from their own folder.

### MongoDB connection error

Check:

- `MONGODB_URI` exists in `backend\.env` and includes `/arthsaathi`.
- Atlas username/password are correct (regenerate the password if it has special characters).
- Your current IP is allowed under Atlas → Network Access.

### Telegram bot does not reply

Check:

- Both terminals (backend and bot) are still running.
- `BOT_TOKEN` is correct and `BACKEND_URL=http://localhost:3000`.
- No other copy of the bot is running elsewhere with the same token — Telegram only allows one active poller per bot token, and a second one will silently fail or throw a conflict error.

### LLM errors / no reply text

- Confirm `LLM_API_KEY` is set and valid for whichever provider you're using.
- If you just switched to Hugging Face and requests fail, double-check you accepted the model's license (Llama) or that the model ID is spelled exactly as on its Hugging Face page.
- Check the backend terminal output — `llm.py` prints the raw error on failure.

### Voice notes fail or reply with "could not understand"

Voice transcription runs entirely through Sarvam's API — check `SARVAM_API_KEY` is set and that the account still has credits at https://dashboard.sarvam.ai/.

### Port already in use

Change the backend port in `backend/.env`:

```env
PORT=3001
```

And update `bot/.env` to match:

```env
BACKEND_URL=http://localhost:3001
```

---

## Daily Startup Checklist

1. Open VS Code → open folder `C:\arthsaathi`.
2. Terminal 1 — backend:

Git Bash:

```bash
source .venv/Scripts/activate
cd backend
python app.py
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python app.py
```

3. Terminal 2 — bot:

Git Bash:

```bash
source .venv/Scripts/activate
cd bot
python app.py
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
cd bot
python app.py
```

4. Open Telegram, send `/start` to your bot.
