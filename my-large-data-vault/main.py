#!/usr/bin/env python3
"""
Main Entry Point for Data Pipeline & Asset Management.
"""
import sys
from src.utils.storage import check_disk_space, cleanup_scratch_dir
from src.pipelines.process_media import process_media_batch
from src.pipelines.train_model import run_model_pipeline

def main():
    print("=== Large Data Vault Pipeline Initialized ===")
    
    # 1. Storage check & scratch cleanup
    free_gb = check_disk_space(".")
    print(f"[INFO] Storage Check: {free_gb:.2f} GB available.")
    if free_gb < 10.0:
        print("[WARNING] Low disk space! Proceed with caution.")

    cleanup_scratch_dir()

    # 2. Run real processing pipelines
    process_media_batch()
    run_model_pipeline()

    print("\n=== All Vault Tasks Completed Successfully ===")

if __name__ == "__main__":
    main()
