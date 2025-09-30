#!/usr/bin/env python3
"""
Conversation Grader - Modular grading system for conversations
"""

import json
import csv
import os
import time
import sys
from datetime import datetime
from pathlib import Path

# Work around broken ai-catalyst imports
try:
    from ai_catalyst.llm.provider import LLMProvider
    from ai_catalyst.data.pii.processor import PIIProcessor
    from ai_catalyst.config.manager import ConfigManager
    from ai_catalyst.database.manager import DatabaseManager
except ImportError as e:
    print(f"Warning: ai-catalyst import failed: {e}")
    print("Using fallback imports...")
    # Fallback to basic functionality
    LLMProvider = None
    PIIProcessor = None
    ConfigManager = None
    DatabaseManager = None

# Remove the broken AIGrader import for now
# from ai_catalyst.llm.grader import ConversationGrader as AIGrader


class ConversationGrader:
    def __init__(self, db_config=None):
        self.db_config = db_config or {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        
        # Initialize AI_Catalyst components
        self.db_manager = DatabaseManager(self.db_config)
        self.config_manager = ConfigManager()
        self.ai_grader = AIGrader(self.db_manager, self.config_manager)
        
        # Load grader configuration
        self.grader_config = self.load_grader_config()
    
    def get_db(self):
        """Get database connection"""
        return self.db_manager.get_connection()
    
    def load_grader_config(self):
        """Load grader configuration from config file"""
        return self.config_manager.get_config('grader', {})
    
    def save_grader_config(self, config):
        """Save grader configuration to config file"""
        self.config_manager.set_config('grader', config)
        self.grader_config = config
    
    def discover_local_endpoints(self):
        """Discover local LLM endpoints"""
        return self.ai_grader.llm_provider.endpoint_discovery.discover_endpoints()
    
    def grade_conversation(self, conversation_text, conversation_id=None, grader_type="openai"):
        """Grade a single conversation using specified grader type"""
        return self.ai_grader.grade_conversation(conversation_text, conversation_id, grader_type)
    

    
    def grade_csv_files(self, csv_files, output_file=None, rate_limit_delay=2):
        """Grade conversations from CSV files"""
        print(f"Grading conversations from {len(csv_files)} CSV files...")
        
        # Prepare output
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_csv = open(output_path, 'w', newline='', encoding='utf-8')
            writer = csv.writer(output_csv)
            writer.writerow([
                "source_file", "trial_id", "timestamp", "model", "trial",
                "realness_score", "coherence_score", "naturalness_score", 
                "overall_score", "brief_feedback", "grading_error"
            ])
        
        total_graded = 0
        
        try:
            for csv_file in csv_files:
                print(f"Processing: {csv_file}")
                
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        # Extract conversation content
                        conversation_text = row.get('sample_output', '') or row.get('content', '')
                        
                        if not conversation_text.strip():
                            continue
                        
                        # Grade conversation
                        grades = self.grade_conversation(conversation_text)
                        
                        # Write to output
                        if output_file:
                            writer.writerow([
                                Path(csv_file).name,
                                row.get('trial_id', ''),
                                datetime.now().isoformat(),
                                row.get('model', ''),
                                row.get('trial', ''),
                                grades.get("realness_score"),
                                grades.get("coherence_score"),
                                grades.get("naturalness_score"),
                                grades.get("overall_score"),
                                grades.get("brief_feedback", ""),
                                grades.get("grading_error", "")
                            ])
                        
                        total_graded += 1
                        
                        if grades.get("grading_error"):
                            print(f"  Error: {grades['grading_error']}")
                        else:
                            print(f"  Graded: R={grades.get('realness_score')}, O={grades.get('overall_score')}")
                        
                        # Rate limiting
                        time.sleep(rate_limit_delay)
        
        finally:
            if output_file:
                output_csv.close()
        
        print(f"Completed grading {total_graded} conversations")
        return total_graded
    

    
    def grade_database_conversations(self, machine_name=None, job_ids=None, limit=None, grader_type="openai"):
        """Grade conversations from database"""
        print(f"Grading conversations from database using {grader_type} grader...")
        
        conn = self.get_db()
        cur = conn.cursor()
        
        # Build query conditions
        conditions = []
        params = []
        
        if machine_name:
            # Find conversations generated by specific machine
            conditions.append("EXISTS (SELECT 1 FROM nodes n JOIN jobs j ON j.assigned_node_id = n.id WHERE j.id = c.job_id AND n.hostname = %s)")
            params.append(machine_name)
        
        if job_ids:
            placeholders = ','.join(['%s'] * len(job_ids))
            conditions.append(f"c.job_id IN ({placeholders})")
            params.extend(job_ids)
        
        # Only grade conversations that haven't been graded yet
        conditions.append("NOT EXISTS (SELECT 1 FROM conversation_grades WHERE conversation_id = c.id)")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
            SELECT c.id, c.content, c.model_name, j.id as job_id
            FROM conversations c
            JOIN jobs j ON j.id = c.job_id
            WHERE {where_clause}
            ORDER BY c.created_at DESC
            {limit_clause}
        """
        
        cur.execute(query, params)
        conversations = cur.fetchall()
        
        print(f"Found {len(conversations)} conversations to grade")
        
        graded_count = 0
        
        for conv_id, content, model_name, job_id in conversations:
            # Process each conversation in its own transaction
            try:
                # Start new transaction for each conversation
                conn.rollback()  # Clear any previous errors
                
                content_data = json.loads(content) if isinstance(content, str) else content
                
                # Extract conversation from Contact Lens format
                conversation_text = ""
                if "Transcript" in content_data:
                    for turn in content_data["Transcript"]:
                        conversation_text += f"{turn.get('Content', '')}\n"
                else:
                    conversation_text = str(content_data)
                
                if not conversation_text.strip():
                    continue
                
                # Grade conversation
                grades = self.grade_conversation(conversation_text, conv_id, grader_type)
                
                # Store grades in database using AI_Catalyst
                if not grades.get("deleted", False):
                    self.ai_grader.store_grades(conv_id, grades)
                    conn.commit()
                
                graded_count += 1
                

                
                if grades.get("grading_error"):
                    print(f"  Error grading {conv_id[:8]}: {grades['grading_error']}")
                else:
                    print(f"  Graded {conv_id[:8]}: R={grades.get('realness_score')}, O={grades.get('overall_score')}")
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"  Error processing conversation {conv_id[:8]}: {e}")
                conn.rollback()  # Rollback failed transaction
                continue
        
        # Final commit handled per conversation above
        cur.close()
        conn.close()
        
        print(f"Completed grading {graded_count} conversations")
        return graded_count
    
    def setup_grading_schema(self):
        """Setup conversation_grades table"""
        conn = self.get_db()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_grades (
                id UUID PRIMARY KEY,
                conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                realness_score INTEGER,
                coherence_score INTEGER,
                naturalness_score INTEGER,
                overall_score INTEGER,
                healthcare_valid BOOLEAN,
                brief_feedback TEXT,
                grading_error TEXT,
                graded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(conversation_id)
            )
        """)
        
        # Check if table has correct schema and fix if needed
        try:
            # Test if all required columns exist
            cur.execute("SELECT healthcare_valid, brief_feedback FROM conversation_grades LIMIT 0")
            print("[SCHEMA] conversation_grades table schema is correct")
        except Exception as schema_error:
            print(f"[SCHEMA ERROR] Table exists but schema is incorrect: {schema_error}")
            print("[SCHEMA] Attempting to add missing columns...")
            
            # Try to add missing columns
            columns_to_add = [
                ("healthcare_valid", "BOOLEAN"),
                ("brief_feedback", "TEXT")
            ]
            
            for column_name, column_type in columns_to_add:
                try:
                    cur.execute(f"ALTER TABLE conversation_grades ADD COLUMN {column_name} {column_type}")
                    print(f"[SCHEMA] Successfully added column: {column_name}")
                except Exception as add_error:
                    if "already exists" in str(add_error).lower():
                        print(f"[SCHEMA] Column {column_name} already exists")
                    else:
                        print(f"[SCHEMA ERROR] Failed to add column {column_name}: {add_error}")
                        raise Exception(f"Cannot fix conversation_grades schema. Please run drop_grades_table.py and try again. Error: {add_error}")
        
        # Create index for faster lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_grades_conversation_id 
            ON conversation_grades(conversation_id)
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("[SCHEMA] Grading schema setup complete")
    
    def delete_invalid_conversation(self, conversation_id):
        """Delete conversation that failed healthcare validation"""
        self.ai_grader._delete_invalid_conversation(conversation_id)

def main():
    """CLI interface for grader"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Grade conversations")
    parser.add_argument("--mode", choices=["csv", "database"], help="Grading mode")
    parser.add_argument("--csv-files", nargs="+", help="CSV files to grade")
    parser.add_argument("--output", help="Output CSV file for grades")
    parser.add_argument("--machine", help="Grade conversations from specific machine")
    parser.add_argument("--limit", type=int, help="Limit number of conversations to grade")
    parser.add_argument("--setup-schema", action="store_true", help="Setup grading database schema")
    
    args = parser.parse_args()
    
    grader = ConversationGrader()
    
    if args.setup_schema:
        grader.setup_grading_schema()
        return
    
    if not args.mode:
        print("Error: --mode required unless using --setup-schema")
        return
    
    if args.mode == "csv":
        if not args.csv_files:
            print("Error: --csv-files required for CSV mode")
            return
        
        grader.grade_csv_files(args.csv_files, args.output)
    
    elif args.mode == "database":
        grader.grade_database_conversations(
            machine_name=args.machine,
            limit=args.limit
        )

if __name__ == "__main__":
    main()