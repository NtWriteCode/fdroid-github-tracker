# 📱 F-Droid Auto-Updater

A super simple tool that builds your own personal "App Store" for Android. It automatically keeps your F-Droid repository up to date by watching your GitHub projects for new releases.

### 🌟 What does this do?
1.  **Watches GitHub**: It checks your favorite repos for new `.apk` releases.
2.  **Downloads Everything**: It grabs the new versions automatically.
3.  **Organizes the Store**: It creates all the files F-Droid needs to see your apps.
4.  **Signs your Store**: Uses your private key so your phone knows the apps are safe.

---

### 🚀 Quick Setup (The 5-Minute Guide)

#### 1. Prepare your Keys
You need an F-Droid signing key (`keystore.jks`). Put it in the folder where you run this.

#### 2. Create a `.env` file
Make a file named `.env` and put your key info inside:
```bash
FDROID_KEY_ALIAS=my-key-alias
FDROID_KEYSTORE_PASS=my-password
FDROID_KEY_PASS=my-password
```

#### 3. List your Repos
Edit `repos.json` and add the GitHub paths of the apps you want to track:
```json
[
  "NtWriteCode/Pockard",
  "NtWriteCode/gymness-tracker"
]
```

#### 4. Update your Domain
Open `config.yml` and change the `repo_url` to your actual domain (e.g., `https://fdroid.example.com/repo`).

#### 5. Run it!
Just run:
```bash
docker-compose up -d
```
The tool will now check for updates every 15 minutes!

---

### 🌐 Serving the Store
You need a web server (like Caddy) to show the files to your phone. Just point it to the `./data/repo/` folder.

**Caddy Example:**
```
fdroid.example.com {
    root * /path/to/fdroid-repo/data/repo
    file_server
}
```

### 📲 Add to your Phone
1. Open the **F-Droid** app.
2. Go to **Settings** -> **Repositories**.
3. Click the **+** button and enter your URL: `https://fdroid.example.com/repo`.
4. Your apps will now show up in F-Droid!

---

### 🛠️ Simple Troubleshooting
- **App doesn't update?** Make sure you increased the `versionCode` in your Android code (e.g., from `1` to `2`). F-Droid only sees the update if that number gets bigger!
- **Logs?** Run `docker-compose logs -f` to see what's happening.
