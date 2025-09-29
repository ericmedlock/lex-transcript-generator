#!/usr/bin/env python3
"""
Training Dataset Processor - Convert Training Datasets to LEX format with PII redaction
"""

import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.data.translators.file_processor import FileProcessor
from src.data.translators.lex_converter import LexConverter
from src.data.translators.pii_processor import PIIProcessor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainingDatasetProcessor:
    """Process Training Datasets directory and convert to LEX format"""
    
    def __init__(self, pii_mode: str = "safe", pii_strategy: str = "regex"):
        self.file_processor = FileProcessor()
        self.lex_converter = LexConverter()
        self.pii_processor = PIIProcessor()
        self.pii_mode = pii_mode
        self.pii_strategy = pii_strategy
        
        self.stats = {
            'files_processed': 0,
            'conversations_converted': 0,
            'conversations_skipped': 0,
            'pii_scrubbed': 0,
            'errors': 0,
            'by_extension': {},
            'pii_stats': {}
        }
    
    def process_directory(self, input_dir: Path, output_dir: Path, recursive: bool = True) -> Dict[str, Any]:
        """
        Process all files in Training Datasets directory
        
        Args:
            input_dir: Input directory to process
            output_dir: Output directory for LEX files
            recursive: Whether to process subdirectories
            
        Returns:
            Processing statistics
        """
        logger.info(f"Processing directory: {input_dir}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"PII mode: {self.pii_mode}, strategy: {self.pii_strategy}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get file statistics
        file_stats = self.file_processor.get_file_stats(input_dir)
        logger.info(f"Found {file_stats['total_files']} files to process")
        logger.info(f"File types: {file_stats['by_extension']}")
        
        # Process each file
        for file_path in self.file_processor.scan_directory(input_dir, recursive):
            try:
                self._process_file(file_path, output_dir)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.stats['errors'] += 1
        
        # Generate summary report
        self._generate_summary_report(output_dir)
        
        return self.stats
    
    def _process_file(self, file_path: Path, output_dir: Path):
        """Process a single file"""
        logger.info(f"Processing: {file_path}")
        
        self.stats['files_processed'] += 1
        ext = file_path.suffix.lower()
        self.stats['by_extension'][ext] = self.stats['by_extension'].get(ext, 0) + 1
        
        # Create subdirectory structure in output
        relative_path = file_path.relative_to(file_path.parents[len(file_path.parents) - 2])  # Relative to Training Datasets
        output_subdir = output_dir / relative_path.parent
        output_subdir.mkdir(parents=True, exist_ok=True)
        
        # Process conversations from file
        for conversation_item in self.file_processor.process_file(file_path):
            try:
                self._process_conversation(conversation_item, output_subdir, file_path.stem)
            except Exception as e:
                logger.error(f"Error processing conversation from {file_path}: {e}")
                self.stats['conversations_skipped'] += 1
    
    def _process_conversation(self, conversation_item: Dict[str, Any], output_dir: Path, base_filename: str):
        """Process a single conversation"""
        conversation_data = conversation_item['conversation_data']
        metadata = conversation_item.get('metadata', {})
        index = conversation_item.get('index', 0)
        
        # Convert to LEX format
        try:
            lex_data = self.lex_converter.convert_to_lex(conversation_data, metadata)
        except Exception as e:
            logger.error(f"Failed to convert conversation to LEX format: {e}")
            self.stats['conversations_skipped'] += 1
            return
        
        # Validate LEX format
        if not self.lex_converter.validate_lex_format(lex_data):
            logger.warning(f"Invalid LEX format generated for conversation {index}")
            self.stats['conversations_skipped'] += 1
            return
        
        # Apply PII scrubbing
        pii_found = False
        if self.pii_mode == "safe":
            for turn in lex_data.get("Transcript", []):
                original_content = turn.get("Content", "")
                
                # Detect PII before scrubbing
                pii_detected = self.pii_processor.detect_pii(original_content)
                if pii_detected:
                    pii_found = True
                    for pii_type, count in pii_detected.items():
                        self.stats['pii_stats'][pii_type] = self.stats['pii_stats'].get(pii_type, 0) + count
                
                # Scrub PII
                scrubbed_content = self.pii_processor.scrub_text(
                    original_content, self.pii_mode, self.pii_strategy
                )
                turn["Content"] = scrubbed_content
            
            # Update metadata
            lex_data["ContentMetadata"]["Output"] = "Redacted"
            if pii_found:
                self.stats['pii_scrubbed'] += 1
        else:
            lex_data["ContentMetadata"]["Output"] = "Raw"
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{base_filename}_{index:04d}_{timestamp}.json"
        output_path = output_dir / output_filename
        
        # Write LEX file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(lex_data, f, indent=2, ensure_ascii=False)
        
        self.stats['conversations_converted'] += 1
        
        if self.stats['conversations_converted'] % 100 == 0:
            logger.info(f"Processed {self.stats['conversations_converted']} conversations...")
    
    def _generate_summary_report(self, output_dir: Path):
        """Generate processing summary report"""
        summary = {
            "processing_date": datetime.now().isoformat(),
            "pii_mode": self.pii_mode,
            "pii_strategy": self.pii_strategy,
            "statistics": self.stats,
            "output_directory": str(output_dir)
        }
        
        # Write summary
        summary_path = output_dir / "processing_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("Processing Summary:")
        logger.info(f"  Files processed: {self.stats['files_processed']}")
        logger.info(f"  Conversations converted: {self.stats['conversations_converted']}")
        logger.info(f"  Conversations skipped: {self.stats['conversations_skipped']}")
        logger.info(f"  PII scrubbed: {self.stats['pii_scrubbed']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info(f"  Summary saved: {summary_path}")

def main():
    parser = argparse.ArgumentParser(description="Process Training Datasets to LEX format with PII redaction")
    parser.add_argument("--input-dir", type=Path, default="Training Datasets", 
                       help="Input directory (default: Training Datasets)")
    parser.add_argument("--output-dir", type=Path, default="Training Datasets/lex-transformed-data",
                       help="Output directory (default: Training Datasets/lex-transformed-data)")
    parser.add_argument("--pii-mode", choices=["safe", "raw"], default="safe",
                       help="PII handling mode (default: safe)")
    parser.add_argument("--pii-strategy", choices=["llm", "regex", "off"], default="regex",
                       help="PII scrubbing strategy (default: regex)")
    parser.add_argument("--no-recursive", action="store_true",
                       help="Don't process subdirectories")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be processed without writing files")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not args.input_dir.exists():
        logger.error(f"Input directory not found: {args.input_dir}")
        return 1
    
    # Create processor
    processor = TrainingDatasetProcessor(args.pii_mode, args.pii_strategy)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be written")
        # Just scan and report
        file_stats = processor.file_processor.get_file_stats(args.input_dir)
        logger.info(f"Would process {file_stats['total_files']} files")
        logger.info(f"File types: {file_stats['by_extension']}")
        logger.info(f"Total size: {file_stats['total_size']:,} bytes")
        return 0
    
    # Process directory
    try:
        stats = processor.process_directory(
            args.input_dir, 
            args.output_dir, 
            recursive=not args.no_recursive
        )
        
        if stats['conversations_converted'] > 0:
            logger.info(f"Successfully processed {stats['conversations_converted']} conversations")
            logger.info(f"LEX files ready in: {args.output_dir}")
        else:
            logger.warning("No conversations were converted")
        
        return 0
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())