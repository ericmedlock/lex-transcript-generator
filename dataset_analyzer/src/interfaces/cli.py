"""Command line interface for dataset analyzer"""

import click
import yaml
from pathlib import Path
from typing import Optional

from ..core import FileScanner, FormatDetector, MetadataExtractor
from ..utils.config_manager import ConfigManager
from ..utils.logger import setup_logger

@click.group()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """Dataset Analyzer & Template Generator"""
    ctx.ensure_object(dict)
    
    # Setup logging
    logger = setup_logger(verbose)
    ctx.obj['logger'] = logger
    
    # Load configuration
    config_manager = ConfigManager(config)
    ctx.obj['config'] = config_manager
    
    logger.info("Dataset Analyzer initialized")

@cli.command()
@click.option('--input', '-i', required=True, help='Input directory to scan')
@click.option('--output', '-o', default='./analysis_results', help='Output directory')
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'csv']), default='yaml', help='Output format')
@click.pass_context
def scan(ctx, input: str, output: str, format: str):
    """Scan directory and analyze conversation files"""
    logger = ctx.obj['logger']
    config = ctx.obj['config']
    
    logger.info(f"Scanning directory: {input}")
    
    # Initialize components
    scanner = FileScanner(cache_enabled=config.get('processing.cache_enabled', True))
    detector = FormatDetector()
    extractor = MetadataExtractor()
    
    # Create output directory
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Scan and analyze files
    results = []
    file_count = 0
    
    try:
        for file_info in scanner.scan_directory(input):
            file_count += 1
            logger.info(f"Processing file {file_count}: {file_info.filepath}")
            
            # Parse conversation
            conversation = detector.parse_file(file_info.filepath)
            if conversation is None:
                logger.warning(f"Failed to parse: {file_info.filepath}")
                continue
            
            # Extract metadata
            metadata = extractor.extract_conversation_metadata(conversation)
            
            # Store result
            result = {
                'file_info': {
                    'filepath': file_info.filepath,
                    'size': file_info.size,
                    'extension': file_info.extension
                },
                'metadata': {
                    'turn_count': metadata.turn_count,
                    'speaker_count': metadata.speaker_count,
                    'avg_turn_length': metadata.avg_turn_length,
                    'total_length': metadata.total_length,
                    'speakers': metadata.speakers,
                    'conversation_type': metadata.conversation_type,
                    'quality_indicators': metadata.quality_indicators
                }
            }
            results.append(result)
    
    except KeyboardInterrupt:
        logger.info("Scan interrupted by user")
    except Exception as e:
        logger.error(f"Error during scan: {e}")
        return
    
    # Save results
    output_file = output_path / f"scan_results.{format}"
    
    if format == 'yaml':
        with open(output_file, 'w') as f:
            yaml.dump({'scan_results': results, 'total_files': len(results)}, f, default_flow_style=False)
    elif format == 'json':
        import json
        with open(output_file, 'w') as f:
            json.dump({'scan_results': results, 'total_files': len(results)}, f, indent=2)
    
    logger.info(f"Scan complete. Processed {len(results)} files. Results saved to: {output_file}")

@cli.command()
@click.option('--llm', default='openai', help='LLM provider (openai, local, ollama)')
@click.option('--model', help='Specific model to use')
@click.option('--export', type=click.Choice(['yaml', 'json']), default='yaml', help='Export format')
@click.pass_context
def generate_templates(ctx, llm: str, model: Optional[str], export: str):
    """Generate conversation templates from analyzed data"""
    logger = ctx.obj['logger']
    config = ctx.obj['config']
    
    logger.info("Template generation not yet implemented")
    logger.info(f"Would use LLM: {llm}, Model: {model}, Export: {export}")

@cli.command()
@click.option('--templates', help='Templates directory to validate')
@click.option('--sample-size', default=10, help='Number of samples to generate for validation')
@click.pass_context
def validate(ctx, templates: Optional[str], sample_size: int):
    """Validate generated templates"""
    logger = ctx.obj['logger']
    
    logger.info("Template validation not yet implemented")
    logger.info(f"Would validate templates in: {templates}, Sample size: {sample_size}")

def main():
    """Entry point for CLI"""
    cli()