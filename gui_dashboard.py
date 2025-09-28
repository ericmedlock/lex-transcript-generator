#!/usr/bin/env python3
"""
GUI Dashboard for Transcript Intelligence Platform
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import psycopg2
import json
import threading
import time
from datetime import datetime, timedelta
import numpy as np

class TranscriptDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Transcript Intelligence Dashboard")
        self.root.geometry("1200x800")
        
        # Database config
        self.db_config = {
            'host': '192.168.68.60',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        
        self.setup_ui()
        self.start_auto_refresh()
    
    def setup_ui(self):
        """Setup the main UI"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(main_frame, text="Transcript Intelligence Dashboard", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Stats frame
        stats_frame = ttk.LabelFrame(main_frame, text="System Statistics", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Stats labels
        self.stats_labels = {}
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        stats_items = [
            ("Total Conversations", "total_conversations"),
            ("Active Nodes", "active_nodes"),
            ("Conversations/Hour", "conversations_per_hour"),
            ("Current Run", "current_run"),
            ("Pending Jobs", "pending_jobs"),
            ("Completed Jobs", "completed_jobs")
        ]
        
        for i, (label, key) in enumerate(stats_items):
            row, col = i // 3, i % 3
            ttk.Label(stats_grid, text=f"{label}:").grid(row=row*2, column=col, sticky=tk.W, padx=10)
            self.stats_labels[key] = ttk.Label(stats_grid, text="--", font=("Arial", 12, "bold"))
            self.stats_labels[key].grid(row=row*2+1, column=col, sticky=tk.W, padx=10)
        
        # Charts frame
        charts_frame = ttk.Frame(main_frame)
        charts_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left charts
        left_frame = ttk.Frame(charts_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Right charts  
        right_frame = ttk.Frame(charts_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Generation rate chart
        self.setup_generation_chart(left_frame)
        
        # Node performance chart
        self.setup_node_chart(right_frame)
        
        # Bottom charts
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Quality metrics chart
        self.setup_quality_chart(bottom_frame)
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Refresh Now", command=self.refresh_data).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Run Quality Analysis", command=self.run_quality_analysis).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(control_frame, text="Export Report", command=self.export_report).pack(side=tk.LEFT, padx=(10, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(10, 0))
    
    def setup_generation_chart(self, parent):
        """Setup generation rate over time chart"""
        chart_frame = ttk.LabelFrame(parent, text="Generation Rate (Conversations/Hour)", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.gen_fig, self.gen_ax = plt.subplots(figsize=(6, 3))
        self.gen_canvas = FigureCanvasTkAgg(self.gen_fig, chart_frame)
        self.gen_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initial empty chart
        self.gen_ax.set_title("Generation Rate Over Time")
        self.gen_ax.set_xlabel("Time")
        self.gen_ax.set_ylabel("Conversations/Hour")
        self.gen_fig.tight_layout()
    
    def setup_node_chart(self, parent):
        """Setup node performance chart"""
        chart_frame = ttk.LabelFrame(parent, text="Node Performance", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.node_fig, self.node_ax = plt.subplots(figsize=(6, 3))
        self.node_canvas = FigureCanvasTkAgg(self.node_fig, chart_frame)
        self.node_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initial empty chart
        self.node_ax.set_title("Conversations by Node")
        self.node_ax.set_ylabel("Conversations Generated")
        self.node_fig.tight_layout()
    
    def setup_quality_chart(self, parent):
        """Setup quality metrics chart"""
        chart_frame = ttk.LabelFrame(parent, text="Quality Metrics", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.quality_fig, self.quality_ax = plt.subplots(figsize=(12, 3))
        self.quality_canvas = FigureCanvasTkAgg(self.quality_fig, chart_frame)
        self.quality_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initial empty chart
        self.quality_ax.set_title("Quality Scores Over Time")
        self.quality_ax.set_xlabel("Time")
        self.quality_ax.set_ylabel("Score")
        self.quality_fig.tight_layout()
    
    def get_db(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def refresh_data(self):
        """Refresh all dashboard data"""
        self.status_var.set("Refreshing data...")
        self.root.update()
        
        try:
            self.update_stats()
            self.update_generation_chart()
            self.update_node_chart()
            self.update_quality_chart()
            self.status_var.set(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"Failed to refresh data: {e}")
    
    def update_stats(self):
        """Update statistics labels"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Total conversations
        cur.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cur.fetchone()[0]
        self.stats_labels["total_conversations"].config(text=str(total_conversations))
        
        # Active nodes
        cur.execute("SELECT COUNT(*) FROM nodes WHERE status = 'online' AND node_type = 'generation'")
        active_nodes = cur.fetchone()[0]
        self.stats_labels["active_nodes"].config(text=str(active_nodes))
        
        # Current run
        cur.execute("SELECT current_run FROM run_counter LIMIT 1")
        result = cur.fetchone()
        current_run = result[0] if result else 0
        self.stats_labels["current_run"].config(text=str(current_run))
        
        # Jobs
        cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'pending'")
        pending_jobs = cur.fetchone()[0]
        self.stats_labels["pending_jobs"].config(text=str(pending_jobs))
        
        cur.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'")
        completed_jobs = cur.fetchone()[0]
        self.stats_labels["completed_jobs"].config(text=str(completed_jobs))
        
        # Conversations per hour (last hour)
        cur.execute("""
            SELECT COUNT(*) FROM conversations 
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)
        conversations_last_hour = cur.fetchone()[0]
        self.stats_labels["conversations_per_hour"].config(text=str(conversations_last_hour))
        
        cur.close()
        conn.close()
    
    def update_generation_chart(self):
        """Update generation rate chart"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Get hourly conversation counts for last 24 hours
        cur.execute("""
            SELECT 
                DATE_TRUNC('hour', created_at) as hour,
                COUNT(*) as count
            FROM conversations 
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour
        """)
        
        data = cur.fetchall()
        
        if data:
            hours = [row[0] for row in data]
            counts = [row[1] for row in data]
            
            self.gen_ax.clear()
            self.gen_ax.plot(hours, counts, marker='o', linewidth=2)
            self.gen_ax.set_title("Generation Rate (Last 24 Hours)")
            self.gen_ax.set_xlabel("Time")
            self.gen_ax.set_ylabel("Conversations/Hour")
            self.gen_ax.grid(True, alpha=0.3)
            
            # Format x-axis
            self.gen_fig.autofmt_xdate()
        
        self.gen_fig.tight_layout()
        self.gen_canvas.draw()
        
        cur.close()
        conn.close()
    
    def update_node_chart(self):
        """Update node performance chart"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Get conversation counts by node
        cur.execute("""
            SELECT 
                n.hostname,
                COUNT(c.id) as conversation_count
            FROM nodes n
            LEFT JOIN jobs j ON j.assigned_node_id = n.id
            LEFT JOIN conversations c ON c.job_id = j.id
            WHERE n.node_type = 'generation'
            GROUP BY n.hostname
            ORDER BY conversation_count DESC
        """)
        
        data = cur.fetchall()
        
        if data:
            nodes = [row[0] for row in data]
            counts = [row[1] for row in data]
            
            self.node_ax.clear()
            bars = self.node_ax.bar(nodes, counts, color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
            self.node_ax.set_title("Conversations by Node")
            self.node_ax.set_ylabel("Conversations Generated")
            
            # Add value labels on bars
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                self.node_ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                                 str(count), ha='center', va='bottom')
        
        self.node_fig.tight_layout()
        self.node_canvas.draw()
        
        cur.close()
        conn.close()
    
    def update_quality_chart(self):
        """Update quality metrics chart"""
        conn = self.get_db()
        cur = conn.cursor()
        
        # Check if conversation_grades table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'conversation_grades'
            )
        """)
        
        if not cur.fetchone()[0]:
            # No quality data available
            self.quality_ax.clear()
            self.quality_ax.text(0.5, 0.5, 'No quality data available\nRun quality analysis to see metrics', 
                               ha='center', va='center', transform=self.quality_ax.transAxes)
            self.quality_ax.set_title("Quality Scores Over Time")
            self.quality_canvas.draw()
            cur.close()
            conn.close()
            return
        
        # Get quality scores over time
        cur.execute("""
            SELECT 
                DATE_TRUNC('day', graded_at) as day,
                AVG(overall_score) as avg_score,
                COUNT(*) as count
            FROM conversation_grades 
            WHERE graded_at > NOW() - INTERVAL '30 days'
            AND overall_score IS NOT NULL
            GROUP BY day
            ORDER BY day
        """)
        
        data = cur.fetchall()
        
        if data:
            days = [row[0] for row in data]
            scores = [row[1] for row in data]
            counts = [row[2] for row in data]
            
            self.quality_ax.clear()
            
            # Plot average scores
            line1 = self.quality_ax.plot(days, scores, marker='o', linewidth=2, 
                                        color='green', label='Avg Quality Score')
            self.quality_ax.set_ylabel("Average Score", color='green')
            self.quality_ax.tick_params(axis='y', labelcolor='green')
            
            # Add second y-axis for counts
            ax2 = self.quality_ax.twinx()
            line2 = ax2.bar(days, counts, alpha=0.3, color='blue', label='Conversations Graded')
            ax2.set_ylabel("Conversations Graded", color='blue')
            ax2.tick_params(axis='y', labelcolor='blue')
            
            self.quality_ax.set_title("Quality Scores Over Time (Last 30 Days)")
            self.quality_ax.set_xlabel("Date")
            self.quality_ax.grid(True, alpha=0.3)
            
            # Format x-axis
            self.quality_fig.autofmt_xdate()
        else:
            self.quality_ax.clear()
            self.quality_ax.text(0.5, 0.5, 'No quality scores available', 
                               ha='center', va='center', transform=self.quality_ax.transAxes)
            self.quality_ax.set_title("Quality Scores Over Time")
        
        self.quality_fig.tight_layout()
        self.quality_canvas.draw()
        
        cur.close()
        conn.close()
    
    def run_quality_analysis(self):
        """Run quality analysis on sample conversations"""
        def analysis_thread():
            try:
                self.status_var.set("Running quality analysis...")
                self.root.update()
                
                # Import and run quality analysis
                import sys, os
                sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'core'))
                from conversation_grader import ConversationGrader
                
                grader = ConversationGrader(db_config=self.db_config)
                graded_count = grader.grade_database_conversations(limit=50)
                
                self.status_var.set(f"Quality analysis complete: {graded_count} conversations graded")
                
                # Refresh quality chart
                self.update_quality_chart()
                
            except Exception as e:
                self.status_var.set(f"Quality analysis failed: {e}")
                messagebox.showerror("Error", f"Quality analysis failed: {e}")
        
        # Run in background thread
        threading.Thread(target=analysis_thread, daemon=True).start()
    
    def export_report(self):
        """Export dashboard data to file"""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write("Transcript Intelligence Platform Report\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Generated: {datetime.now()}\n\n")
                    
                    # Write stats
                    f.write("System Statistics:\n")
                    for key, label in self.stats_labels.items():
                        f.write(f"  {key}: {label.cget('text')}\n")
                    
                    f.write("\nReport exported successfully.")
                
                messagebox.showinfo("Success", f"Report exported to {filename}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")
    
    def start_auto_refresh(self):
        """Start automatic data refresh"""
        def auto_refresh():
            while True:
                time.sleep(30)  # Refresh every 30 seconds
                try:
                    self.root.after(0, self.refresh_data)
                except:
                    break
        
        # Initial refresh
        self.refresh_data()
        
        # Start background refresh thread
        threading.Thread(target=auto_refresh, daemon=True).start()
    
    def run(self):
        """Start the dashboard"""
        self.root.mainloop()

if __name__ == "__main__":
    dashboard = TranscriptDashboard()
    dashboard.run()