#!/usr/bin/env python3
"""
Misplaced PII Fix - Corrects PII placeholders used as symptoms/objects
"""

import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Detection patterns for misplaced PII
MISPLACED_PATTERNS = [
    # After adjectives
    r'(?:persistent|chronic|severe|mild|nagging|sharp|dull|recurring)\s+<(NAME|PHONE|EMAIL|DATE|ADDRESS|ID|INSURANCEID)>',
    # After articles
    r'\b(a|an|the)\s+<(NAME|PHONE|EMAIL|DATE|ADDRESS|ID|INSURANCEID)>',
    # After medical cues
    r'(pain|cough|rash|fever|symptom|headache|migraine|ache|soreness)\s+(?:in|with|from)?\s*<(NAME|PHONE|EMAIL|DATE|ADDRESS|ID|INSURANCEID)>'
]

# Valid PII contexts (should NOT be changed)
PII_ALLOWLIST = [
    r'my name is\s+<NAME>',
    r'this is\s+<NAME>',
    r'I am\s+<NAME>',
    r'call me\s+<NAME>',
    r'phone number\s+(?:is\s+)?<PHONE>',
    r'contact number\s+(?:is\s+)?<PHONE>',
    r'email\s+(?:is\s+)?<EMAIL>',
    r'DOB\s+(?:is\s+)?<DATE>',
    r'date of birth\s+(?:is\s+)?<DATE>',
    r'policy number\s+(?:is\s+)?<ID>',
    r'member ID\s+(?:is\s+)?<ID>',
    r'MRN\s+(?:is\s+)?<ID>',
    r'address\s+(?:is\s+)?<ADDRESS>'
]

def is_in_allowlist(text: str, match_start: int) -> bool:
    """Check if match is within an allowlisted context (4 tokens left)"""
    # Get 4 tokens before the match
    before_text = text[:match_start].split()[-4:]
    context = ' '.join(before_text + [text[match_start:match_start+20]])
    
    for pattern in PII_ALLOWLIST:
        if re.search(pattern, context, re.IGNORECASE):
            return True
    return False

def detect_misplaced_pii(content: str) -> List[Tuple[int, int, str, str]]:
    """Detect misplaced PII placeholders. Returns (start, end, old, new) tuples"""
    fixes = []
    
    for pattern in MISPLACED_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            if not is_in_allowlist(content, match.start()):
                old_text = match.group(0)
                
                # Determine replacement based on context
                if any(word in pattern.lower() for word in ['pain', 'cough', 'rash', 'fever', 'symptom', 'headache', 'migraine', 'ache', 'soreness']):
                    new_placeholder = '<SYMPTOM>'
                else:
                    new_placeholder = '<ITEM>'
                
                # Handle article agreement for "a/an"
                if match.group(1) and match.group(1).lower() in ['a', 'an']:
                    article = 'an' if new_placeholder.startswith('<I') else 'a'
                    new_text = old_text.replace(f'{match.group(1)} <{match.group(2)}>', f'{article} {new_placeholder}')
                else:
                    # Replace the placeholder part
                    placeholder_match = re.search(r'<(NAME|PHONE|EMAIL|DATE|ADDRESS|ID|INSURANCEID)>', old_text)
                    if placeholder_match:
                        new_text = old_text.replace(placeholder_match.group(0), new_placeholder)
                    else:
                        continue
                
                fixes.append((match.start(), match.end(), old_text, new_text))
    
    return fixes

def fix_conversation(conv_data: Dict) -> Tuple[Dict, List[Dict]]:
    """Fix misplaced PII in conversation. Returns (fixed_data, changes)"""
    changes = []
    
    for turn in conv_data.get('Transcript', []):
        if isinstance(turn, dict) and 'Content' in turn:
            content = turn['Content']
            fixes = detect_misplaced_pii(content)
            
            if fixes:
                # Apply fixes in reverse order to maintain positions
                new_content = content
                for start, end, old_text, new_text in reversed(fixes):
                    new_content = new_content[:start] + new_text + new_content[end:]
                    
                    changes.append({
                        'id': turn.get('Id', 'unknown'),
                        'before': old_text,
                        'after': new_text
                    })
                
                turn['Content'] = new_content
    
    return conv_data, changes

def process_file(input_path: Path, output_path: Path = None, dry_run: bool = False) -> Dict:
    """Process single file"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        fixed_data, changes = fix_conversation(data)
        
        result = {
            'file': str(input_path),
            'utterances_scanned': len(data.get('Transcript', [])),
            'utterances_corrected': len(changes),
            'examples': changes[:3],  # First 3 examples
            'skipped_due_to_allowlist': 0  # Would need more complex tracking
        }
        
        if not dry_run and changes:
            output_file = output_path or input_path
            if output_path != input_path:
                output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        
        return result
        
    except Exception as e:
        return {
            'file': str(input_path),
            'error': str(e),
            'utterances_scanned': 0,
            'utterances_corrected': 0,
            'examples': [],
            'skipped_due_to_allowlist': 0
        }

def main():
    parser = argparse.ArgumentParser(description='Fix misplaced PII placeholders')
    parser.add_argument('input', help='Input directory')
    parser.add_argument('--output', help='Output directory (default: in-place)')
    parser.add_argument('--dry-run', action='store_true', help='Report only, no changes')
    parser.add_argument('--report', help='Report file path')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output) if args.output else None
    
    if not input_dir.exists():
        print(f"ERROR: Input directory {input_dir} does not exist")
        return 1
    
    # Find all JSON files
    json_files = list(input_dir.glob('**/*.json'))
    if not json_files:
        print("No JSON files found")
        return 0
    
    print(f"Processing {len(json_files)} files...")
    
    results = []
    total_scanned = 0
    total_corrected = 0
    
    for json_file in json_files:
        if output_dir:
            rel_path = json_file.relative_to(input_dir)
            output_file = output_dir / rel_path
        else:
            output_file = json_file
        
        result = process_file(json_file, output_file, args.dry_run)
        results.append(result)
        
        if 'error' not in result:
            total_scanned += result['utterances_scanned']
            total_corrected += result['utterances_corrected']
            
            if result['utterances_corrected'] > 0:
                print(f"Fixed {result['utterances_corrected']} utterances in {json_file.name}")
    
    # Summary
    print(f"\nSummary:")
    print(f"  Files processed: {len([r for r in results if 'error' not in r])}")
    print(f"  Total utterances scanned: {total_scanned}")
    print(f"  Total corrections made: {total_corrected}")
    
    # Show sample fixes
    if total_corrected > 0:
        print(f"\nSample fixes:")
        count = 0
        for result in results:
            if 'examples' in result:
                for example in result['examples']:
                    if count < 3:
                        print(f"  '{example['before']}' -> '{example['after']}')")
                        count += 1
    
    # Write report
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'files_processed': len(results),
                    'total_scanned': total_scanned,
                    'total_corrected': total_corrected
                },
                'files': results
            }, f, indent=2, ensure_ascii=False)
        print(f"Report written to {args.report}")
    
    return 0

if __name__ == '__main__':
    exit(main())