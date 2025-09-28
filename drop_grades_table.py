#!/usr/bin/env python3
"""
Drop conversation_grades table - Use when schema is corrupted
"""

import psycopg2

def drop_grades_table():
    """Drop the conversation_grades table"""
    
    db_config = {
        'host': '192.168.68.60',
        'port': 5432,
        'database': 'calllab',
        'user': 'postgres',
        'password': 'pass'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'conversation_grades'
            )
        """)
        
        table_exists = cur.fetchone()[0]
        
        if table_exists:
            print("Dropping conversation_grades table...")
            cur.execute("DROP TABLE conversation_grades")
            conn.commit()
            print("✅ conversation_grades table dropped successfully")
        else:
            print("ℹ️  conversation_grades table does not exist")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error dropping table: {e}")

if __name__ == "__main__":
    print("Drop conversation_grades table")
    print("=" * 40)
    
    confirm = input("Are you sure you want to drop the conversation_grades table? (yes/no): ")
    
    if confirm.lower() == 'yes':
        drop_grades_table()
    else:
        print("Operation cancelled")