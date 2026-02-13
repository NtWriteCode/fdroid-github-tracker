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

## Troubleshooting

### F-Droid suggests older version instead of newer one

**Problem:** F-Droid shows version 0.0.1 as suggested, but 0.0.2 is available and should be suggested.

**Root Cause:** F-Droid uses `versionCode` (an integer) to determine which version is newer, NOT `versionName` (a string like "0.0.1" vs "0.0.2"). If version 0.0.2 has a lower or equal `versionCode` than 0.0.1, F-Droid will suggest 0.0.1.

**Debugging:**

1. On your server, run the debugging script:
   ```bash
   docker-compose exec fdroid-updater python3 /app/debug_version_codes.py <package_name>
   ```
   
   Or if running locally:
   ```bash
   python3 debug_version_codes.py <package_name> /data/repo /data/metadata
   ```

2. The script will show:
   - Version codes and names for all APKs
   - Which version F-Droid is suggesting
   - Whether version codes are in the correct order

**Solution:**

1. Check your app's `build.gradle` (Android) or `build.gradle.kts`:
   ```gradle
   android {
       defaultConfig {
           versionCode 1  // ← This must be INCREMENTED for each release
           versionName "0.0.1"
       }
   }
   ```

2. For version 0.0.2, make sure:
   ```gradle
   versionCode 2  // Must be > 1
   versionName "0.0.2"
   ```

3. Rebuild and release your APK with the correct version code

4. The F-Droid repo will automatically pick up the new version on the next poll

**Common Mistakes:**
- Using the same `versionCode` for different releases
- Decreasing `versionCode` (e.g., 0.0.2 has `versionCode 1`, 0.0.1 had `versionCode 2`)
- Not incrementing `versionCode` when only `versionName` changes

## Notes

- APKs are downloaded from GitHub Releases (must be public)
- Only the latest release per repo is tracked
- Old APKs are kept (manual cleanup if needed)
- Index is signed with your keystore
