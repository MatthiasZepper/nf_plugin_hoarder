#!/usr/bin/env python3
# /// script
# dependencies = [
#   "requests",
# ]
# ///

import argparse
import os
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path
import zipfile

import requests

REGISTRY_API = "https://registry.nextflow.io/api/v1/plugins"
DEFAULT_PLUGINS = ["nf-co2footprint", "nf-hello", "nf-prov", "nf-schema", "nf-tower", "nf-wave"]
DEFAULT_OUTDIR = "./nxf-plugin-cache"
DEFAULT_LIMIT = 5


def get_args():
    parser = argparse.ArgumentParser(description="Cache Nextflow plugins for offline use.")
    parser.add_argument(
        "-p",
        "--plugins",
        nargs="+",
        default=DEFAULT_PLUGINS,
        help=f"Plugin IDs (default: {' '.join(DEFAULT_PLUGINS)})",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        default=DEFAULT_OUTDIR,
        help=f"Installation directory (default: {DEFAULT_OUTDIR})",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Latest versions to keep (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument("-a", "--archive", action="store_true", help="Create a .tar.gz archive")
    parser.add_argument(
        "-c",
        "--clean",
        action="store_true",
        help="Remove the outdir after successful archiving (requires -a)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    return parser.parse_args()


def fetch_plugin_metadata(plugin_id):
    """Fetch all releases for a specific plugin from the registry."""
    params = {"plugins": plugin_id}
    response = requests.get(REGISTRY_API, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    for plugin in data.get("plugins", []):
        if plugin.get("id") == plugin_id:
            return plugin.get("releases", [])
    return []


def hoard():
    args = get_args()
    plugin_dir = Path(args.outdir).resolve()

    print("🐿️ nf-plugin-hoarder")
    print("----------------------------------------")
    print("Fetching and caching Nextflow plugins...")
    print("----------------------------------------")

    if args.clean and not args.archive:
        print("Warning: --clean was specified without --archive. The folder will NOT be deleted for safety.")

    if not plugin_dir.exists() and not args.dry_run:
        plugin_dir.mkdir(parents=True, exist_ok=True)

    for plugin_id in args.plugins:
        print(f"🔍 Checking registry for: {plugin_id}")
        try:
            releases = fetch_plugin_metadata(plugin_id)
            releases.sort(key=lambda item: item.get("date", ""), reverse=True)

            if not releases:
                print(f"  ⚠️  No releases found for {plugin_id}.")
                continue

            for rel in releases[: args.limit]:
                version = rel.get("version")
                download_url = rel.get("url")

                if not version or not download_url:
                    print(f"  ⚠️  Skipping malformed release entry for {plugin_id}.")
                    continue

                plugin_subdir = plugin_dir / f"{plugin_id}-{version}"
                if plugin_subdir.exists():
                    print(f"  ✅ {version} already cached.")
                    continue

                zip_path = Path(f"{plugin_subdir}.zip")
                print(f"  📥 Downloading {version}...")

                if args.dry_run:
                    print(f"  [DRY-RUN] GET {download_url}")
                    print(f"  [DRY-RUN] unzip {zip_path.name} -> {plugin_subdir}")
                    continue

                with requests.get(download_url, stream=True, timeout=60) as response:
                    response.raise_for_status()
                    with open(zip_path, "wb") as file_handle:
                        shutil.copyfileobj(response.raw, file_handle)

                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(plugin_subdir)
                os.remove(zip_path)

        except Exception as e:
            print(f"  ❌ Error fetching {plugin_id}: {e}")

    archive_success = False
    if args.archive and not args.dry_run:
        timestamp = datetime.now().strftime("%Y%m%d")
        archive_name = f"nxf-plugins-offline-{timestamp}.tar.gz"
        print(f"### Archiving to {archive_name}...")
        try:
            with tarfile.open(archive_name, "w:gz") as tar:
                tar.add(plugin_dir, arcname=plugin_dir.name)
            print(f"Successfully archived: {Path(archive_name).resolve()}")
            archive_success = True
        except Exception as e:
            print(f"Error during archiving: {e}")

    if args.clean and archive_success:
        print(f"### Cleaning up: Removing {plugin_dir}")
        shutil.rmtree(plugin_dir)

    if args.dry_run:
        print(f"\n✨ Dry-run complete! Target plugin directory would be: {plugin_dir}")
    else:
        print(f"\n✨ Hoarding complete! Plugins are in: {plugin_dir}")
    print("-" * 30 + "\nDone!")


if __name__ == "__main__":
    try:
        hoard()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)