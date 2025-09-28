#!/usr/bin/env python3
"""
Performance Data Export - Export all performance and grading data to CSV
"""

import psycopg2
import json
import csv
from datetime import datetime
from pathlib import Path

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host='EPM_DELL',
        port=5432,
        database='calllab',
        user='postgres',
        password='pass'
    )

def export_performance_data():
    """Export comprehensive performance and grading data"""
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get comprehensive data with all metrics
    query = """
    SELECT 
        c.id as conversation_id,
        c.model_name,
        c.quality_score,
        c.generation_start_time,
        c.generation_end_time,
        c.generation_duration_ms,
        c.created_at,
        
        -- Extract performance metrics from JSON
        c.evaluation_metrics->>'speed_score' as speed_score,
        c.evaluation_metrics->>'duplicate_status' as duplicate_status,
        c.evaluation_metrics->>'completion_tokens' as completion_tokens,
        c.evaluation_metrics->>'rag_used' as rag_used,
        c.evaluation_metrics->>'retry_attempt' as retry_attempt,
        
        -- Job and scenario info
        j.id as job_id,
        j.status as job_status,
        j.started_at as job_started,
        j.completed_at as job_completed,
        s.name as scenario_name,
        
        -- Node info
        n.hostname as machine_name,
        n.capabilities,
        
        -- Grading data if available
        g.realness_score as graded_realness,
        g.coherence_score as graded_coherence,
        g.naturalness_score as graded_naturalness,
        g.overall_score as graded_overall,
        g.graded_at,
        
        -- Calculate tokens per second
        CASE 
            WHEN c.generation_duration_ms > 0 AND c.evaluation_metrics->>'completion_tokens' IS NOT NULL
            THEN (c.evaluation_metrics->>'completion_tokens')::float / (c.generation_duration_ms::float / 1000)
            ELSE NULL
        END as tokens_per_second,
        
        -- Extract GPU info from capabilities if available
        CASE 
            WHEN n.capabilities::text LIKE '%gpu%' THEN 'GPU'
            ELSE 'CPU'
        END as processing_type
        
    FROM conversations c
    LEFT JOIN jobs j ON c.job_id = j.id
    LEFT JOIN scenarios s ON c.scenario_id = s.id
    LEFT JOIN nodes n ON j.assigned_node_id = n.id
    LEFT JOIN conversation_grades g ON c.id = g.conversation_id
    
    ORDER BY c.created_at DESC
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    # Get column names
    columns = [desc[0] for desc in cur.description]
    
    cur.close()
    conn.close()
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"performance_analysis_{timestamp}.csv"
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(columns)
        
        # Write data rows
        for row in rows:
            # Convert any JSON objects to strings for CSV
            processed_row = []
            for item in row:
                if isinstance(item, (dict, list)):
                    processed_row.append(json.dumps(item))
                elif item is None:
                    processed_row.append('')
                else:
                    processed_row.append(str(item))
            writer.writerow(processed_row)
    
    print(f"Exported {len(rows)} records to {output_file}")
    
    # Print summary stats
    if rows:
        print(f"\nSummary:")
        print(f"- Date range: {min(row[6] for row in rows if row[6])} to {max(row[6] for row in rows if row[6])}")
        
        # Count by model
        models = {}
        machines = {}
        for row in rows:
            model = row[1] or 'unknown'
            machine = row[18] or 'unknown'
            models[model] = models.get(model, 0) + 1
            machines[machine] = machines.get(machine, 0) + 1
        
        print(f"- Models: {dict(models)}")
        print(f"- Machines: {dict(machines)}")
        
        # Performance stats
        durations = [row[5] for row in rows if row[5]]
        if durations:
            avg_duration = sum(durations) / len(durations)
            print(f"- Avg generation time: {avg_duration:.0f}ms")
        
        # Grading stats
        graded_count = sum(1 for row in rows if row[21])  # graded_realness
        print(f"- Graded conversations: {graded_count}/{len(rows)} ({graded_count/len(rows)*100:.1f}%)")
    
    return output_file

if __name__ == "__main__":
    try:
        output_file = export_performance_data()
        print(f"\nData exported successfully to: {output_file}")
        print("Ready for analysis in your preferred data analysis tool!")
    except Exception as e:
        print(f"Error exporting data: {e}")