#!/usr/bin/env python3
"""
RAG Preprocessor - Process Kaggle call records for RAG ingestion
"""

import os
import json
import psycopg2
from pathlib import Path
import uuid
from datetime import datetime
import requests

class RAGPreprocessor:
    def __init__(self):
        self.db_config = {
            'host': 'EPM_DELL',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        
        # Initialize LM Studio for embeddings
        self.embedding_endpoint = "http://localhost:1234/v1"
        self.embedding_model = self.detect_embedding_model()
        
        if not self.embedding_model:
            raise RuntimeError(
                "No embedding model found in LM Studio. "
                "Please load an embedding model (e.g., nomic-embed-text-v1.5) in LM Studio first."
            )
    
    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def chunk_text(self, text, chunk_size=500, overlap=50):
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks
    
    def detect_embedding_model(self):
        """Detect available embedding model in LM Studio"""
        try:
            import requests
            response = requests.get(f"{self.embedding_endpoint}/models", timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                
                # Look for embedding models
                for model in models:
                    model_name = model["id"].lower()
                    if any(embed_type in model_name for embed_type in 
                           ['embedding', 'embed', 'nomic-embed', 'bge-', 'e5-']):
                        print(f"Found embedding model: {model['id']}")
                        return model["id"]
                
                print(f"Available models: {[m['id'] for m in models]}")
                return None
        except Exception as e:
            print(f"Error detecting embedding model: {e}")
            return None
    
    def generate_embedding(self, text):
        """Generate embedding using LM Studio"""
        try:
            import requests
            
            response = requests.post(
                f"{self.embedding_endpoint}/embeddings",
                json={
                    "model": self.embedding_model,
                    "input": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["data"][0]["embedding"]
            else:
                print(f"Embedding API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
    
    def load_translator(self, file_path):
        """Load appropriate translator for file type"""
        if file_path.suffix == '.json':
            try:
                # Check if it's AWS Transcribe format
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'results' in data and ('transcripts' in data['results'] or 'speaker_labels' in data['results']):
                        import sys
                        import os
                        sys.path.append(os.path.join(os.path.dirname(__file__), 'translators'))
                        from aws_transcribe_translator import AWSTranscribeTranslator
                        return AWSTranscribeTranslator()
            except Exception as e:
                print(f"Error checking file format: {e}")
        
        return None
    
    def process_kaggle_directory(self, directory_path, sample_size=None):
        """Process Kaggle health directory with JSON files"""
        print(f"Processing Kaggle directory: {directory_path}")
        
        directory = Path(directory_path)
        if not directory.exists():
            print(f"Directory not found: {directory_path}")
            return
        
        # Find numeric subdirectories (21, 22, 25, etc.)
        subdirs = [d for d in directory.iterdir() if d.is_dir() and d.name.isdigit()]
        
        if not subdirs:
            print("No numeric subdirectories found")
            return
        
        print(f"Found subdirectories: {[d.name for d in subdirs]}")
        
        conn = self.get_db()
        cur = conn.cursor()
        
        total_chunks = 0
        processed_files = 0
        
        for subdir in subdirs:
            print(f"Processing directory: {subdir.name}")
            
            # Find JSON files
            json_files = list(subdir.glob("*.json"))
            
            if sample_size:
                json_files = json_files[:sample_size]
                print(f"Using sample of {len(json_files)} files from {subdir.name}")
            
            for json_file in json_files:
                print(f"Processing file: {json_file.name}")
                
                # Load translator
                translator = self.load_translator(json_file)
                if not translator:
                    print(f"No translator found for {json_file}")
                    continue
                
                try:
                    # Translate file
                    translated_data = translator.translate(json_file)
                    conversation_text = translated_data.get("conversation_text", "")
                    
                    if not conversation_text.strip():
                        continue
                    
                    # Register source file
                    source_id = str(uuid.uuid4())
                    cur.execute(
                        "INSERT INTO rag_sources (id, file_path, file_type, metadata) VALUES (%s, %s, %s, %s)",
                        (source_id, str(json_file), "aws_transcribe_json", json.dumps(translated_data["metadata"]))
                    )
                    
                    # Create chunks
                    chunks = self.chunk_text(conversation_text)
                    
                    for chunk_idx, chunk in enumerate(chunks):
                        # Generate embedding
                        embedding = self.generate_embedding(chunk)
                        
                        # Store chunk
                        chunk_id = str(uuid.uuid4())
                        metadata = {
                            "source_file": json_file.name,
                            "source_directory": subdir.name,
                            "job_name": translated_data.get("job_name", ""),
                            "speaker_count": translated_data.get("speaker_count", 0),
                            "turn_count": translated_data.get("turn_count", 0),
                            "duration": translated_data.get("duration", 0),
                            "chunk_length": len(chunk)
                        }
                        
                        cur.execute(
                            """INSERT INTO document_chunks 
                               (id, source_file, chunk_index, content, embedding, metadata) 
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            (chunk_id, str(json_file), chunk_idx, chunk, embedding, json.dumps(metadata))
                        )
                        
                        total_chunks += 1
                    
                    processed_files += 1
                    
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
                    continue
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Processed {processed_files} files, created {total_chunks} chunks")
    
    def search_similar(self, query, limit=5):
        """Search for similar content using vector similarity"""
        if not self.embedding_model:
            print("No embedding model available for similarity search")
            return []
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        if not query_embedding:
            return []
        
        conn = self.get_db()
        cur = conn.cursor()
        
        # Vector similarity search - convert to list for PostgreSQL
        embedding_list = query_embedding if isinstance(query_embedding, list) else list(query_embedding)
        
        cur.execute(
            """SELECT content, metadata, embedding <=> %s::vector as distance 
               FROM document_chunks 
               WHERE embedding IS NOT NULL
               ORDER BY embedding <=> %s::vector 
               LIMIT %s""",
            (embedding_list, embedding_list, limit)
        )
        
        results = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{"content": r[0], "metadata": json.loads(r[1]), "distance": r[2]} for r in results]

def main():
    preprocessor = RAGPreprocessor()
    
    # Look for Kaggle dataset
    kaggle_path = Path("Training Datasets/kaggle-health")
    
    if not kaggle_path.exists():
        print(f"Kaggle dataset not found at {kaggle_path}")
        print("Please place JSON files in Training Datasets/kaggle-health/")
        return
    
    # Process Kaggle health directory
    print(f"Processing Kaggle health dataset...")
    
    # Process with small sample first (5 files per directory)
    preprocessor.process_kaggle_directory(kaggle_path, sample_size=5)
    
    # Test similarity search
    print("\nTesting similarity search:")
    results = preprocessor.search_similar("appointment scheduling", limit=3)
    for i, result in enumerate(results, 1):
        print(f"{i}. Distance: {result['distance']:.3f}")
        print(f"   Content: {result['content'][:100]}...")
        print()

if __name__ == "__main__":
    main()