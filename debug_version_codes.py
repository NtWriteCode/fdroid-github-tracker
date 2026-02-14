#!/usr/bin/env python3
"""
Debug script to check version codes in APKs and F-Droid metadata.

This script helps identify why F-Droid might be suggesting an older version
instead of a newer one. F-Droid uses versionCode (integer) to determine
which version is newer, not versionName (string like "0.0.1" vs "0.0.2").

Usage:
    python3 debug_version_codes.py <package_name> [repo_dir] [metadata_dir]

Example:
    python3 debug_version_codes.py com.example.gymness /data/repo /data/metadata
"""

import sys
import json
from pathlib import Path

try:
    from androguard.core.apk import APK
    from androguard.util import set_log
    set_log("ERROR")
except ImportError:
    print("ERROR: Androguard is required. Install with: pip install androguard")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("WARNING: PyYAML not installed. Cannot read metadata YAML files.")
    yaml = None


def check_apk_version(apk_path):
    """Extract version information from an APK file."""
    try:
        apk = APK(str(apk_path))
        return {
            'package': apk.get_package(),
            'version_code': apk.get_androidversion_code(),
            'version_name': apk.get_androidversion_name(),
            'min_sdk': apk.get_min_sdk_version(),
            'target_sdk': apk.get_target_sdk_version(),
        }
    except Exception as e:
        return {'error': str(e)}


def check_index_file(repo_dir, package_name):
    """Check version information in F-Droid index files."""
    repo_dir = Path(repo_dir)
    results = {}
    
    # Check index-v1.json
    index_v1 = repo_dir / 'index-v1.json'
    if index_v1.exists():
        try:
            with open(index_v1, 'r') as f:
                data = json.load(f)
            
            packages = data.get('packages', {}).get(package_name, [])
            if packages:
                results['index-v1.json'] = []
                for pkg in packages:
                    results['index-v1.json'].append({
                        'apk_name': pkg.get('apkName'),
                        'version_code': pkg.get('versionCode'),
                        'version_name': pkg.get('versionName'),
                        'added': pkg.get('added'),
                    })
            else:
                results['index-v1.json'] = 'Package not found'
        except Exception as e:
            results['index-v1.json'] = {'error': str(e)}
    else:
        results['index-v1.json'] = 'File not found'
    
    # Check suggestedVersionCode in apps section
    if index_v1.exists():
        try:
            with open(index_v1, 'r') as f:
                data = json.load(f)
            
            apps = data.get('apps', [])
            for app in apps:
                if app.get('packageName') == package_name:
                    results['suggested_version_code'] = app.get('suggestedVersionCode')
                    results['app_last_updated'] = app.get('lastUpdated')
                    break
        except Exception as e:
            pass
    
    return results


def check_metadata_file(metadata_dir, package_name):
    """Check version information in metadata YAML file."""
    if not yaml:
        return {'error': 'PyYAML not installed'}
    
    metadata_dir = Path(metadata_dir)
    yml_file = metadata_dir / f"{package_name}.yml"
    
    if not yml_file.exists():
        return {'error': f'Metadata file not found: {yml_file}'}
    
    try:
        with open(yml_file, 'r') as f:
            data = yaml.safe_load(f) or {}
        
        return {
            'current_version_code': data.get('CurrentVersionCode'),
            'current_version': data.get('CurrentVersion'),
            'auto_update_mode': data.get('AutoUpdateMode'),
            'update_check_mode': data.get('UpdateCheckMode'),
        }
    except Exception as e:
        return {'error': str(e)}


def find_apks(repo_dir, package_name):
    """Find all APK files that might belong to this package."""
    repo_dir = Path(repo_dir)
    apks = []
    
    # Search for APKs in the repo directory
    for apk_file in repo_dir.glob('*.apk'):
        try:
            apk_info = check_apk_version(apk_file)
            if apk_info.get('package') == package_name:
                apks.append({
                    'path': str(apk_file),
                    'filename': apk_file.name,
                    **apk_info
                })
        except Exception:
            pass
    
    return apks


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    package_name = sys.argv[1]
    repo_dir = sys.argv[2] if len(sys.argv) > 2 else '/data/repo'
    metadata_dir = sys.argv[3] if len(sys.argv) > 3 else '/data/metadata'
    
    print(f"Debugging version codes for package: {package_name}")
    print(f"Repo directory: {repo_dir}")
    print(f"Metadata directory: {metadata_dir}")
    print("=" * 70)
    print()
    
    # Find and check APKs
    print("1. Checking APK files in repo directory...")
    print("-" * 70)
    apks = find_apks(repo_dir, package_name)
    
    if not apks:
        print(f"   No APKs found for package {package_name}")
        print("   Searching for any APK files...")
        repo_path = Path(repo_dir)
        all_apks = list(repo_path.glob('*.apk'))
        if all_apks:
            print(f"   Found {len(all_apks)} APK file(s), checking packages...")
            for apk_file in all_apks:
                try:
                    apk_info = check_apk_version(apk_file)
                    if 'package' in apk_info:
                        print(f"   - {apk_file.name}: {apk_info['package']} "
                              f"(versionCode: {apk_info.get('version_code')}, "
                              f"versionName: {apk_info.get('version_name')})")
                except Exception:
                    pass
    else:
        # Sort by version code
        apks.sort(key=lambda x: x.get('version_code', 0))
        
        for apk in apks:
            print(f"   APK: {apk['filename']}")
            if 'error' in apk:
                print(f"      ERROR: {apk['error']}")
            else:
                print(f"      Package: {apk['package']}")
                print(f"      Version Code: {apk['version_code']}")
                print(f"      Version Name: {apk['version_name']}")
                print(f"      Min SDK: {apk.get('min_sdk', 'N/A')}")
                print(f"      Target SDK: {apk.get('target_sdk', 'N/A')}")
            print()
        
        # Check if version codes are in correct order
        if len(apks) > 1:
            print("   Version Code Analysis:")
            for i in range(len(apks) - 1):
                vc1 = apks[i].get('version_code', 0)
                vc2 = apks[i + 1].get('version_code', 0)
                vn1 = apks[i].get('version_name', '')
                vn2 = apks[i + 1].get('version_name', '')
                
                if vc1 >= vc2:
                    print(f"      ⚠️  WARNING: {apks[i]['filename']} (v{vn1}, code={vc1}) "
                          f"has same or HIGHER version code than "
                          f"{apks[i+1]['filename']} (v{vn2}, code={vc2})")
                    print(f"         F-Droid will suggest the version with the HIGHEST version code.")
                else:
                    print(f"      ✓ {apks[i]['filename']} (code={vc1}) < "
                          f"{apks[i+1]['filename']} (code={vc2})")
    
    print()
    
    # Check index files
    print("2. Checking F-Droid index files...")
    print("-" * 70)
    index_info = check_index_file(repo_dir, package_name)
    
    if 'index-v1.json' in index_info:
        if isinstance(index_info['index-v1.json'], list):
            print("   Packages in index-v1.json:")
            for pkg in index_info['index-v1.json']:
                print(f"      - {pkg['apk_name']}")
                print(f"        Version Code: {pkg['version_code']}")
                print(f"        Version Name: {pkg['version_name']}")
                print(f"        Added: {pkg['added']}")
        else:
            print(f"   {index_info['index-v1.json']}")
    
    if 'suggested_version_code' in index_info:
        print(f"   Suggested Version Code: {index_info['suggested_version_code']}")
        if index_info['suggested_version_code'] == 2147483647:
            print("      ⚠️  WARNING: This is the maximum integer value (placeholder).")
            print("         F-Droid couldn't determine the correct version code.")
    
    print()
    
    # Check metadata file
    print("3. Checking metadata YAML file...")
    print("-" * 70)
    metadata_info = check_metadata_file(metadata_dir, package_name)
    
    if 'error' in metadata_info:
        print(f"   {metadata_info['error']}")
    else:
        print(f"   Current Version Code: {metadata_info.get('current_version_code', 'N/A')}")
        print(f"   Current Version: {metadata_info.get('current_version', 'N/A')}")
        print(f"   Auto Update Mode: {metadata_info.get('auto_update_mode', 'N/A')}")
        print(f"   Update Check Mode: {metadata_info.get('update_check_mode', 'N/A')}")
        
        if metadata_info.get('current_version_code') == 2147483647:
            print("      ⚠️  WARNING: CurrentVersionCode is set to maximum integer (placeholder).")
            print("         This might prevent F-Droid from suggesting the correct version.")
    
    print()
    print("=" * 70)
    print("DIAGNOSIS:")
    print()
    
    # Provide diagnosis
    if apks and len(apks) > 1:
        max_vc_apk = max(apks, key=lambda x: x.get('version_code', 0))
        suggested_vc = index_info.get('suggested_version_code')
        
        if suggested_vc and suggested_vc != 2147483647:
            suggested_apk = next((a for a in apks if a.get('version_code') == suggested_vc), None)
            if suggested_apk:
                print(f"F-Droid is suggesting: {suggested_apk['filename']} "
                      f"(versionCode: {suggested_apk['version_code']})")
            else:
                print(f"F-Droid suggests versionCode: {suggested_vc}, but no matching APK found")
        
        if max_vc_apk.get('version_code') != suggested_vc:
            print(f"Latest APK by versionCode: {max_vc_apk['filename']} "
                  f"(versionCode: {max_vc_apk['version_code']})")
            print()
            print("SOLUTION:")
            print("The version codes in your APKs might be incorrect.")
            print("Make sure that version 0.0.2 has a HIGHER versionCode than 0.0.1.")
            print("You can check this in your app's build.gradle or AndroidManifest.xml:")
            print("  - versionCode should be an integer (e.g., 1, 2, 3)")
            print("  - versionName is the string version (e.g., '0.0.1', '0.0.2')")
            print()
            print("After fixing version codes, rebuild your APKs and re-run 'fdroid update'.")


if __name__ == '__main__':
    main()
