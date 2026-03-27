# /// script
# dependencies = [
#   "packaging",
# ]
# ///

#!/usr/bin/env python3
import json
import urllib.request
import argparse
import os
import subprocess
import sys
import tarfile
import shutil
from datetime import datetime

# Attempt to import packaging.version
try:
    from packaging.version import InvalidVersion, Version
except ImportError:
    print("Error: 'packaging' library missing. Use 'uv run nf_plugin_hoarder.py' to auto-install.")
    sys.exit(1)

PLUGINS_URL = "https://raw.githubusercontent.com/nextflow-io/plugins/main/plugins.json"
DEFAULT_PLUGINS = ["nf-co2footprint","nf-hello", "nf-prov", "nf-schema", "nf-tower","nf-wave"]

def get_args():
    parser = argparse.ArgumentParser(description="Cache Nextflow plugins for offline use.")
    parser.add_argument("-p", "--plugins", nargs="+", default=DEFAULT_PLUGINS,
                        help=f"Plugin IDs (default: {' '.join(DEFAULT_PLUGINS)})")
    parser.add_argument("-o", "--outdir", default="./nxf-plugin-cache",
                        help="Installation directory (default: ./nxf-plugin-cache)")
    parser.add_argument("-n", "--limit", type=int, default=5,
                        help="Latest versions to keep (default: 5)")
    parser.add_argument("-a", "--archive", action="store_true",
                        help="Create a .tar.gz archive")
    parser.add_argument("-c", "--clean", action="store_true",
                        help="Remove the outdir after successful archiving (requires -a)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    return parser.parse_args()

def main():
    args = get_args()
    plugin_dir = os.path.abspath(args.outdir)

    print("🐿️ nf-plugin-hoarder")
    print("----------------------------------------")
    print("Fetching and caching Nextflow plugins...")
    print("----------------------------------------")
    
    if args.clean and not args.archive:
        print("Warning: --clean was specified without --archive. The folder will NOT be deleted for safety.")

    # 1. Prepare Directory
    if not os.path.exists(plugin_dir) and not args.dry_run:
        os.makedirs(plugin_dir, exist_ok=True)
    
    # 2. Fetch Index
    try:
        print("### Fetching plugin index...")
        with urllib.request.urlopen(PLUGINS_URL) as response:
            plugins_data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # 3. Filter & Sort
    targets = []
    for plugin in plugins_data:
        if plugin.get("id") in args.plugins:
            # Keep invalid/non-PEP440 versions from crashing the sort.
            # Valid versions are ordered semantically first; invalid ones follow in text order.
            invalid_versions = []
            valid_rels = []
            invalid_rels = []

            for release in plugin.get("releases", []):
                version_str = release.get("version", "")
                try:
                    valid_rels.append((Version(version_str), release))
                except InvalidVersion:
                    invalid_versions.append(version_str)
                    invalid_rels.append(release)

            sorted_valid_rels = [release for _, release in sorted(valid_rels, key=lambda item: item[0], reverse=True)]
            sorted_invalid_rels = sorted(invalid_rels, key=lambda release: release.get("version", ""), reverse=True)
            sorted_rels = sorted_valid_rels + sorted_invalid_rels

            if invalid_versions:
                unique_invalid = sorted(set(invalid_versions))
                print(f"Warning: Plugin '{plugin.get('id')}' contains non-PEP440 versions: {', '.join(unique_invalid)}")

            for rel in sorted_rels[:args.limit]:
                targets.append((plugin.get("id"), rel['version']))

    if not targets:
        print("No matching plugins found.")
        return

    # 4. Install
    env = os.environ.copy()
    env["NXF_PLUGINS_DIR"] = plugin_dir
    print(f"### Installing to: {plugin_dir}")

    for p_id, version in targets:
        cmd = ["nextflow", "plugin", "install", f"{p_id}@{version}"]
        if args.dry_run:
            print(f"[DRY-RUN] {' '.join(cmd)}")
        else:
            print(f"  > {p_id}@{version}")
            subprocess.run(cmd, env=env, check=True, stdout=subprocess.DEVNULL)

    # 5. Archive and Clean
    archive_success = False
    if args.archive and not args.dry_run:
        timestamp = datetime.now().strftime("%Y%m%d")
        archive_name = f"nxf-plugins-offline-{timestamp}.tar.gz"
        print(f"### Archiving to {archive_name}...")
        try:
            with tarfile.open(archive_name, "w:gz") as tar:
                tar.add(plugin_dir, arcname=os.path.basename(plugin_dir))
            print(f"Successfully archived: {os.path.abspath(archive_name)}")
            archive_success = True
        except Exception as e:
            print(f"Error during archiving: {e}")

    if args.clean and archive_success:
        print(f"### Cleaning up: Removing {plugin_dir}")
        shutil.rmtree(plugin_dir)

    print("-" * 30 + "\nDone!")

if __name__ == "__main__":
    main()