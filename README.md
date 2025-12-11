# F-Droid Self-Hosted Repository

Self-hosted F-Droid repository that automatically polls GitHub releases and serves APKs.

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- Your own domain (e.g., `fdroid.example.com`)
- Caddy or any web server for serving static files
- F-Droid signing keystore

### 2. Setup

**Create `.env` file:**
```bash
FDROID_KEY_ALIAS=your-key-alias
FDROID_KEYSTORE_PASS=your-keystore-password
FDROID_KEY_PASS=your-key-password
```

**Add your keystore:**
```bash
cp /path/to/your/keystore.jks ./keystore.jks
```

**Edit `repos.json`** to list GitHub repos to track:
```json
[
  "username/repo1",
  "username/repo2"
]
```

**Update `config.yml`** if needed (domain is already set to `fdroid.example.com`).

### 3. Run with Docker Compose

**Option A: Use pre-built image from Docker Hub (recommended)**
```bash
docker-compose up -d
```

**Option B: Build locally**
```bash
# Modify docker-compose.yml to use 'build: .' instead of 'image:'
docker-compose up -d --build
```

The container will:
- Poll GitHub every 15 minutes for new releases
- Download APKs to `./data/repo/`
- Generate F-Droid index files
- Sign the index with your keystore

### 4. Configure Caddy

Point Caddy to serve `./data/repo` at your domain:

```
fdroid.example.com {
    root * /path/to/fdroid-repo/data/repo
    file_server
}
```

### 5. Add to F-Droid Client

In F-Droid app:
1. Settings → Repositories
2. Add repository: `https://fdroid.example.com/repo`

## Directory Structure

```
fdroid-repo/
├── docker-compose.yml      # Docker stack
├── Dockerfile              # Container definition
├── .env                    # Environment variables (create this)
├── config.yml              # F-Droid config
├── repos.json              # GitHub repos to track
├── keystore.jks            # Your signing key (add this)
├── scripts/
│   └── poll_and_update.sh  # Polling script
└── data/                   # Output directory (auto-created)
    └── repo/               # Serve this with Caddy
        ├── *.apk
        ├── index-v1.json
        └── icons/
```

## Configuration

**Poll interval:** Edit `POLL_INTERVAL` in `docker-compose.yml` (default: 900 seconds = 15 min)

**Logs:** View with `docker-compose logs -f`

**Manual update:** `docker-compose exec fdroid-updater /app/poll_and_update.sh`

## Notes

- APKs are downloaded from GitHub Releases (must be public)
- Only the latest release per repo is tracked
- Old APKs are kept (manual cleanup if needed)
- Index is signed with your keystore
