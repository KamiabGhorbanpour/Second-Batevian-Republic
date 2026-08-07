# The Second Batavian Republic

A four-player collaborative/competitive cabinet game built with NiceGUI. Each player joins from a separate browser, claims one ministry, and submits two private decisions per round. The round resolves only after all eight decisions have been received.

## Run locally

1. Install Python 3.12.
2. Open a terminal in this folder.
3. Create a virtual environment: `python -m venv .venv`
4. Activate it:
   - Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Start the game: `python main.py`
7. Open `http://localhost:8080`.

Use four separate browser storage contexts to test all ministries on one computer—for example Firefox normal/private and Chrome normal/incognito.

## Deploy on Railway

1. Put this folder in a GitHub repository, or upload it as the root of a Railway service.
2. In Railway, create a new project and deploy the repository.
3. Generate a public domain under **Settings → Networking**.
4. Add a Railway Volume and mount it at `/data`.
5. Add these variables:
   - `DATABASE_PATH=/data/game.db`
   - `STORAGE_SECRET=` followed by a long random string
   - `NICEGUI_STORAGE_PATH=/data/nicegui`
6. Redeploy once after adding the Volume and variables.

Railway supplies `PORT` automatically. The included `railway.json` starts the NiceGUI server on that port and uses `/health` for health checks.

The Volume is strongly recommended: without it, active rooms and remembered browser identities disappear whenever Railway restarts or redeploys the service. Keep the service at one replica while it uses SQLite.
