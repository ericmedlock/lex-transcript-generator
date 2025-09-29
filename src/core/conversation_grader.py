#!/usr/bin/env python3
"""
Conversation Grader - Modular grading system for conversations
"""

import json
import csv
import os
import time
import psycopg2
from psycopg2 import errors
import uuid
import requests
from datetime import datetime
from pathlib import Path
from openai import OpenAI


class ConversationGrader:
    def __init__(self, db_config=None):
        self.db_config = db_config or {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        
        # Initialize OpenAI client
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None
        
        # Load grader configuration
        self.grader_config = self.load_grader_config()
        
        if not self.openai_client:
            print("Warning: No OpenAI API key found, OpenAI grading will be unavailable")
    
    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def load_grader_config(self):
        """Load grader configuration from config file"""
        config_path = Path(__file__).parent.parent.parent / "config" / "config.json"
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('grader', {})
        except:
            return {}
    
    def save_grader_config(self, config):
        """Save grader configuration to config file"""
        config_path = Path(__file__).parent.parent.parent / "config" / "config.json"
        try:
            with open(config_path, 'r') as f:
                full_config = json.load(f)
            full_config['grader'] = config
            with open(config_path, 'w') as f:
                json.dump(full_config, f, indent=2)
            self.grader_config = config
        except Exception as e:
            print(f"Error saving grader config: {e}")
    
    def discover_local_endpoints(self):
        """Discover local LLM endpoints"""
        endpoints = []
        ports = [8000, 8080, 11434, 5000, 7860, 1234]
        
        for port in ports:
            try:
                response = requests.get(f"http://localhost:{port}/v1/models", timeout=2)
                if response.status_code == 200:
                    endpoints.append(f"http://localhost:{port}/v1")
            except:
                continue
        
        return endpoints
    
    def grade_conversation(self, conversation_text, conversation_id=None, grader_type="openai"):
        """Grade a single conversation using specified grader type"""
        if grader_type == "local":
            return self.grade_conversation_local(conversation_text, conversation_id)
        elif grader_type == "network":
            return self.grade_conversation_network(conversation_text, conversation_id)
        elif grader_type == "openai":
            return self.grade_conversation_openai(conversation_text, conversation_id)
        else:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": f"Unknown grader type: {grader_type}"
            }
    
    def grade_conversation_local(self, conversation_text, conversation_id=None):
        """Grade using local LLM endpoint"""
        endpoints = self.discover_local_endpoints()
        if not endpoints:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": "No local LLM endpoints found"
            }
        
        return self._grade_with_endpoint(endpoints[0], conversation_text, conversation_id)
    
    def grade_conversation_network(self, conversation_text, conversation_id=None):
        """Grade using network LLM endpoint"""
        network_url = self.grader_config.get('network_url')
        if not network_url:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": "No network grader URL configured"
            }
        
        return self._grade_with_endpoint(network_url, conversation_text, conversation_id)
    
    def grade_conversation_openai(self, conversation_text, conversation_id=None):
        """Grade a single conversation using OpenAI with healthcare validation"""
        if not self.openai_client:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": "No OpenAI API key configured"
            }
        
        try:
            grading_prompt = f"""Grade this AI-generated conversation on a scale of 1-10 for each metric:

1. REALNESS: How realistic and believable is this conversation? (1=obviously AI, 10=indistinguishable from human)
2. COHERENCE: How well does the conversation flow logically? (1=nonsensical, 10=perfect flow)
3. NATURALNESS: How natural do the speech patterns sound? (1=robotic, 10=completely natural)
4. OVERALL: Overall quality for training chatbot systems (1=unusable, 10=excellent training data)
5. HEALTHCARE_VALID: Is this actually a healthcare appointment conversation? (true/false)

Conversation to grade:
{conversation_text[:2000]}...

Respond ONLY with JSON format:
{{
  "realness_score": X,
  "coherence_score": X,
  "naturalness_score": X,
  "overall_score": X,
  "healthcare_valid": true/false,
  "brief_feedback": "one sentence explanation"
}}"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": grading_prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean JSON response
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            try:
                grades = json.loads(result_text)
                grades["grading_error"] = None
                
                # Delete conversation if not healthcare valid or low realness score
                should_delete = False
                if grades.get("healthcare_valid") == False and conversation_id:
                    should_delete = True
                    grades["delete_reason"] = "not_healthcare"
                elif grades.get("realness_score") and grades.get("realness_score") < getattr(self, 'min_realness_score', 6) and conversation_id:
                    should_delete = True
                    grades["delete_reason"] = f"low_realness_{grades.get('realness_score')}"
                
                if should_delete:
                    self.delete_invalid_conversation(conversation_id)
                    grades["deleted"] = True
                
                return grades
            except json.JSONDecodeError:
                return {
                    "realness_score": None,
                    "coherence_score": None,
                    "naturalness_score": None,
                    "overall_score": None,
                    "healthcare_valid": None,
                    "grading_error": f"Invalid JSON: {result_text[:100]}"
                }
                
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "invalid_api_key" in error_msg:
                error_msg = "Invalid OpenAI API key - check OPENAI_API_KEY environment variable"
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": error_msg
            }
    
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
    
    def _grade_with_endpoint(self, endpoint_url, conversation_text, conversation_id=None):
        """Grade conversation using OpenAI-compatible endpoint"""
        try:
            grading_prompt = f"""Grade this AI-generated conversation on a scale of 1-10 for each metric:

1. REALNESS: How realistic and believable is this conversation? (1=obviously AI, 10=indistinguishable from human)
2. COHERENCE: How well does the conversation flow logically? (1=nonsensical, 10=perfect flow)
3. NATURALNESS: How natural do the speech patterns sound? (1=robotic, 10=completely natural)
4. OVERALL: Overall quality for training chatbot systems (1=unusable, 10=excellent training data)
5. HEALTHCARE_VALID: Is this actually a healthcare appointment conversation? (true/false)

Conversation to grade:
{conversation_text[:2000]}...

Respond ONLY with JSON format:
{{
  "realness_score": X,
  "coherence_score": X,
  "naturalness_score": X,
  "overall_score": X,
  "healthcare_valid": true/false,
  "brief_feedback": "one sentence explanation"
}}"""
            
            response = requests.post(
                f"{endpoint_url}/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": grading_prompt}],
                    "temperature": 0.1,
                    "max_tokens": 200
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {
                    "realness_score": None,
                    "coherence_score": None,
                    "naturalness_score": None,
                    "overall_score": None,
                    "healthcare_valid": None,
                    "grading_error": f"HTTP {response.status_code}: {response.text}"
                }
            
            result_text = response.json()["choices"][0]["message"]["content"].strip()
            
            # Clean JSON response
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.startswith('```'):
                result_text = result_text[3:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            try:
                grades = json.loads(result_text)
                grades["grading_error"] = None
                
                # Delete conversation if not healthcare valid or low realness score
                should_delete = False
                if grades.get("healthcare_valid") == False and conversation_id:
                    should_delete = True
                    grades["delete_reason"] = "not_healthcare"
                elif grades.get("realness_score") and grades.get("realness_score") < getattr(self, 'min_realness_score', 6) and conversation_id:
                    should_delete = True
                    grades["delete_reason"] = f"low_realness_{grades.get('realness_score')}"
                
                if should_delete:
                    self.delete_invalid_conversation(conversation_id)
                    grades["deleted"] = True
                
                return grades
            except json.JSONDecodeError:
                return {
                    "realness_score": None,
                    "coherence_score": None,
                    "naturalness_score": None,
                    "overall_score": None,
                    "healthcare_valid": None,
                    "grading_error": f"Invalid JSON: {result_text[:100]}"
                }
                
        except Exception as e:
            return {
                "realness_score": None,
                "coherence_score": None,
                "naturalness_score": None,
                "overall_score": None,
                "healthcare_valid": None,
                "grading_error": str(e)
            }
    
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
                
                # Store grades in database
                grade_id = str(uuid.uuid4())
                # Only store grades if conversation wasn't deleted
                if not grades.get("deleted", False):
                    cur.execute("""
                        INSERT INTO conversation_grades 
                        (id, conversation_id, realness_score, coherence_score, naturalness_score, 
                         overall_score, healthcare_valid, brief_feedback, grading_error, graded_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        grade_id, conv_id,
                        grades.get("realness_score"),
                        grades.get("coherence_score"), 
                        grades.get("naturalness_score"),
                        grades.get("overall_score"),
                        grades.get("healthcare_valid"),
                        grades.get("brief_feedback", ""),
                        grades.get("grading_error", ""),
                        datetime.now()
                    ))
                    
                    # Commit this conversation's grade
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
        try:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Delete from conversations table (cascade will handle grades)
            cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"  Deleted invalid conversation: {conversation_id[:8]}")
        except Exception as e:
            print(f"  Error deleting conversation {conversation_id[:8]}: {e}")

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