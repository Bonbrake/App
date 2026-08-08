#!/usr/bin/env python3
"""
ComfyUI Auto-Fix Monitor for Hermes
Watches for new error files and routes them to Hermes for auto-fixing.
This script should be run as a separate process or cron job.
"""
import json
import os
import time
import sys
from pathlib import Path

LOG_DIR = os.path.normpath(os.path.expanduser(r"~/Logs"))
ERROR_QUEUE_FILE = os.path.join(LOG_DIR, "ComfyUI_Error_Queue.json")

def process_error_queue():
    """Check for new errors and report them to Hermes"""
    if not os.path.exists(ERROR_QUEUE_FILE):
        return []
    
    try:
        with open(ERROR_QUEUE_FILE, "r") as f:
            queue = json.load(f)
    except:
        return []
    
    new_errors = []
    processed = []
    
    for error_file in queue:
        if not os.path.exists(error_file):
            processed.append(error_file)
            continue
            
        try:
            with open(error_file, "r") as f:
                error_data = json.load(f)
            
            if error_data.get("hermes_processed"):
                processed.append(error_file)
                continue
            
            # Mark as being processed
            error_data["hermes_processed"] = True
            error_data["status"] = "processing"
            with open(error_file, "w") as f:
                json.dump(error_data, f, indent=2)
            
            new_errors.append({
                "file": error_file,
                "error_type": error_data.get("error_type"),
                "error_message": error_data.get("error_message"),
                "traceback": error_data.get("traceback"),
                "context": error_data.get("context", "app"),
                "timestamp": error_data.get("timestamp")
            })
            processed.append(error_file)
            
        except Exception as e:
            processed.append(error_file)
            continue
    
    # Update queue
    remaining = [f for f in queue if f not in processed]
    with open(ERROR_QUEUE_FILE, "w") as f:
        json.dump(remaining, f)
    
    return new_errors

if __name__ == "__main__":
    errors = process_error_queue()
    if errors:
        for err in errors:
            print(f"NEW ERROR: {err['error_type']} - {err['error_message']}")
            print(f"Context: {err['context']}")
            print(f"Timestamp: {err['timestamp']}")
            print(f"File: {err['file']}")
            print("---")
        sys.exit(0)
    else:
        print("No new errors")
        sys.exit(0)