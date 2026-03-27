#!/usr/bin/env python3
# /// script
# dependencies = [
#   "packaging",
#   "requests",
# ]
# ///

import argparse
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

import requests
from packaging.version import InvalidVersion, Version

# Constants
REGISTRY_API = "https://registry.nextflow.io/api/v1/plugins"
DEFAULT_PLUGINS = ["nf-co2footprint", "nf-hello", "nf-prov", "nf-schema", "nf-tower", "nf-wave"]
DEFAULT_OUTDIR = "./nxf-plugin-cache"
DEFAULT_LIMIT = 5

def get_args():
    parser = argparse.ArgumentParser(description="🐿️ nf-plugin-hoarder: Cache Nextflow plugins for offline use.")
    parser.add_argument("-p", "--plugins", nargs="+", default=DEFAULT_PLUGINS,
                        help=f"Plugin IDs (default: {' '.join(DEFAULT_PLUGINS)})")
    parser.add_argument("-o", "--outdir", default=DEFAULT_OUTDIR,
                        help=f"Installation directory (default: {DEFAULT_OUTDIR})")
    parser.add_argument("-n", "--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Latest versions to keep per plugin (default: {DEFAULT_LIMIT})")
    parser.add_argument("-a", "--archive", action="store_true", help="Create a .tar.gz archive")
    parser.add_argument("-c", "--clean", action="store_true",
                        help="Remove the outdir after successful archiving (requires -a)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    return parser.parse_args()

def fetch_plugin_metadata(plugin_id):
    """Fetch all releases for a specific plugin from the registry."""
    url = f"{REGISTRY_API}/{plugin_id}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # The API returns {'plugin': {'id': '...', 'releases': [...]}}
    data = response.json()
    plugin_data = data.get("plugin", {})
    return plugin_data.get("releases", [])

def hoard():
    args = get_args()
    plugin_dir = Path(args.outdir).resolve()

    print("\n🐿️  nf-plugin-hoarder")
    print("=" * 40)
    print(f"Target: {plugin_dir}")
    if args.dry_run:
        print("--- DRY RUN MODE ---")
    print("=" * 40)

    if args.clean and not args.archive:
        print("⚠️  Warning: --clean requires --archive. Folder will not be deleted.")

    if not plugin_dir.exists() and not args.dry_run:
        plugin_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["NXF_PLUGINS_DIR"] = str(plugin_dir)

    for plugin_id in args.plugins:
        print(f"🔍 Checking: {plugin_id}")
        try:
            releases = fetch_plugin_metadata(plugin_id)

            if not releases:
                print("  ⚠️  No releases found.")
                continue

            # Keep invalid/non-PEP440 versions from crashing the sort.
            # Valid versions are ordered semantically first; invalid ones follow in text order.
            invalid_versions = []
            valid_rels = []

            for release in releases:
                version_str = release.get("version", "")
                try:
                    valid_rels.append((Version(version_str), release))
                except InvalidVersion:
                    invalid_versions.append(version_str)

            sorted_valid_rels = [release for _, release in sorted(valid_rels, key=lambda item: item[0], reverse=True)]

            if invalid_versions:
                unique_invalid = sorted(set(invalid_versions))
                print(f"Warning: Plugin ' {plugin_id}' contains non-PEP440 versions: {', '.join(unique_invalid)}")


            for rel in sorted_valid_rels[: args.limit]:
                version = rel.get("version")

                # Nextflow expects: <outdir>/<plugin>-<version>/MANIFEST.MF
                target_plugin_path = plugin_dir / f"{plugin_id}-{version}"
                
                if target_plugin_path.exists():
                    print(f"  ✅ {version} cached.")
                    continue

                cmd = ["nextflow", "plugin", "install", f"{plugin_id}@{version}"]
                if args.dry_run:
                    print(f"  [DRY-RUN] {' '.join(cmd)}")
                    continue

                print(f"  > {plugin_id}@{version}")
                subprocess.run(cmd, env=env, check=True, stdout=subprocess.DEVNULL)

        except Exception as e:
            print(f"  ❌ Error fetching {plugin_id}: {e}")

    # Archiving logic
    archive_success = False
    if args.archive and not args.dry_run:
        timestamp = datetime.now().strftime("%Y%m%d")
        archive_name = f"nxf-plugins-offline-{timestamp}.tar.gz"
        print(f"\n📦 Archiving to {archive_name}...")
        try:
            with tarfile.open(archive_name, "w:gz") as tar:
                # arcname ensures we don't store absolute system paths in the tar
                tar.add(plugin_dir, arcname=plugin_dir.name)
            print(f"✨ Successfully archived: {Path(archive_name).resolve()}")
            archive_success = True
        except Exception as e:
            print(f"❌ Error during archiving: {e}")

    if args.clean and archive_success:
        print(f"🧹 Cleaning up: Removing {plugin_dir}")
        shutil.rmtree(plugin_dir)

    print("\n🏁 Done!")

if __name__ == "__main__":
    try:
        hoard()
    except KeyboardInterrupt:
        print("\n\nStopped by user. See you later, hoarder!")
        sys.exit(130)