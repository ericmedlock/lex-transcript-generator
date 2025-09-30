#!/usr/bin/env python3
"""
Efficient Lex Quality Analyzer - Fast statistical analysis
"""

import json
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
import time

class FastLexAnalyzer:
    def __init__(self):
        self.pii_patterns = {
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        }

    def quick_sample(self, directory: Path, sample_size: int = 50) -> List[Path]:
        """Get a quick random sample"""
        all_files = list(directory.glob("**/*.json"))
        if len(all_files) <= sample_size:
            return all_files
        return random.sample(all_files, sample_size)

    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single file quickly"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Format compliance
            required_fields = ['Version', 'Participants', 'Transcript', 'ContentMetadata']
            format_ok = all(field in data for field in required_fields)
            version_ok = data.get('Version') == '1.1.0'
            
            # Basic metrics
            participants = data.get('Participants', [])
            transcript = data.get('Transcript', [])
            
            # PII detection (sample first 5 turns for speed)
            pii_count = 0
            sample_turns = transcript[:5] if len(transcript) > 5 else transcript
            for turn in sample_turns:
                content = turn.get('Content', '')
                for pattern in self.pii_patterns.values():
                    pii_count += len(re.findall(pattern, content))
            
            # Quality metrics
            turn_lengths = []
            empty_turns = 0
            for turn in transcript:
                content = turn.get('Content', '')
                word_count = len(content.split()) if content else 0
                turn_lengths.append(word_count)
                if word_count == 0:
                    empty_turns += 1
            
            avg_turn_length = sum(turn_lengths) / len(turn_lengths) if turn_lengths else 0
            
            # Speaker alternation (quick check)
            speakers = [turn.get('ParticipantId', '') for turn in transcript]
            alternations = sum(1 for i in range(1, len(speakers)) if speakers[i] != speakers[i-1])
            alternation_rate = alternations / (len(speakers) - 1) if len(speakers) > 1 else 0
            
            return {
                'format_ok': format_ok and version_ok,
                'participant_count': len(participants),
                'turn_count': len(transcript),
                'avg_turn_length': avg_turn_length,
                'empty_turns': empty_turns,
                'pii_detected': pii_count > 0,
                'pii_count': pii_count,
                'alternation_rate': alternation_rate,
                'speaker_roles': [p.get('ParticipantRole', 'UNKNOWN') for p in participants],
                'error': None
            }
            
        except Exception as e:
            return {'error': str(e), 'format_ok': False}

    def analyze_directory(self, directory: Path, sample_size: int = 50) -> Dict:
        """Analyze directory with sampling"""
        print(f"\nAnalyzing {directory}")
        
        all_files = list(directory.glob("**/*.json"))
        total_files = len(all_files)
        
        if total_files == 0:
            return {'error': 'No files found', 'total_files': 0}
        
        # Sample files
        sample_files = self.quick_sample(directory, sample_size)
        actual_sample_size = len(sample_files)
        
        print(f"Total files: {total_files:,}")
        print(f"Sample size: {actual_sample_size}")
        print(f"Analyzing...")
        
        # Analyze sample
        results = []
        start_time = time.time()
        
        for i, file_path in enumerate(sample_files):
            if i % 10 == 0 and i > 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                eta = (actual_sample_size - i) / rate if rate > 0 else 0
                print(f"  Progress: {i}/{actual_sample_size} ({i/actual_sample_size*100:.1f}%) - ETA: {eta:.1f}s")
            
            result = self.analyze_file(file_path)
            results.append(result)
        
        elapsed = time.time() - start_time
        print(f"  Completed in {elapsed:.1f}s")
        
        # Calculate aggregate metrics
        valid_results = [r for r in results if not r.get('error')]
        error_count = len(results) - len(valid_results)
        
        if not valid_results:
            return {'error': 'No valid files analyzed', 'total_files': total_files}
        
        # Aggregate metrics
        format_compliance = sum(1 for r in valid_results if r['format_ok']) / len(valid_results)
        pii_detection_rate = sum(1 for r in valid_results if r['pii_detected']) / len(valid_results)
        
        avg_turns = sum(r['turn_count'] for r in valid_results) / len(valid_results)
        avg_turn_length = sum(r['avg_turn_length'] for r in valid_results) / len(valid_results)
        avg_alternation = sum(r['alternation_rate'] for r in valid_results) / len(valid_results)
        
        total_empty_turns = sum(r['empty_turns'] for r in valid_results)
        total_turns = sum(r['turn_count'] for r in valid_results)
        empty_turn_rate = total_empty_turns / total_turns if total_turns > 0 else 0
        
        # Speaker roles
        all_roles = []
        for r in valid_results:
            all_roles.extend(r['speaker_roles'])
        role_distribution = dict(Counter(all_roles))
        
        # Quality score (0-100)
        quality_score = 100
        quality_score *= format_compliance  # Format compliance weight
        quality_score -= pii_detection_rate * 30  # PII penalty
        quality_score -= empty_turn_rate * 20  # Empty turn penalty
        quality_score += avg_alternation * 10  # Alternation bonus
        quality_score = max(0, min(100, quality_score))
        
        return {
            'total_files': total_files,
            'sample_size': actual_sample_size,
            'error_count': error_count,
            'format_compliance': format_compliance,
            'pii_detection_rate': pii_detection_rate,
            'avg_conversation_length': avg_turns,
            'avg_turn_length': avg_turn_length,
            'empty_turn_rate': empty_turn_rate,
            'alternation_rate': avg_alternation,
            'speaker_distribution': role_distribution,
            'quality_score': quality_score,
            'analysis_time': elapsed
        }

    def calculate_lex_readiness(self, metrics: Dict) -> float:
        """Calculate Lex readiness confidence (0-100)"""
        if metrics.get('error'):
            return 0
        
        confidence = 100
        
        # Format compliance (40% weight)
        confidence *= (0.6 + 0.4 * metrics['format_compliance'])
        
        # PII penalty (20% weight)
        pii_penalty = min(metrics['pii_detection_rate'] * 50, 20)
        confidence -= pii_penalty
        
        # Quality factors (40% weight)
        quality_factor = (
            (1 - metrics['empty_turn_rate']) * 0.3 +  # Low empty turns
            min(metrics['avg_turn_length'] / 10, 1) * 0.3 +  # Good turn length
            metrics['alternation_rate'] * 0.4  # Good alternation
        )
        confidence *= (0.6 + 0.4 * quality_factor)
        
        return max(0, min(100, confidence))

    def print_report(self, health_metrics: Dict, lex_metrics: Dict):
        """Print comprehensive report"""
        print("\n" + "="*80)
        print("LEX EXPORT QUALITY ANALYSIS REPORT")
        print("="*80)
        
        datasets = [
            ("Health Calls Output", health_metrics),
            ("Lex Export", lex_metrics)
        ]
        
        for name, metrics in datasets:
            if metrics.get('error'):
                print(f"\n{name}: ERROR - {metrics['error']}")
                continue
            
            confidence = self.calculate_lex_readiness(metrics)
            
            print(f"\n{name.upper()}:")
            print(f"  Total Files: {metrics['total_files']:,}")
            print(f"  Sample Analyzed: {metrics['sample_size']}")
            print(f"  Analysis Time: {metrics['analysis_time']:.1f}s")
            print(f"  Format Compliance: {metrics['format_compliance']*100:.1f}%")
            print(f"  PII Detection Rate: {metrics['pii_detection_rate']*100:.1f}%")
            print(f"  Avg Conversation Length: {metrics['avg_conversation_length']:.1f} turns")
            print(f"  Avg Turn Length: {metrics['avg_turn_length']:.1f} words")
            print(f"  Empty Turn Rate: {metrics['empty_turn_rate']*100:.1f}%")
            print(f"  Speaker Alternation: {metrics['alternation_rate']*100:.1f}%")
            print(f"  Quality Score: {metrics['quality_score']:.1f}/100")
            print(f"  LEX READINESS: {confidence:.1f}%")
            
            if metrics['speaker_distribution']:
                print(f"  Speaker Roles: {dict(metrics['speaker_distribution'])}")
        
        # Overall recommendation
        print(f"\n{'='*80}")
        print("FINAL RECOMMENDATION:")
        
        if not health_metrics.get('error') and not lex_metrics.get('error'):
            health_confidence = self.calculate_lex_readiness(health_metrics)
            lex_confidence = self.calculate_lex_readiness(lex_metrics)
            overall_confidence = (health_confidence + lex_confidence) / 2
            
            print(f"Overall Confidence: {overall_confidence:.1f}%")
            
            if overall_confidence >= 85:
                print("[READY] High confidence for Lex deployment")
            elif overall_confidence >= 70:
                print("[CAUTION] Ready with minor fixes needed")
            else:
                print("[NOT READY] Significant issues require resolution")
        
        print("="*80)

def main():
    analyzer = FastLexAnalyzer()
    
    print("Fast Lex Export Quality Analysis")
    print("Analyzing statistical samples for quick assessment...")
    
    # Analyze directories
    health_dir = Path("Training Datasets/health-calls-output")
    lex_dir = Path("lex_export")
    
    health_metrics = analyzer.analyze_directory(health_dir, sample_size=100)
    lex_metrics = analyzer.analyze_directory(lex_dir, sample_size=100)
    
    # Generate report
    analyzer.print_report(health_metrics, lex_metrics)

if __name__ == "__main__":
    main()