#!/usr/bin/env python3
"""
DEPRECATED.

This script used to overwrite my-large-data-vault/{main.py, src/utils/storage.py,
src/pipelines/process_media.py, src/pipelines/train_model.py} with hardcoded
copies of their source.

Those files are now the source of truth and have grown beyond what this
script's old snapshot contained (the API layer in api/ imports structured
functions from them — get_disk_usage, list_dir_tree, list_model_weights,
get_weight_detail, list_raw_videos, list_proxies, process_media_batch with
a progress_callback, etc.). Running the old version of this script would
silently revert all of that and break the API.

Edit the files in my-large-data-vault/src/ directly instead. This script is
kept only for history and does nothing.
"""
import sys


def update_vault():
    print(__doc__)
    print("No files were changed.")


if __name__ == "__main__":
    try:
        update_vault()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
