#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
import urllib.error
import subprocess
import time
import logging
import shutil
import traceback
from pathlib import Path

# Third-party imports
try:
    import yaml
except ImportError:
    yaml = None

# Handle Androguard version differences
try:
    from androguard.core.apk import APK
    from androguard.util import set_log
    set_log("ERROR")
except ImportError:
    sys.exit("Androguard is required but not installed.")
    APK = None

def log(message):
    print(f"[{message}]", flush=True)

def fetch_apks():
    """Fetch APKs from GitHub releases"""
    repos_file = Path('/app/config/repos.json')
    if not repos_file.exists():
        log("ERROR: repos.json not found")
        return False, []
    
    with open(repos_file) as f:
        repos = json.load(f)
    
    repo_dir = Path('/data/repo')
    repo_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = False
    repo_package_map = {}
    
    # Load existing map if available
    map_file = Path('/data/repo_package_map.json')
    if map_file.exists():
        try:
            with open(map_file, 'r') as f:
                repo_package_map = json.load(f)
        except Exception:
            pass

    for repo in repos:
        log(f"Checking {repo}...")
        
        try:
            # Get latest release from GitHub API
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'F-Droid-Updater'
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
            
            # Download APKs
            for asset in data.get('assets', []):
                if not asset['name'].endswith('.apk'):
                    continue
                
                filename = asset['name']
                download_url = asset['browser_download_url']
                target_path = repo_dir / filename
                
                if target_path.exists():
                    log(f"  {filename} already exists, skipping")
                else:
                    log(f"  Downloading {filename}...")
                    urllib.request.urlretrieve(download_url, target_path)
                    log(f"  Downloaded {filename}")
                    downloaded = True
                
                # Extract package name for mapping if needed
                if repo not in repo_package_map and target_path.exists() and APK:
                    try:
                        apk = APK(str(target_path))
                        package_name = apk.get_package()
                        repo_package_map[repo] = package_name
                        log(f"  Mapped {repo} to {package_name}")
                    except Exception as e:
                        log(f"  WARNING: Failed to extract package name from {filename}: {e}")
                
        except urllib.error.HTTPError as e:
            log(f"ERROR: Failed to fetch {repo}: HTTP {e.code}")
        except Exception as e:
            log(f"ERROR: Failed to process {repo}: {e}")
            traceback.print_exc()

    # Save mapping
    try:
        with open(map_file, 'w') as f:
            json.dump(repo_package_map, f)
    except Exception as e:
        log(f"WARNING: Failed to save repo map: {e}")
    
    return downloaded, repos

def fetch_fastlane_metadata(repos):
    """Fetch fastlane metadata (descriptions, screenshots, etc) from app repos"""
    for repo in repos:
        log(f"Fetching metadata for {repo}...")
        owner, repo_name = repo.split('/')
        
        # Try both main and master branches
        for branch in ['main', 'master']:
            base_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{branch}/fastlane/metadata/android/en-US"
            
            try:
                # Check for existence via title.txt
                title_url = f"{base_url}/title.txt"
                req = urllib.request.Request(title_url, headers={'User-Agent': 'F-Droid-Updater'})
                
                with urllib.request.urlopen(req) as response:
                    title = response.read().decode('utf-8').strip()
                
                log(f"  Found fastlane metadata on {branch} branch")
                
                temp_metadata = Path(f'/data/.temp_metadata_{owner}_{repo_name}')
                temp_metadata.mkdir(parents=True, exist_ok=True)
                
                # Dictionary of file downloads
                downloads = {
                    'title.txt': f"{base_url}/title.txt",
                    'short_description.txt': f"{base_url}/short_description.txt",
                    'full_description.txt': f"{base_url}/full_description.txt",
                    'icon.png': f"{base_url}/images/icon.png"
                }

                # Fetch basic files
                for name, url in downloads.items():
                    try:
                        if name == 'title.txt': # Already fetched content, just write it
                             (temp_metadata / name).write_text(title)
                             log(f"    ✓ {name}")
                             continue

                        urllib.request.urlretrieve(url, temp_metadata / name)
                        log(f"    ✓ {name}")
                    except Exception:
                        pass # Optional files
                
                # Fetch screenshots
                screenshots_dir = temp_metadata / 'phoneScreenshots'
                screenshots_dir.mkdir(exist_ok=True)
                
                for i in range(1, 9):
                    try:
                        screenshot_url = f"{base_url}/images/phoneScreenshots/{i}.png"
                        urllib.request.urlretrieve(screenshot_url, screenshots_dir / f"{i}.png")
                        log(f"    ✓ screenshot {i}.png")
                    except:
                        break
                
                break # Success
                
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    log(f"  ERROR: HTTP {e.code}")
            except Exception as e:
                log(f"  ERROR: {e}")
                
        else:
            log(f"  No fastlane metadata found")

def apply_fastlane_metadata():
    """Apply fetched fastlane metadata to F-Droid metadata files"""
    metadata_dir = Path('/data/metadata')
    
    if not yaml:
        log("WARNING: PyYAML not installed, skipping metadata application")
        return

    # Load repo mapping
    repo_package_map = {}
    map_file = Path('/data/repo_package_map.json')
    if map_file.exists():
        try:
            with open(map_file, 'r') as f:
                repo_package_map = json.load(f)
        except Exception:
            pass
    
    for temp_dir in Path('/data').glob('.temp_metadata_*'):
        dir_name = temp_dir.name.replace('.temp_metadata_', '')
        
        # Match matches dir_name (Owner_Repo) to package_id
        matched_package = None
        for repo_slug, package_id in repo_package_map.items():
            expected_suffix = repo_slug.replace('/', '_')
            if dir_name == expected_suffix:
                matched_package = package_id
                break
        
        if not matched_package:
            log(f"WARNING: Could not match temp dir {dir_name} to a package ID. Skipping.")
            continue
            
        log(f"Applying metadata for {matched_package}...")
        yml_file = metadata_dir / f"{matched_package}.yml"
        
        if not yml_file.exists():
            log(f"  WARNING: Metadata file {yml_file} not found")
            continue

        try:
            with open(yml_file, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            # Update fields
            for filename, field in [
                ('title.txt', 'Name'),
                ('short_description.txt', 'Summary'),
                ('full_description.txt', 'Description')
            ]:
                if (temp_dir / filename).exists():
                    data[field] = (temp_dir / filename).read_text().strip()
            
            # Add repo-based metadata from user request
            if repo_slug:
                owner = repo_slug.split('/')[0]
                data['AuthorName'] = owner
                data['SourceCode'] = f"https://github.com/{repo_slug}"
                data['WebSite'] = f"https://github.com/{repo_slug}"
                data['IssueTracker'] = f"https://github.com/{repo_slug}/issues"
            
            with open(yml_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            # Copy resources
            package_locale_dir = metadata_dir / matched_package / 'en-US'
            package_locale_dir.mkdir(parents=True, exist_ok=True)
            
            if (temp_dir / 'icon.png').exists():
                shutil.copy(temp_dir / 'icon.png', package_locale_dir / 'icon.png')
            
            screenshots_src = temp_dir / 'phoneScreenshots'
            if screenshots_src.exists():
                screenshots_dst = package_locale_dir / 'phoneScreenshots'
                screenshots_dst.mkdir(exist_ok=True)
                for screenshot in screenshots_src.glob('*.png'):
                    shutil.copy(screenshot, screenshots_dst / screenshot.name)
            
            log(f"  Applied metadata to {matched_package}")
            
        except Exception as e:
            log(f"  ERROR applying metadata: {e}")
            traceback.print_exc()
            continue
    
    # Cleanup
    for temp_dir in Path('/data').glob('.temp_metadata_*'):
        shutil.rmtree(temp_dir, ignore_errors=True)

def copy_resources():
    """Copy entire directory tree from config/resources/ to repo/"""
    resources_dir = Path('/app/config/resources')
    data_dir = Path('/data')
    
    if not resources_dir.exists():
        return
        
    log("Copying resources...")
    # Copy entire directory tree
    for item in resources_dir.rglob('*'):
        if item.is_file():
            rel_path = item.relative_to(resources_dir)
            target = data_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(item, target)
            log(f"  Copied {item} -> {target}")

    log("Setting permissions...")
    subprocess.run(['chmod', '-R', 'a+r', '/data'])

def run_fdroid_update(sign=True):
    """Run fdroid update, optionally signing"""
    os.chdir('/data')
    
    # Copy config if not present
    config_src = Path('/app/config/config.yml')
    config_dst = Path('/data/config.yml')
    if not config_dst.exists() and config_src.exists():
        shutil.copy(config_src, config_dst)
    
    if not config_dst.exists():
        log("ERROR: config.yml not found, cannot proceed with update")
        return

    os.chmod('config.yml', 0o600)
    
    # Proactively clean up any left-over temp config from previous crashed runs
    with open('config.yml', 'r') as f:
        lines = f.readlines()
    if any('--- TEMPORARY KEYSTORE CONFIG' in line for line in lines):
        log("Cleaning up left-over temporary config from previous run...")
        with open('config.yml', 'w') as f:
            for line in lines:
                if '--- TEMPORARY KEYSTORE CONFIG' in line:
                    break
                f.write(line)

    # Read config again to check for existing keys
    with open('config.yml', 'r') as f:
        config_lines = f.readlines()
    
    # Check if keystore is already configured in the base config
    has_keystore = any(line.strip().startswith('keystore:') for line in config_lines)
    
    added_config = False
    if not has_keystore:
        keystore_config = f"""
# --- TEMPORARY KEYSTORE CONFIG (AUTO-GENERATED) ---
keystore: /app/config/keystore.jks
repo_keyalias: {os.environ.get('FDROID_KEY_ALIAS', '')}
keystorepass: {os.environ.get('FDROID_KEYSTORE_PASS', '')}
keypass: {os.environ.get('FDROID_KEY_PASS', '')}
"""
        with open('config.yml', 'a') as f:
            f.write(keystore_config)
        added_config = True
    
    try:
        log("Running fdroid update...")
        subprocess.run(['fdroid', 'update', '-q', '--create-metadata', '--pretty'], check=True)
        
        if sign:
            log("Signing index...")
            subprocess.run(['fdroid', 'signindex', '-q'], check=True)
            log("F-Droid index signed and ready!")
            
    finally:
        if added_config:
            # Remove temporary keystore config using the marker
            with open('config.yml', 'r') as f:
                lines = f.readlines()
            with open('config.yml', 'w') as f:
                for line in lines:
                    if '--- TEMPORARY KEYSTORE CONFIG' in line:
                        break
                    f.write(line)

def main():
    log("Starting F-Droid updater service...")
    
    try:
        poll_interval = int(os.environ.get('POLL_INTERVAL', 900))
    except (ValueError, TypeError):
        poll_interval = 900
    
    log(f"Poll interval set to {poll_interval} seconds")
    
    while True:
        try:
            log("Starting update check...")
            downloaded, repos = fetch_apks()
            
            if downloaded:
                log("New APKs found. Starting Two-Pass Update Process...")
                
                # Fetch fastlane metadata
                fetch_fastlane_metadata(repos)
                
                # Copy resources
                copy_resources()
                
                # PASS 1: Generate Skeletons
                # We don't sign yet, just generate the YAML structure
                log("--- Pass 1: Generating metadata skeletons ---")
                run_fdroid_update(sign=False)
                
                # Apply metadata to the skeletons
                apply_fastlane_metadata()
                
                # PASS 2: Build Final Index
                # Now we build the index using the patched metadata and sign it
                log("--- Pass 2: Building final index ---")
                run_fdroid_update(sign=True)
                
            else:
                log("No new APKs found.")
                
            log("Update check complete.")
            
        except Exception as e:
            log(f"ERROR: Main loop crashed: {e}")
            traceback.print_exc()
            
        log(f"Sleeping for {poll_interval} seconds...")
        time.sleep(poll_interval)

if __name__ == '__main__':
    main()
