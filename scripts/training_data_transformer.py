#!/usr/bin/env python3
"""
Training Data Transformer - Pipeline orchestrator for Lex V2 compliance
Pipeline: load → validate → scrub → filter artifacts → validate → serialize → write
"""

import json
import argparse
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple

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
    
    def transform_file(self, input_path: Path, output_path: Path, pii_config: Dict = None) -> bool:
        """Transform single file through complete pipeline"""
        if pii_config is None:
            pii_config = {"fallback_to_regex": True}
        
        try:
            print(f"Processing {input_path.name}...")
            
            # Stage 1: Load
            obj = self.load_conversation(input_path)
            
            # Stage 2: Initial validation
            obj = self.validate_stage(obj, "initial", input_path.name)
            
            # Stage 3: PII scrubbing
            obj = self.pii_scrub_stage(obj, pii_config)
            
            # Stage 4: Final validation
            obj = self.validate_stage(obj, "final", output_path.name)
            
            # Stage 5: Generate compliant filename
            contact_id = obj.get("CustomerMetadata", {}).get("ContactId", "unknown")
            compliant_filename = generate_lex_filename(contact_id)
            final_output_path = output_path.parent / compliant_filename
            
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
    
    def transform_directory(self, input_dir: Path, output_dir: Path, pii_config: Dict = None) -> Dict:
        """Transform all JSON files in directory"""
        input_files = list(input_dir.glob("**/*.json"))
        
        if not input_files:
            print(f"No JSON files found in {input_dir}")
            return self.stats
        
        print(f"Found {len(input_files)} JSON files to process")
        print(f"Pipeline: load -> validate -> scrub({self.pii_mode}) -> artifacts -> validate -> serialize -> write")
        print(f"Strict mode: {self.strict}, Fail on artifacts: {self.fail_on_artifacts}")
        print()
        
        for input_file in input_files:
            # Preserve relative directory structure
            rel_path = input_file.relative_to(input_dir)
            output_file = output_dir / rel_path
            
            self.transform_file(input_file, output_file, pii_config)
        
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
            
            stats = pipeline.transform_directory(input_path, output_path)
            
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