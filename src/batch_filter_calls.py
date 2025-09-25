#!/usr/bin/env python3
"""
Parallel call transcript filter - removes IVR-only files, keeps patient conversations.
Processes numeric subdirectories in parallel threads.
"""

import os
import json
import argparse
import shutil
import csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from glob import glob
import threading

IVR_MARKERS = [
    "thank you for calling",
    "please listen to all of the prompts",
    "if you are calling",
    "press 1", "press 2", "press 3", "press [pii]"
]

AGENT_MARKERS = [
    "how may i help",
    "diagnostics, this is",
    "wessler diagnostics", "wassler diagnostics", "wasler diagnostics",
    "waffler diagnostics", "lossler diagnostics", "bossler diagnostics"
]

PATIENT_MARKERS = [
    "i was just wondering", "i was wondering", "i need", "i have", "i'd like",
    "i want", "i'm calling", "can i", "do you have", "do you guys have",
    "any appointments available", "is there any appointment",
    "it doesn't matter", "it's a pelvic ultrasound", "my health number is",
    "i have to cancel", "i need to cancel", "am i calling the right",
    "i was told", "i'm under the impression", "uh", "um", "yeah", "yep"
]

def has_any(text, phrases):
    return any(p in text for p in phrases)

def count_speakers(segments):
    try:
        return len(set(s.get("speaker_label") for s in segments))
    except:
        return 0

def decide_status(transcript, segments):
    t = (transcript or "").lower()
    has_agent = has_any(t, AGENT_MARKERS)
    has_patient = has_any(t, PATIENT_MARKERS)
    
    # IVR-only quick reject
    ivr_only = ("thank you for calling" in t and "if you are calling" in t 
                and not has_agent and not has_patient)
    if ivr_only:
        return "NO_PATIENT", has_agent, has_patient, count_speakers(segments), "IVR-only markers"
    
    # Clear patient conversation
    if has_agent and has_patient:
        return "HAS_PATIENT", has_agent, has_patient, count_speakers(segments), "Agent + patient content"
    
    # Fallback heuristics
    two_speakers = count_speakers(segments) >= 2
    conversational = ("?" in t) or (" ok" in t) or (" alright" in t)
    if two_speakers and conversational:
        return "HAS_PATIENT", has_agent, has_patient, count_speakers(segments), "Two speakers + conversational"
    
    return "NO_PATIENT", has_agent, has_patient, count_speakers(segments), "No patient content"

def process_file(file_path, trash_dir, delete_mode, dry_run):
    """Process a single JSON file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract transcript and segments
        transcript = ""
        segments = []
        try:
            transcript = data.get("results", {}).get("transcripts", [{}])[0].get("transcript", "")
            segments = data.get("results", {}).get("speaker_labels", {}).get("segments", [])
        except (KeyError, IndexError, TypeError):
            pass
        
        # Make decision
        status, has_agent, has_patient, speaker_count, reason = decide_status(transcript, segments)
        
        # Take action - remove both NO_PATIENT and ERROR files
        if status in ["NO_PATIENT", "ERROR"] and not dry_run:
            if delete_mode:
                os.remove(file_path)
            elif trash_dir:
                os.makedirs(trash_dir, exist_ok=True)
                shutil.move(file_path, os.path.join(trash_dir, os.path.basename(file_path)))
        
        return {
            "filename": os.path.basename(file_path),
            "directory": os.path.basename(os.path.dirname(file_path)),
            "status": status,
            "has_agent": has_agent,
            "has_patient_content": has_patient,
            "speaker_count": speaker_count,
            "reason": reason
        }
    
    except Exception as e:
        return {
            "filename": os.path.basename(file_path),
            "directory": os.path.basename(os.path.dirname(file_path)),
            "status": "ERROR",
            "has_agent": False,
            "has_patient_content": False,
            "speaker_count": 0,
            "reason": f"Error: {str(e)}"
        }

def process_directory(dir_path, trash_base, delete_mode, dry_run):
    """Process all JSON files in a directory"""
    dir_name = os.path.basename(dir_path)
    print(f"[Thread {threading.current_thread().name}] Processing directory: {dir_name}")
    
    json_files = glob(os.path.join(dir_path, "*.json"))
    if not json_files:
        print(f"[{dir_name}] No JSON files found")
        return []
    
    trash_dir = os.path.join(trash_base, f"trash_no_patient_{dir_name}") if trash_base else None
    results = []
    
    for file_path in json_files:
        result = process_file(file_path, trash_dir, delete_mode, dry_run)
        results.append(result)
    
    # Summary for this directory
    total = len(results)
    no_patient = sum(1 for r in results if r["status"] == "NO_PATIENT")
    has_patient = sum(1 for r in results if r["status"] == "HAS_PATIENT")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    removed = no_patient + errors
    
    print(f"[{dir_name}] Processed {total} files: {has_patient} kept, {removed} removed ({no_patient} IVR + {errors} errors)")
    return results

def main():
    parser = argparse.ArgumentParser(description="Filter call transcripts - keep only clean patient conversations")
    parser.add_argument("--src", required=True, help="Source directory containing numeric subdirectories")
    parser.add_argument("--trash", help="Base directory for trash folders")
    parser.add_argument("--delete", action="store_true", help="Delete files instead of moving to trash")
    parser.add_argument("--report", help="Output CSV report file")
    parser.add_argument("--dry-run", action="store_true", help="Don't move/delete files, just analyze")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum number of parallel threads")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.dry_run and not args.delete and not args.trash:
        parser.error("Must specify --trash directory, --delete, or --dry-run")
    
    # Expand user path and find numeric subdirectories
    src_path = Path(args.src).expanduser().resolve()
    if not src_path.exists():
        print(f"Error: Source directory {src_path} does not exist")
        print(f"Tried to resolve: {args.src} -> {src_path}")
        return
    
    numeric_dirs = []
    all_dirs = []
    for item in src_path.iterdir():
        if item.is_dir():
            all_dirs.append(item.name)
            if item.name.isdigit():
                numeric_dirs.append(str(item))
    
    print(f"All subdirectories found: {sorted(all_dirs)}")
    
    if not numeric_dirs:
        print(f"No numeric subdirectories found in {src_path}")
        return
    
    print(f"Found {len(numeric_dirs)} numeric directories to process")
    print(f"Using {args.max_workers} parallel threads")
    
    # Process directories in parallel
    all_results = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit all directory processing tasks
        future_to_dir = {
            executor.submit(process_directory, dir_path, args.trash, args.delete, args.dry_run): dir_path
            for dir_path in numeric_dirs
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_dir):
            dir_path = future_to_dir[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"Error processing {dir_path}: {e}")
    
    # Generate report
    if args.report and all_results:
        report_dir = os.path.dirname(args.report)
        if report_dir:  # Only create directory if there is one
            os.makedirs(report_dir, exist_ok=True)
        with open(args.report, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["filename", "directory", "status", "has_agent", "has_patient_content", "speaker_count", "reason"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        print(f"Report saved to: {args.report}")
    
    # Final summary
    total = len(all_results)
    if total > 0:
        no_patient = sum(1 for r in all_results if r["status"] == "NO_PATIENT")
        has_patient = sum(1 for r in all_results if r["status"] == "HAS_PATIENT")
        errors = sum(1 for r in all_results if r["status"] == "ERROR")
        
        print(f"\nFinal Summary:")
        print(f"Total files processed: {total}")
        print(f"Clean patient files (kept): {has_patient}")
        print(f"IVR-only files (removed): {no_patient}")
        print(f"Error/corrupted files (removed): {errors}")
        print(f"Total removed: {no_patient + errors}")
        
        if not args.dry_run:
            action = "deleted" if args.delete else "moved to trash"
            print(f"Bad files (IVR + errors) were {action}")

if __name__ == "__main__":
    main()