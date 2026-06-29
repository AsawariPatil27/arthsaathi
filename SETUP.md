# ArthSaathi Setup Guide

This guide starts from an empty Windows desktop and gets the full project running:

- FastAPI backend in `backend/`
- Telegram polling bot in `bot/`
- MongoDB database
- AI/LLM API keys
- Optional voice, mandi price, YouTube, and scam-checking features

Commands are shown for both **Git Bash** and **PowerShell**. If you use Git Bash, prefer the Git Bash blocks.

## Project Folder Structure

```text
arthsaathi/
  backend/
    app.py                 FastAPI backend entry point
    db.py                  MongoDB connection and collections
    import_schemes.py      Imports scheme data into MongoDB
    requirements.txt       Backend Python packages
    data/
      schemes.json         Government scheme data
      rbi_registered.csv   RBI registered entity data for scam checks
    ai/
      graph.py             Routes user messages to the right AI feature
      config/
        llm.py             LLM API configuration
      agents/              Planner, tracker, scam, insights, and jargon agents
    uploads/               Temporary voice uploads during local runs
    charts/                Generated chart images
  bot/
    app.py                 Telegram bot entry point
    requirements.txt       Bot Python packages
  .venv/                   Local Python virtual environment
  .gitignore               Files Git should ignore
  SETUP.md                 This setup guide
```

Important files you create locally:

```text
backend/.env               Backend secrets and API keys
bot/.env                   Telegram bot token and backend URL
```

Do not commit `.env` files to GitHub.

## 1. Install Required Software

### Install VS Code

1. Go to https://code.visualstudio.com/
2. Download VS Code for Windows.
3. Install it.
4. During install, enable:
   - Add to PATH
   - Open with Code

### Install Python

1. Go to https://www.python.org/downloads/windows/
2. Install Python 3.11.
3. On the first installer screen, tick:
   - Add python.exe to PATH
4. After install, open Git Bash or PowerShell and check:

Git Bash:

```bash
python --version
python -m pip --version
```

PowerShell:

```powershell
python --version
python -m pip --version
```

Expected:

```text
Python 3.11.x
pip ...
```

### Install Git

1. Go to https://git-scm.com/download/win
2. Install Git with the default options.
3. Check:

Git Bash or PowerShell:

```bash
git --version
```

### Install VS Code Extensions

Open VS Code, then install these extensions:

- Python by Microsoft
- Pylance by Microsoft
- Python Debugger by Microsoft
- dotenv

Optional but useful:

- GitLens
- MongoDB for VS Code

## 2. Get The Project On Your Computer

If you already have the folder, open it in VS Code:

Git Bash:

```bash
cd /c
code arthsaathi
```

PowerShell:

```powershell
cd C:\
code arthsaathi
```

If you are starting fresh from GitHub:

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

Replace `<YOUR_GITHUB_REPO_URL>` with your real repository URL.

## 3. Create A Python Virtual Environment

From the project root:

Git Bash:

```bash
cd /c/arthsaathi
python -m venv .venv
```

PowerShell:

```powershell
cd C:\arthsaathi
python -m venv .venv
```

Activate it:

Git Bash:

```bash
source .venv/Scripts/activate
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once in PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

Git Bash:

```bash
source .venv/Scripts/activate
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

When active, your terminal should show `(.venv)`.

## 4. Install Python Packages

Upgrade pip:

Git Bash or PowerShell:

```bash
python -m pip install --upgrade pip
```

Install backend packages:

Git Bash:

```bash
python -m pip install -r backend/requirements.txt
```

PowerShell:

```powershell
python -m pip install -r backend\requirements.txt
```

Install bot packages:

Git Bash:

```bash
python -m pip install -r bot/requirements.txt
```

PowerShell:

```powershell
python -m pip install -r bot\requirements.txt
```

This project uses:

- `fastapi` and `uvicorn` for the backend server
- `pymongo` and `dnspython` for MongoDB
- `python-dotenv` for `.env` files
- `python-telegram-bot` for Telegram
- `requests` for HTTP API calls
- `faster-whisper` for voice note transcription
- `matplotlib` for generated charts
- `python-whois` and `rapidfuzz` for scam/link checks

## 5. Connect MongoDB

You can use MongoDB Atlas or local MongoDB. Atlas is easier for sharing and deployment.

### Option A: MongoDB Atlas

1. Go to https://www.mongodb.com/products/platform/atlas-database
2. Create an account.
3. Create a free cluster.
4. Create a database user:
   - Username: choose anything
   - Password: generate a strong password and save it
5. Go to Network Access.
6. Add your IP address.
   - For local testing, you can temporarily allow `0.0.0.0/0`, but this is less secure.
7. Click Connect.
8. Choose Drivers.
9. Copy the connection string.

Your connection string must include a database name after the cluster host:

```text
mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/arthsaathi?retryWrites=true&w=majority
```

Important:

- Replace `USERNAME`.
- Replace `PASSWORD`.
- Keep `/arthsaathi` in the URI.
- If your password contains special characters like `@`, `/`, `#`, `%`, encode them or create a simpler password.

### Option B: Local MongoDB

Install MongoDB Community Server from:

```text
https://www.mongodb.com/try/download/community
```

Then use:

```text
mongodb://localhost:27017/arthsaathi
```

## 6. Create The Backend `.env`

Create this file:

```text
C:\arthsaathi\backend\.env
```

Add:

```env
PORT=3000

MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/arthsaathi?retryWrites=true&w=majority

LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=qwen/qwen3-32b

DATA_GOV_MANDI_URL=https://api.data.gov.in/resource/<resource-id>
DATA_GOV_API_KEY=your_data_gov_api_key_here

GOOGLE_SAFE_BROWSING_KEY=your_google_safe_browsing_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here

WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

Minimum required for the backend:

```env
PORT=3000
MONGODB_URI=mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/arthsaathi?retryWrites=true&w=majority
LLM_API_KEY=your_llm_api_key_here
```

Optional variables:

- `DATA_GOV_MANDI_URL` and `DATA_GOV_API_KEY`: needed for mandi prices.
- `GOOGLE_SAFE_BROWSING_KEY`: improves scam URL checking.
- `YOUTUBE_API_KEY`: returns direct YouTube video links for schemes. Without it, the app falls back to YouTube search links.
- `WHISPER_*`: controls voice transcription model settings.

## 7. Get An LLM API Key

The current default backend is Groq-compatible:

```env
LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
LLM_MODEL=qwen/qwen3-32b
```

To use Groq:

1. Go to https://console.groq.com/
2. Create an API key.
3. Put it in:

```env
LLM_API_KEY=your_groq_api_key
```

You can also use another OpenAI-compatible chat-completions API by changing:

```env
LLM_API_URL=
LLM_API_KEY=
LLM_MODEL=
```

## 8. Create The Telegram Bot

1. Open Telegram.
2. Search for `@BotFather`.
3. Send:

```text
/start
```

4. Send:

```text
/newbot
```

5. BotFather will ask for:
   - Bot display name, for example `ArthSaathi`
   - Bot username, which must end in `bot`, for example `arthsaathi_test_bot`
6. BotFather will give you a bot token.

It looks like:

```text
1234567890:AAExampleTokenHere
```

Keep this private.

## 9. Create The Bot `.env`

Create this file:

```text
C:\arthsaathi\bot\.env
```

Add:

```env
BOT_TOKEN=your_telegram_bot_token_here
BACKEND_URL=http://localhost:3000
VOICE_TIMEOUT=600
```

Required:

```env
BOT_TOKEN=your_telegram_bot_token_here
BACKEND_URL=http://localhost:3000
```

## 10. Import Scheme Data Into MongoDB

The backend has government scheme data in:

```text
C:\arthsaathi\backend\data\schemes.json
```

After setting `backend\.env`, import it:

Git Bash:

```bash
cd /c/arthsaathi
source .venv/Scripts/activate
cd backend
python import_schemes.py
```

PowerShell:

```powershell
cd C:\arthsaathi
.\.venv\Scripts\Activate.ps1
cd backend
python import_schemes.py
```

Expected output:

```text
Imported <number> schemes
```

## 11. Run The Backend

Open a terminal:

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

The backend should run on:

```text
http://localhost:3000
```

You can test it in another terminal:

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

## 12. Run The Telegram Bot

Open a second terminal:

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

Expected output:

```text
[BOT] ArthSaathi bot is running...
```

Now open Telegram, search your bot username, and send:

```text
/start
```

## 13. How The Project Runs

You need two terminals:

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

Terminal 2:

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

Flow:

```text
Telegram user
  -> Telegram bot in bot/app.py
  -> FastAPI backend at http://localhost:3000
  -> MongoDB
  -> LLM / external APIs when needed
```

## 14. Environment Variables Reference

### Backend

| Variable | Required | Purpose |
| --- | --- | --- |
| `PORT` | No | Backend port. Defaults to `3000`. |
| `MONGODB_URI` | Yes | MongoDB connection string. Must include database name. |
| `LLM_API_URL` | No | OpenAI-compatible chat completions URL. Defaults to Groq. |
| `LLM_API_KEY` | Yes for AI replies | API key for the LLM provider. |
| `LLM_MODEL` | No | Model name. Defaults to `qwen/qwen3-32b`. |
| `DATA_GOV_MANDI_URL` | For mandi prices | Data.gov.in mandi API endpoint. |
| `DATA_GOV_API_KEY` | For mandi prices | Data.gov.in API key. |
| `GOOGLE_SAFE_BROWSING_KEY` | Optional | Checks unsafe URLs in scam detection. |
| `YOUTUBE_API_KEY` | Optional | Gets direct videos for scheme help. |
| `WHISPER_MODEL` | Optional | Voice transcription model. Defaults to `small`. |
| `WHISPER_DEVICE` | Optional | Use `cpu` unless you have GPU setup. |
| `WHISPER_COMPUTE_TYPE` | Optional | Use `int8` for CPU. |

### Bot

| Variable | Required | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Telegram bot token from BotFather. |
| `BACKEND_URL` | Yes | Backend URL, usually `http://localhost:3000`. |
| `VOICE_TIMEOUT` | No | Timeout for voice note processing. Defaults to `600`. |

## 15. Common Problems

### `ModuleNotFoundError`

Make sure the virtual environment is active and packages are installed:

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

Also run the backend from inside `backend`:

Git Bash:

```bash
cd /c/arthsaathi/backend
python app.py
```

PowerShell:

```powershell
cd C:\arthsaathi\backend
python app.py
```

Run the bot from inside `bot`:

Git Bash:

```bash
cd /c/arthsaathi/bot
python app.py
```

PowerShell:

```powershell
cd C:\arthsaathi\bot
python app.py
```

### MongoDB connection error

Check:

- `MONGODB_URI` exists in `backend\.env`.
- The URI contains `/arthsaathi`.
- Your Atlas username/password are correct.
- Your IP is allowed in Atlas Network Access.
- Your internet is working.

### Telegram bot does not reply

Check:

- Backend terminal is running.
- Bot terminal is running.
- `BOT_TOKEN` is correct.
- `BACKEND_URL=http://localhost:3000`.
- No old copy of the bot is already running elsewhere with the same token.

### Voice note is slow first time

The first voice request downloads/loads the Whisper model. This can take time.

Use these CPU-friendly settings:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

If audio decoding fails, install FFmpeg:

Git Bash or PowerShell:

```powershell
winget install Gyan.FFmpeg
```

Then restart Git Bash or PowerShell.

### Port already in use

Change backend port:

```env
PORT=3001
```

Then update bot:

```env
BACKEND_URL=http://localhost:3001
```

## 16. Daily Startup Checklist

1. Open VS Code.
2. Open folder `C:\arthsaathi`.
3. Open terminal 1:

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

4. Open terminal 2:

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

5. Open Telegram.
6. Send `/start` to your bot.
