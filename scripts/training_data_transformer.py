#!/usr/bin/env python3
"""
Training Data Transformer - Pipeline orchestrator for Lex V2 compliance
Pipeline: load → scrub → validate → serialize → write
"""

import json
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.lex_validator import (
    LexValidator, serialize_canonical_lex, fix_lex_object, 
    generate_lex_filename, LexValidationError
)

try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pii_scrubber.engine import scrub_text
    PII_AVAILABLE = True
    class LLMUnavailableError(Exception): pass
except ImportError:
    PII_AVAILABLE = False
    def scrub_text(text, mode, strategy, config): return text
    class LLMUnavailableError(Exception): pass

def process_single_file(args):
    """Process single file - used by multiprocessing pool"""
    input_path, output_path, pii_mode, pii_strategy, strict, fail_on_artifacts, pii_config = args
    
    # Create pipeline instance for this worker
    pipeline = TransformationPipeline(
        pii_mode=pii_mode,
        pii_strategy=pii_strategy,
        strict=strict,
        fail_on_artifacts=fail_on_artifacts
    )
    
    return pipeline.transform_file(input_path, output_path, pii_config)

def process_file_batch(args):
    """Process batch of files - used by multiprocessing pool for batch PII scrubbing"""
    file_args_list, pii_mode, pii_strategy, strict, fail_on_artifacts, pii_config = args
    
    # Create pipeline instance for this worker
    pipeline = TransformationPipeline(
        pii_mode=pii_mode,
        pii_strategy=pii_strategy,
        strict=strict,
        fail_on_artifacts=fail_on_artifacts
    )
    
    results = []
    
    # Load all conversations first
    conversations = []
    file_paths = []
    
    for input_path, output_path in file_args_list:
        try:
            obj = pipeline.load_conversation(input_path)
            conversations.append(obj)
            file_paths.append((input_path, output_path))
        except Exception as e:
            print(f"  - Failed to load {input_path.name}: {e}")
            results.append(False)
            continue
    
    if not conversations:
        return results
    
    try:
        # Batch process PII scrubbing
        scrubbed_conversations = pipeline.batch_pii_scrub_stage(conversations, pii_config)
        
        # Process each conversation individually for validation and writing
        for i, (obj, (input_path, output_path)) in enumerate(zip(scrubbed_conversations, file_paths)):
            try:
                # Validate and write
                obj = pipeline.validate_stage(obj, "final", output_path.name)
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(serialize_canonical_lex(obj))
                
                print(f"  + Wrote {output_path.name}")
                results.append(True)
                
            except Exception as e:
                print(f"  - Failed to process {input_path.name}: {e}")
                results.append(False)
    
    except Exception as e:
        print(f"  - Batch processing failed: {e}, falling back to individual processing")
        # Fallback to individual processing
        for input_path, output_path in file_paths:
            try:
                success = pipeline.transform_file(input_path, output_path, pii_config)
                results.append(success)
            except Exception as e:
                print(f"  - Failed to process {input_path.name}: {e}")
                results.append(False)
    
    return results

class TransformationPipeline:
    def __init__(self, pii_mode="raw", pii_strategy="llm", strict=False, fail_on_artifacts=False):
        self.pii_mode = pii_mode
        self.pii_strategy = pii_strategy
        self.strict = strict
        self.fail_on_artifacts = fail_on_artifacts
        self.validator = LexValidator()
        self.stats = {
            "processed": 0,
            "failed": 0,
            "artifacts_removed": 0,
            "pii_scrubbed": 0,
            "auto_fixed": 0
        }
    
    def load_conversation(self, file_path: Path) -> Dict:
        """Load conversation from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load {file_path}: {e}")
    
    def validate_stage(self, obj: Dict, stage_name: str, filename: str = None) -> Dict:
        """Validation stage with error handling"""
        report = self.validator.run_all_validations(obj, filename)
        
        if not report["valid"]:
            if self.strict:
                errors = "; ".join(report["errors"])
                raise LexValidationError(f"{stage_name} validation failed: {errors}")
            else:
                print(f"  Auto-fixing {stage_name} issues...")
                obj = fix_lex_object(obj, self.pii_mode)
                self.stats["auto_fixed"] += 1
        
        # Handle artifacts
        if report["artifact_count"] > 0:
            if self.fail_on_artifacts:
                raise LexValidationError(f"Artifacts found in {stage_name} (fail-on-artifacts enabled)")
            else:
                print(f"  Removing {report['artifact_count']} artifacts...")
                obj, removed = self.validator.remove_artifacts(obj)
                self.stats["artifacts_removed"] += removed
        
        return obj
    
    def pii_scrub_stage(self, obj: Dict, pii_config: Dict) -> Dict:
        """PII scrubbing stage"""
        if self.pii_mode == "raw":
            # Set metadata for raw mode
            if "ContentMetadata" not in obj:
                obj["ContentMetadata"] = {}
            obj["ContentMetadata"]["Output"] = "Raw"
            obj["ContentMetadata"]["RedactionTypes"] = ["PII"]
            return obj
        
        if not PII_AVAILABLE:
            if self.pii_mode == "safe":
                raise LexValidationError("PII scrubber not available for safe mode")
            return obj
        
        print(f"  Scrubbing PII using {self.pii_strategy} strategy...")
        scrubbed_any = False
        
        for turn in obj.get("Transcript", []):
            if isinstance(turn, dict) and "Content" in turn:
                original_content = turn["Content"]
                try:
                    config_with_fallback = pii_config.copy()
                    config_with_fallback['fallback_to_regex'] = self.pii_strategy != "llm"
                    
                    scrubbed_content = scrub_text(original_content, self.pii_mode, self.pii_strategy, config_with_fallback)
                    turn["Content"] = scrubbed_content
                    if scrubbed_content != original_content:
                        scrubbed_any = True
                except LLMUnavailableError as e:
                    if self.pii_strategy == "llm" and not pii_config.get('fallback_to_regex', True):
                        raise LexValidationError(f"LLM unavailable for PII scrubbing: {e}")
                    # Fallback handled by scrub_text
        
        # Update metadata
        if "ContentMetadata" not in obj:
            obj["ContentMetadata"] = {}
        obj["ContentMetadata"]["Output"] = "Redacted" if scrubbed_any else "Raw"
        obj["ContentMetadata"]["RedactionTypes"] = ["PII"]
        
        if scrubbed_any:
            self.stats["pii_scrubbed"] += 1
        
        return obj
    
    def batch_pii_scrub_stage(self, conversations: List[Dict], pii_config: Dict) -> List[Dict]:
        """Batch PII scrubbing for multiple conversations"""
        # Ensure pii_config is not None
        if pii_config is None:
            pii_config = {"fallback_to_regex": True}
        
        if self.pii_mode == "raw":
            # Set metadata for raw mode on all conversations
            for obj in conversations:
                if "ContentMetadata" not in obj:
                    obj["ContentMetadata"] = {}
                obj["ContentMetadata"]["Output"] = "Raw"
                obj["ContentMetadata"]["RedactionTypes"] = ["PII"]
            return conversations
        
        if not PII_AVAILABLE:
            if self.pii_mode == "safe":
                raise LexValidationError("PII scrubber not available for safe mode")
            return conversations
        
        if self.pii_strategy != "llm":
            # For non-LLM strategies, fall back to individual processing
            return [self.pii_scrub_stage(obj, pii_config) for obj in conversations]
        
        print(f"  Batch scrubbing PII for {len(conversations)} conversations using {self.pii_strategy} strategy...")
        
        # Collect all turns that need scrubbing
        turns_to_scrub = []
        turn_mapping = []  # (conv_idx, turn_idx) for each turn in turns_to_scrub
        
        for conv_idx, obj in enumerate(conversations):
            for turn_idx, turn in enumerate(obj.get("Transcript", [])):
                if isinstance(turn, dict) and "Content" in turn:
                    turns_to_scrub.append(turn["Content"])
                    turn_mapping.append((conv_idx, turn_idx))
        
        if not turns_to_scrub:
            return conversations
        
        try:
            # Batch scrub all turns
            scrubbed_turns = self._batch_scrub_texts(turns_to_scrub, pii_config)
            
            # Apply scrubbed content back to conversations
            for i, scrubbed_content in enumerate(scrubbed_turns):
                conv_idx, turn_idx = turn_mapping[i]
                original_content = conversations[conv_idx]["Transcript"][turn_idx]["Content"]
                conversations[conv_idx]["Transcript"][turn_idx]["Content"] = scrubbed_content
                
                # Update metadata if content changed
                if scrubbed_content != original_content:
                    if "ContentMetadata" not in conversations[conv_idx]:
                        conversations[conv_idx]["ContentMetadata"] = {}
                    conversations[conv_idx]["ContentMetadata"]["Output"] = "Redacted"
                    conversations[conv_idx]["ContentMetadata"]["RedactionTypes"] = ["PII"]
                    self.stats["pii_scrubbed"] += 1
                else:
                    if "ContentMetadata" not in conversations[conv_idx]:
                        conversations[conv_idx]["ContentMetadata"] = {}
                    conversations[conv_idx]["ContentMetadata"]["Output"] = "Raw"
                    conversations[conv_idx]["ContentMetadata"]["RedactionTypes"] = ["PII"]
            
            return conversations
            
        except Exception as e:
            print(f"  Batch PII scrubbing failed: {e}, falling back to individual processing")
            # Fallback to individual processing
            return [self.pii_scrub_stage(obj, pii_config) for obj in conversations]
    
    def _batch_scrub_texts(self, texts: List[str], pii_config: Dict) -> List[str]:
        """Batch scrub multiple texts using LLM"""
        if not texts:
            return []
        
        # Ensure pii_config is not None
        if pii_config is None:
            pii_config = {"fallback_to_regex": True}
        
        try:
            from pii_scrubber.llm_client import batch_redact_with_llm
            endpoint = pii_config.get('llm', {}).get('endpoint', 'http://127.0.0.1:1234/v1/chat/completions')
            model = pii_config.get('llm', {}).get('model', 'redactor-7b-gguf')
            timeout = pii_config.get('llm', {}).get('timeout_s', 20)
            
            return batch_redact_with_llm(texts, endpoint, model, timeout)
        except ImportError:
            # batch_redact_with_llm not available, fall back to individual calls
            from pii_scrubber.engine import scrub_text
            return [scrub_text(text, self.pii_mode, self.pii_strategy, pii_config) for text in texts]
    
    def transform_file(self, input_path: Path, output_path: Path, pii_config: Dict = None) -> bool:
        """Transform single file through complete pipeline"""
        if pii_config is None:
            pii_config = {"fallback_to_regex": True}
        
        try:
            print(f"Processing {input_path.name}...")
            
            # Stage 1: Load
            obj = self.load_conversation(input_path)
            
            # Stage 2: PII scrubbing
            obj = self.pii_scrub_stage(obj, pii_config)
            
            # Stage 3: Final validation
            obj = self.validate_stage(obj, "final", output_path.name)
            
            # Stage 5: Use original filename to preserve uniqueness
            final_output_path = output_path
            
            # Stage 6: Serialize and write
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write(serialize_canonical_lex(obj))
            
            print(f"  + Wrote {final_output_path.name}")
            self.stats["processed"] += 1
            return True
            
        except Exception as e:
            print(f"  - Failed: {e}")
            self.stats["failed"] += 1
            return False
    
    def transform_directory(self, input_dir: Path, output_dir: Path, pii_config: Dict = None, workers: int = 1, batch_size: int = 10) -> Dict:
        """Transform all JSON files in directory"""
        input_files = list(input_dir.glob("**/*.json"))
        
        if not input_files:
            print(f"No JSON files found in {input_dir}")
            return self.stats
        
        print(f"Found {len(input_files)} JSON files to process")
        print(f"Pipeline: load -> scrub({self.pii_mode}) -> validate -> serialize -> write")
        print(f"Strict mode: {self.strict}, Fail on artifacts: {self.fail_on_artifacts}")
        print(f"Workers: {workers}, Batch size: {batch_size}")
        print()
        
        if workers == 1:
            # Single-threaded processing
            for input_file in input_files:
                output_file = output_dir / input_file.name
                self.transform_file(input_file, output_file, pii_config)
        else:
            # Multi-threaded processing with batching for PII scrubbing
            use_batching = (self.pii_mode == "safe" and self.pii_strategy == "llm" and batch_size > 1)
            
            if use_batching:
                print(f"Using batch PII scrubbing with batch size {batch_size}")
                # Group files into batches
                file_batches = []
                for i in range(0, len(input_files), batch_size):
                    batch_files = input_files[i:i + batch_size]
                    batch_args = []
                    for input_file in batch_files:
                        output_file = output_dir / input_file.name
                        batch_args.append((input_file, output_file))
                    
                    file_batches.append((
                        batch_args, self.pii_mode, self.pii_strategy,
                        self.strict, self.fail_on_artifacts, pii_config
                    ))
                
                # Process batches in parallel
                with ProcessPoolExecutor(max_workers=workers) as executor:
                    batch_results = list(executor.map(process_file_batch, file_batches))
                
                # Aggregate results from batches
                for batch_result in batch_results:
                    for success in batch_result:
                        if success:
                            self.stats["processed"] += 1
                        else:
                            self.stats["failed"] += 1
            else:
                # Standard individual file processing
                print(f"Using individual file processing (batching disabled for mode={self.pii_mode}, strategy={self.pii_strategy})")
                file_args = []
                for input_file in input_files:
                    output_file = output_dir / input_file.name
                    file_args.append((
                        input_file, output_file, self.pii_mode, self.pii_strategy,
                        self.strict, self.fail_on_artifacts, pii_config
                    ))
                
                # Process files in parallel
                with ProcessPoolExecutor(max_workers=workers) as executor:
                    results = list(executor.map(process_single_file, file_args))
                
                # Aggregate results
                for success in results:
                    if success:
                        self.stats["processed"] += 1
                    else:
                        self.stats["failed"] += 1
        
        return self.stats

def main():
    parser = argparse.ArgumentParser(description="Transform conversations to Lex V2 compliant format")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("output", help="Output file or directory")
    
    # Pipeline options
    parser.add_argument("--mode", choices=["safe", "raw"], default="raw", help="PII scrubbing mode")
    parser.add_argument("--pii-strategy", choices=["llm", "regex", "off"], default="llm", help="PII scrubbing strategy")
    parser.add_argument("--strict", action="store_true", help="Fail on validation errors instead of auto-fixing")
    parser.add_argument("--fail-on-artifacts", action="store_true", help="Fail if artifact lines found")
    
    # Processing options
    parser.add_argument("--dry-run", action="store_true", help="Validate only, don't write files")
    parser.add_argument("--workers", type=int, default=mp.cpu_count(), help="Number of parallel workers (default: CPU count)")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of files to batch for PII scrubbing (default: 10)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"ERROR: Input path {input_path} does not exist")
        return 1
    
    # Initialize pipeline
    pipeline = TransformationPipeline(
        pii_mode=args.mode,
        pii_strategy=args.pii_strategy,
        strict=args.strict,
        fail_on_artifacts=args.fail_on_artifacts
    )
    
    try:
        if input_path.is_file():
            # Single file processing
            if args.dry_run:
                print("[DRY RUN] Would process single file")
                return 0
            
            success = pipeline.transform_file(input_path, output_path)
            if not success:
                return 1
        else:
            # Directory processing
            if args.dry_run:
                print("[DRY RUN] Would process directory")
                return 0
            
            stats = pipeline.transform_directory(input_path, output_path, pii_config=None, workers=args.workers, batch_size=args.batch_size)
            
            print(f"\nTransformation complete:")
            print(f"  Processed: {stats['processed']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Auto-fixed: {stats['auto_fixed']}")
            print(f"  Artifacts removed: {stats['artifacts_removed']}")
            print(f"  PII scrubbed: {stats['pii_scrubbed']}")
            
            if stats['failed'] > 0:
                return 1
    
    except KeyboardInterrupt:
        print("\n\nTransformation cancelled by user.")
        return 1
    except LexValidationError as e:
        print(f"\nVALIDATION ERROR: {e}")
        return 2
    except Exception as e:
        print(f"ERROR: Transformation failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())