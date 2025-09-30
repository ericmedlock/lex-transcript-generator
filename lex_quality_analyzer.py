#!/usr/bin/env python3
"""
Lex Export Quality Analyzer
Statistical analysis of Lex v2 conversation files for PII, format compliance, and quality
"""

import json
import random
import re
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np

@dataclass
class QualityMetrics:
    total_files: int
    sample_size: int
    format_compliance: float
    pii_detection_rate: float
    avg_conversation_length: float
    avg_turn_length: float
    speaker_distribution: Dict[str, int]
    quality_score: float
    issues: List[str]

class LexQualityAnalyzer:
    def __init__(self):
        self.pii_patterns = {
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'date_birth': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            'address': r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b'
        }
        
        self.lex_required_fields = {
            'Version': str,
            'Participants': list,
            'Transcript': list,
            'ContentMetadata': dict,
            'CustomerMetadata': dict
        }
        
        self.participant_required_fields = {
            'ParticipantId': str,
            'ParticipantRole': str
        }
        
        self.turn_required_fields = {
            'ParticipantId': str,
            'Id': str,
            'Content': str
        }

    def get_statistical_sample(self, directory: Path, confidence_level: float = 0.95, margin_error: float = 0.05) -> List[Path]:
        """Calculate statistically meaningful sample size and return random sample"""
        all_files = list(directory.glob("**/*.json"))
        population_size = len(all_files)
        
        if population_size == 0:
            return []
        
        # Calculate sample size using formula for finite population
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%
        p = 0.5  # Maximum variability
        
        numerator = (z_score ** 2) * p * (1 - p)
        denominator = (margin_error ** 2)
        
        sample_size_infinite = numerator / denominator
        sample_size = sample_size_infinite / (1 + ((sample_size_infinite - 1) / population_size))
        
        final_sample_size = min(int(math.ceil(sample_size)), population_size)
        
        # Ensure minimum sample size for small populations
        if population_size < 30:
            final_sample_size = population_size
        elif final_sample_size < 30:
            final_sample_size = min(30, population_size)
        
        print(f"Population: {population_size} files")
        print(f"Sample size for {confidence_level*100}% confidence, ±{margin_error*100}% margin: {final_sample_size}")
        
        return random.sample(all_files, final_sample_size)

    def detect_pii_in_text(self, text: str) -> Dict[str, List[str]]:
        """Detect PII patterns in text"""
        detected = defaultdict(list)
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                detected[pii_type].extend(matches)
        
        return dict(detected)

    def validate_lex_format(self, data: Dict) -> Tuple[bool, List[str]]:
        """Validate Lex v2 format compliance"""
        issues = []
        
        # Check top-level required fields
        for field, expected_type in self.lex_required_fields.items():
            if field not in data:
                issues.append(f"Missing required field: {field}")
            elif not isinstance(data[field], expected_type):
                issues.append(f"Field {field} has wrong type: expected {expected_type.__name__}, got {type(data[field]).__name__}")
        
        # Check Version
        if 'Version' in data and data['Version'] != '1.1.0':
            issues.append(f"Incorrect version: {data['Version']} (expected 1.1.0)")
        
        # Validate Participants
        if 'Participants' in data:
            for i, participant in enumerate(data['Participants']):
                for field, expected_type in self.participant_required_fields.items():
                    if field not in participant:
                        issues.append(f"Participant {i}: Missing {field}")
                    elif not isinstance(participant[field], expected_type):
                        issues.append(f"Participant {i}: {field} wrong type")
                
                # Check valid roles
                if 'ParticipantRole' in participant:
                    valid_roles = ['AGENT', 'CUSTOMER', 'SYSTEM']
                    if participant['ParticipantRole'] not in valid_roles:
                        issues.append(f"Participant {i}: Invalid role {participant['ParticipantRole']}")
        
        # Validate Transcript
        if 'Transcript' in data:
            participant_ids = set()
            if 'Participants' in data:
                participant_ids = {p['ParticipantId'] for p in data['Participants']}
            
            for i, turn in enumerate(data['Transcript']):
                for field, expected_type in self.turn_required_fields.items():
                    if field not in turn:
                        issues.append(f"Turn {i}: Missing {field}")
                    elif not isinstance(turn[field], expected_type):
                        issues.append(f"Turn {i}: {field} wrong type")
                
                # Check participant ID exists
                if 'ParticipantId' in turn and participant_ids:
                    if turn['ParticipantId'] not in participant_ids:
                        issues.append(f"Turn {i}: Unknown ParticipantId {turn['ParticipantId']}")
        
        return len(issues) == 0, issues

    def analyze_conversation_quality(self, data: Dict) -> Dict[str, Any]:
        """Analyze conversation quality metrics"""
        metrics = {
            'turn_count': 0,
            'avg_turn_length': 0,
            'speaker_alternation': 0,
            'empty_turns': 0,
            'very_short_turns': 0,
            'speaker_balance': 0
        }
        
        if 'Transcript' not in data:
            return metrics
        
        turns = data['Transcript']
        metrics['turn_count'] = len(turns)
        
        if not turns:
            return metrics
        
        # Calculate turn lengths
        turn_lengths = []
        empty_count = 0
        very_short_count = 0
        
        for turn in turns:
            content = turn.get('Content', '')
            word_count = len(content.split()) if content else 0
            turn_lengths.append(word_count)
            
            if word_count == 0:
                empty_count += 1
            elif word_count < 3:
                very_short_count += 1
        
        metrics['avg_turn_length'] = sum(turn_lengths) / len(turn_lengths) if turn_lengths else 0
        metrics['empty_turns'] = empty_count
        metrics['very_short_turns'] = very_short_count
        
        # Calculate speaker alternation
        speakers = [turn.get('ParticipantId', '') for turn in turns]
        alternations = sum(1 for i in range(1, len(speakers)) if speakers[i] != speakers[i-1])
        max_alternations = len(speakers) - 1
        metrics['speaker_alternation'] = alternations / max_alternations if max_alternations > 0 else 0
        
        # Calculate speaker balance
        speaker_counts = Counter(speakers)
        if len(speaker_counts) > 1:
            counts = list(speaker_counts.values())
            min_count, max_count = min(counts), max(counts)
            metrics['speaker_balance'] = min_count / max_count if max_count > 0 else 0
        
        return metrics

    def analyze_directory(self, directory: Path) -> QualityMetrics:
        """Analyze a directory of Lex conversation files"""
        print(f"\nAnalyzing directory: {directory}")
        
        # Get statistical sample
        sample_files = self.get_statistical_sample(directory)
        
        if not sample_files:
            return QualityMetrics(0, 0, 0, 0, 0, 0, {}, 0, ["No files found"])
        
        # Analysis results
        format_compliant = 0
        pii_detected_files = 0
        total_pii_instances = 0
        conversation_lengths = []
        turn_lengths = []
        speaker_roles = Counter()
        all_issues = []
        quality_scores = []
        
        print(f"Analyzing {len(sample_files)} files...")
        
        for i, file_path in enumerate(sample_files):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(sample_files)}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Format validation
                is_compliant, issues = self.validate_lex_format(data)
                if is_compliant:
                    format_compliant += 1
                else:
                    all_issues.extend([f"{file_path.name}: {issue}" for issue in issues])
                
                # PII detection
                file_pii_count = 0
                if 'Transcript' in data:
                    for turn in data['Transcript']:
                        content = turn.get('Content', '')
                        pii_found = self.detect_pii_in_text(content)
                        if pii_found:
                            file_pii_count += sum(len(matches) for matches in pii_found.values())
                
                if file_pii_count > 0:
                    pii_detected_files += 1
                    total_pii_instances += file_pii_count
                
                # Quality analysis
                quality_metrics = self.analyze_conversation_quality(data)
                conversation_lengths.append(quality_metrics['turn_count'])
                
                if quality_metrics['avg_turn_length'] > 0:
                    turn_lengths.append(quality_metrics['avg_turn_length'])
                
                # Calculate quality score (0-100)
                quality_score = 100
                quality_score -= quality_metrics['empty_turns'] * 5  # -5 per empty turn
                quality_score -= quality_metrics['very_short_turns'] * 2  # -2 per very short turn
                quality_score += quality_metrics['speaker_alternation'] * 20  # +20 for good alternation
                quality_score += quality_metrics['speaker_balance'] * 10  # +10 for balanced speakers
                quality_score = max(0, min(100, quality_score))
                quality_scores.append(quality_score)
                
                # Speaker roles
                if 'Participants' in data:
                    for participant in data['Participants']:
                        role = participant.get('ParticipantRole', 'UNKNOWN')
                        speaker_roles[role] += 1
                
            except Exception as e:
                all_issues.append(f"{file_path.name}: Parse error - {str(e)}")
        
        # Calculate final metrics
        total_files = len(list(directory.glob("**/*.json")))
        sample_size = len(sample_files)
        
        format_compliance = format_compliant / sample_size if sample_size > 0 else 0
        pii_detection_rate = pii_detected_files / sample_size if sample_size > 0 else 0
        avg_conversation_length = sum(conversation_lengths) / len(conversation_lengths) if conversation_lengths else 0
        avg_turn_length = sum(turn_lengths) / len(turn_lengths) if turn_lengths else 0
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return QualityMetrics(
            total_files=total_files,
            sample_size=sample_size,
            format_compliance=format_compliance,
            pii_detection_rate=pii_detection_rate,
            avg_conversation_length=avg_conversation_length,
            avg_turn_length=avg_turn_length,
            speaker_distribution=dict(speaker_roles),
            quality_score=overall_quality,
            issues=all_issues[:20]  # Top 20 issues
        )

    def generate_report(self, health_calls_metrics: QualityMetrics, lex_export_metrics: QualityMetrics):
        """Generate comprehensive analysis report with visualizations"""
        
        # Calculate Lex readiness confidence
        def calculate_confidence(metrics: QualityMetrics) -> float:
            confidence = 100
            
            # Format compliance (40% weight)
            confidence *= metrics.format_compliance * 0.4 + 0.6
            
            # PII detection penalty (20% weight) - lower is better
            pii_penalty = min(metrics.pii_detection_rate * 50, 20)  # Max 20% penalty
            confidence -= pii_penalty
            
            # Quality score (40% weight)
            confidence *= (metrics.quality_score / 100) * 0.4 + 0.6
            
            return max(0, min(100, confidence))
        
        health_confidence = calculate_confidence(health_calls_metrics)
        lex_confidence = calculate_confidence(lex_export_metrics)
        
        # Create comprehensive visualization
        fig = plt.figure(figsize=(16, 12))
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle('Lex Export Quality Analysis Report', fontsize=16, fontweight='bold')
        
        # 1. Confidence Scores
        ax1 = fig.add_subplot(gs[0, 0])
        datasets = ['Health Calls\nOutput', 'Lex Export']
        confidences = [health_confidence, lex_confidence]
        colors = ['#ff6b6b' if c < 70 else '#ffd93d' if c < 85 else '#6bcf7f' for c in confidences]
        
        bars = ax1.bar(datasets, confidences, color=colors, alpha=0.8)
        ax1.set_ylabel('Confidence %')
        ax1.set_title('Lex Readiness Confidence')
        ax1.set_ylim(0, 100)
        
        # Add confidence text on bars
        for bar, conf in zip(bars, confidences):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{conf:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # 2. Format Compliance
        ax2 = fig.add_subplot(gs[0, 1])
        compliance_data = [health_calls_metrics.format_compliance * 100, lex_export_metrics.format_compliance * 100]
        ax2.bar(datasets, compliance_data, color=['#4ecdc4', '#45b7d1'], alpha=0.8)
        ax2.set_ylabel('Compliance %')
        ax2.set_title('Lex v2 Format Compliance')
        ax2.set_ylim(0, 100)
        
        for i, v in enumerate(compliance_data):
            ax2.text(i, v + 1, f'{v:.1f}%', ha='center', va='bottom')
        
        # 3. PII Detection Rate
        ax3 = fig.add_subplot(gs[0, 2])
        pii_data = [health_calls_metrics.pii_detection_rate * 100, lex_export_metrics.pii_detection_rate * 100]
        colors_pii = ['#ff6b6b' if p > 10 else '#ffd93d' if p > 5 else '#6bcf7f' for p in pii_data]
        ax3.bar(datasets, pii_data, color=colors_pii, alpha=0.8)
        ax3.set_ylabel('PII Detection %')
        ax3.set_title('PII Leakage Rate (Lower is Better)')
        
        for i, v in enumerate(pii_data):
            ax3.text(i, v + 0.5, f'{v:.1f}%', ha='center', va='bottom')
        
        # 4. Conversation Length Distribution
        ax4 = fig.add_subplot(gs[1, 0])
        lengths = [health_calls_metrics.avg_conversation_length, lex_export_metrics.avg_conversation_length]
        ax4.bar(datasets, lengths, color=['#96ceb4', '#feca57'], alpha=0.8)
        ax4.set_ylabel('Average Turns')
        ax4.set_title('Average Conversation Length')
        
        for i, v in enumerate(lengths):
            ax4.text(i, v + 0.5, f'{v:.1f}', ha='center', va='bottom')
        
        # 5. Turn Length Quality
        ax5 = fig.add_subplot(gs[1, 1])
        turn_lengths = [health_calls_metrics.avg_turn_length, lex_export_metrics.avg_turn_length]
        ax5.bar(datasets, turn_lengths, color=['#ff9ff3', '#54a0ff'], alpha=0.8)
        ax5.set_ylabel('Average Words per Turn')
        ax5.set_title('Turn Length Quality')
        
        for i, v in enumerate(turn_lengths):
            ax5.text(i, v + 0.5, f'{v:.1f}', ha='center', va='bottom')
        
        # 6. Speaker Role Distribution
        ax6 = fig.add_subplot(gs[1, 2])
        
        # Combine speaker distributions
        all_roles = set(health_calls_metrics.speaker_distribution.keys()) | set(lex_export_metrics.speaker_distribution.keys())
        health_roles = [health_calls_metrics.speaker_distribution.get(role, 0) for role in all_roles]
        lex_roles = [lex_export_metrics.speaker_distribution.get(role, 0) for role in all_roles]
        
        x = np.arange(len(all_roles))
        width = 0.35
        
        ax6.bar(x - width/2, health_roles, width, label='Health Calls', alpha=0.8)
        ax6.bar(x + width/2, lex_roles, width, label='Lex Export', alpha=0.8)
        
        ax6.set_ylabel('Count')
        ax6.set_title('Speaker Role Distribution')
        ax6.set_xticks(x)
        ax6.set_xticklabels(list(all_roles), rotation=45)
        ax6.legend()
        
        # 7. Quality Score Comparison
        ax7 = fig.add_subplot(gs[2, 0])
        quality_scores = [health_calls_metrics.quality_score, lex_export_metrics.quality_score]
        colors_quality = ['#ff6b6b' if q < 60 else '#ffd93d' if q < 80 else '#6bcf7f' for q in quality_scores]
        ax7.bar(datasets, quality_scores, color=colors_quality, alpha=0.8)
        ax7.set_ylabel('Quality Score')
        ax7.set_title('Overall Quality Score')
        ax7.set_ylim(0, 100)
        
        for i, v in enumerate(quality_scores):
            ax7.text(i, v + 1, f'{v:.1f}', ha='center', va='bottom')
        
        # 8. Sample Size Information
        ax8 = fig.add_subplot(gs[2, 1])
        sample_sizes = [health_calls_metrics.sample_size, lex_export_metrics.sample_size]
        total_sizes = [health_calls_metrics.total_files, lex_export_metrics.total_files]
        
        ax8.bar(datasets, total_sizes, alpha=0.5, label='Total Files', color='lightgray')
        ax8.bar(datasets, sample_sizes, alpha=0.8, label='Sample Size', color=['#e17055', '#74b9ff'])
        ax8.set_ylabel('File Count')
        ax8.set_title('Sample Coverage')
        ax8.legend()
        
        for i, (sample, total) in enumerate(zip(sample_sizes, total_sizes)):
            coverage = (sample / total * 100) if total > 0 else 0
            ax8.text(i, sample + total * 0.02, f'{coverage:.1f}%\ncoverage', ha='center', va='bottom', fontsize=9)
        
        # 9. Summary Text
        ax9 = fig.add_subplot(gs[2, 2])
        ax9.axis('off')
        
        summary_text = f"""
ANALYSIS SUMMARY

Health Calls Output:
• {health_calls_metrics.total_files:,} total files
• {health_calls_metrics.sample_size} analyzed
• {health_confidence:.1f}% Lex readiness

Lex Export:
• {lex_export_metrics.total_files:,} total files  
• {lex_export_metrics.sample_size} analyzed
• {lex_confidence:.1f}% Lex readiness

RECOMMENDATION:
"""
        
        if min(health_confidence, lex_confidence) >= 85:
            recommendation = "✅ READY FOR LEX\nHigh confidence for production use"
            color = 'green'
        elif min(health_confidence, lex_confidence) >= 70:
            recommendation = "⚠️ NEEDS MINOR FIXES\nAddress format/PII issues"
            color = 'orange'
        else:
            recommendation = "❌ NOT READY\nSignificant issues need resolution"
            color = 'red'
        
        summary_text += recommendation
        
        ax9.text(0.05, 0.95, summary_text, transform=ax9.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace')
        
        ax9.text(0.05, 0.25, recommendation, transform=ax9.transAxes, fontsize=12,
                verticalalignment='top', fontweight='bold', color=color,
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.2))
        
        plt.tight_layout()
        plt.show()
        
        # Print detailed text report
        print("\n" + "="*80)
        print("DETAILED ANALYSIS REPORT")
        print("="*80)
        
        for name, metrics in [("Health Calls Output", health_calls_metrics), ("Lex Export", lex_export_metrics)]:
            confidence = calculate_confidence(metrics)
            print(f"\n{name.upper()}:")
            print(f"  Total Files: {metrics.total_files:,}")
            print(f"  Sample Size: {metrics.sample_size}")
            print(f"  Format Compliance: {metrics.format_compliance*100:.1f}%")
            print(f"  PII Detection Rate: {metrics.pii_detection_rate*100:.1f}%")
            print(f"  Avg Conversation Length: {metrics.avg_conversation_length:.1f} turns")
            print(f"  Avg Turn Length: {metrics.avg_turn_length:.1f} words")
            print(f"  Quality Score: {metrics.quality_score:.1f}/100")
            print(f"  LEX READINESS CONFIDENCE: {confidence:.1f}%")
            
            if metrics.issues:
                print(f"  Top Issues:")
                for issue in metrics.issues[:5]:
                    print(f"    • {issue}")
        
        print(f"\n{'='*80}")
        print("FINAL RECOMMENDATION:")
        
        overall_confidence = (health_confidence + lex_confidence) / 2
        
        if overall_confidence >= 85:
            print("✅ READY FOR LEX DEPLOYMENT")
            print("Both datasets show high quality and compliance. Safe for production use.")
        elif overall_confidence >= 70:
            print("⚠️ READY WITH MINOR FIXES")
            print("Good quality overall, but address format compliance and PII issues before deployment.")
        else:
            print("❌ NOT READY FOR LEX")
            print("Significant quality issues detected. Requires substantial fixes before deployment.")
        
        print(f"\nOverall Confidence: {overall_confidence:.1f}%")
        print("="*80)

def main():
    analyzer = LexQualityAnalyzer()
    
    # Analyze both directories
    health_calls_dir = Path("Training Datasets/health-calls-output")
    lex_export_dir = Path("lex_export")
    
    print("Starting Lex Export Quality Analysis...")
    print("This will analyze a statistically meaningful sample from both directories.")
    
    health_metrics = analyzer.analyze_directory(health_calls_dir)
    lex_metrics = analyzer.analyze_directory(lex_export_dir)
    
    # Generate comprehensive report
    analyzer.generate_report(health_metrics, lex_metrics)

if __name__ == "__main__":
    main()