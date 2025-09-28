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
import psutil
try:
    import GPUtil
except ImportError:
    GPUtil = None

class TranscriptDashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Transcript Intelligence Dashboard")
        self.root.geometry("1200x900")
        self.root.minsize(1000, 700)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Database config
        self.db_config = {
            'host': '192.168.68.60',
            'port': 5432,
            'database': 'calllab',
            'user': 'postgres',
            'password': 'pass'
        }
        
        # Grading settings
        self.min_realness_score = tk.IntVar(value=6)
        self.grading_active = False
        
        self.setup_ui()
        self.start_auto_refresh()
    
    def setup_ui(self):
        """Setup the main UI"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Grading Settings", command=self.open_grading_settings)
        
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
            ("Completed Jobs", "completed_jobs"),
            ("CPU Usage", "cpu_usage"),
            ("Memory Usage", "memory_usage"),
            ("GPU Usage", "gpu_usage"),
            ("CPU Temp", "cpu_temp"),
            ("GPU Temp", "gpu_temp")
        ]
        
        for i, (label, key) in enumerate(stats_items):
            row, col = i // 4, i % 4
            ttk.Label(stats_grid, text=f"{label}:").grid(row=row*2, column=col, sticky=tk.W, padx=10)
            self.stats_labels[key] = ttk.Label(stats_grid, text="--", font=("Arial", 10, "bold"))
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
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Quality metrics chart
        self.setup_quality_chart(bottom_frame)
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Refresh Now", command=self.refresh_data).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Node Details", command=self.show_node_details).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(control_frame, text="Spot Check (50)", command=self.run_spot_check).pack(side=tk.LEFT, padx=(10, 0))
        self.grade_all_btn = ttk.Button(control_frame, text="Grade All", command=self.run_grade_all)
        self.grade_all_btn.pack(side=tk.LEFT, padx=(10, 0))
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
        
        self.quality_fig, self.quality_ax = plt.subplots(figsize=(12, 2.5))
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
        
        # Remote node metrics
        self.update_node_metrics()
        
        cur.close()
        conn.close()
    
    def update_node_metrics(self):
        """Update metrics from remote nodes"""
        try:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Get system metrics from all active nodes
            cur.execute("""
                SELECT hostname, system_metrics 
                FROM nodes 
                WHERE status = 'online' AND system_metrics IS NOT NULL
                ORDER BY last_seen DESC
            """)
            
            nodes_data = cur.fetchall()
            
            if nodes_data:
                # Aggregate metrics from all nodes
                total_cpu = 0
                total_memory = 0
                total_gpu = 0
                cpu_temps = []
                gpu_temps = []
                node_count = 0
                
                for hostname, metrics_json in nodes_data:
                    try:
                        metrics = json.loads(metrics_json)
                        if metrics.get('cpu_percent') is not None:
                            total_cpu += metrics['cpu_percent']
                            node_count += 1
                        if metrics.get('memory_percent') is not None:
                            total_memory += metrics['memory_percent']
                        if metrics.get('gpu_usage') is not None:
                            total_gpu += metrics['gpu_usage']
                        if metrics.get('cpu_temp') is not None:
                            cpu_temps.append(metrics['cpu_temp'])
                        if metrics.get('gpu_temp') is not None:
                            gpu_temps.append(metrics['gpu_temp'])
                    except:
                        continue
                
                # Update labels with aggregated data
                if node_count > 0:
                    avg_cpu = total_cpu / node_count
                    avg_memory = total_memory / node_count
                    avg_gpu = total_gpu / node_count if total_gpu > 0 else 0
                    
                    self.stats_labels["cpu_usage"].config(text=f"{avg_cpu:.1f}%")
                    self.stats_labels["memory_usage"].config(text=f"{avg_memory:.1f}%")
                    self.stats_labels["gpu_usage"].config(text=f"{avg_gpu:.1f}%" if avg_gpu > 0 else "N/A")
                    
                    if cpu_temps:
                        avg_cpu_temp = sum(cpu_temps) / len(cpu_temps)
                        self.stats_labels["cpu_temp"].config(text=f"{avg_cpu_temp:.1f}°C")
                    else:
                        self.stats_labels["cpu_temp"].config(text="N/A")
                    
                    if gpu_temps:
                        avg_gpu_temp = sum(gpu_temps) / len(gpu_temps)
                        self.stats_labels["gpu_temp"].config(text=f"{avg_gpu_temp:.1f}°C")
                    else:
                        self.stats_labels["gpu_temp"].config(text="N/A")
                else:
                    # No metrics available
                    for key in ["cpu_usage", "memory_usage", "gpu_usage", "cpu_temp", "gpu_temp"]:
                        self.stats_labels[key].config(text="N/A")
            else:
                # No nodes with metrics
                for key in ["cpu_usage", "memory_usage", "gpu_usage", "cpu_temp", "gpu_temp"]:
                    self.stats_labels[key].config(text="N/A")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"Error updating node metrics: {e}")
            for key in ["cpu_usage", "memory_usage", "gpu_usage", "cpu_temp", "gpu_temp"]:
                self.stats_labels[key].config(text="Error")
    
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
    
    def open_grading_settings(self):
        """Open grading settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Grading Settings")
        settings_window.geometry("300x150")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Min realness score setting
        ttk.Label(settings_window, text="Minimum Realness Score (1-10):").pack(pady=10)
        
        score_frame = ttk.Frame(settings_window)
        score_frame.pack(pady=5)
        
        ttk.Scale(score_frame, from_=1, to=10, orient=tk.HORIZONTAL, 
                 variable=self.min_realness_score, length=200).pack(side=tk.LEFT)
        ttk.Label(score_frame, textvariable=self.min_realness_score).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(settings_window, text="Conversations below this score will be deleted", 
                 font=("Arial", 8)).pack(pady=5)
        
        ttk.Button(settings_window, text="Close", 
                  command=settings_window.destroy).pack(pady=10)
    
    def run_spot_check(self):
        """Run quality analysis on 50 conversations"""
        if self.grading_active:
            messagebox.showwarning("Warning", "Grading already in progress")
            return
            
        self.run_quality_analysis(limit=50)
    
    def run_grade_all(self):
        """Grade all ungraded conversations"""
        if self.grading_active:
            messagebox.showwarning("Warning", "Grading already in progress")
            return
            
        self.run_quality_analysis(limit=None)
    
    def run_quality_analysis(self, limit=50):
        """Run quality analysis on sample conversations"""
        def analysis_thread():
            try:
                self.grading_active = True
                self.grade_all_btn.config(state='disabled')
                
                if limit:
                    self.status_var.set(f"Running spot check on {limit} conversations...")
                else:
                    self.status_var.set("Grading all ungraded conversations...")
                self.root.update()
                
                # Import and run quality analysis
                import sys, os
                sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'core'))
                from conversation_grader import ConversationGrader
                
                grader = ConversationGrader(db_config=self.db_config)
                grader.setup_grading_schema()
                
                # Set minimum realness score
                grader.min_realness_score = self.min_realness_score.get()
                
                if limit:
                    graded_count = grader.grade_database_conversations(limit=limit)
                else:
                    # Grade all - keep going until no more ungraded conversations
                    total_graded = 0
                    while True:
                        batch_count = grader.grade_database_conversations(limit=50)
                        total_graded += batch_count
                        if batch_count == 0:
                            break
                        self.status_var.set(f"Graded {total_graded} conversations so far...")
                        self.root.update()
                    graded_count = total_graded
                
                self.status_var.set(f"Quality analysis complete: {graded_count} conversations graded")
                
                # Refresh quality chart and stats
                self.update_quality_chart()
                self.update_stats()
                
            except Exception as e:
                self.status_var.set(f"Quality analysis failed: {e}")
                messagebox.showerror("Error", f"Quality analysis failed: {e}")
            finally:
                self.grading_active = False
                self.grade_all_btn.config(state='normal')
        
        # Run in background thread
        threading.Thread(target=analysis_thread, daemon=True).start()
    
    def show_node_details(self):
        """Show detailed node metrics window"""
        details_window = tk.Toplevel(self.root)
        details_window.title("Node Details")
        details_window.geometry("800x600")
        details_window.transient(self.root)
        
        # Create treeview for node data
        columns = ('hostname', 'status', 'cpu', 'memory', 'gpu', 'cpu_temp', 'gpu_temp', 'last_seen')
        tree = ttk.Treeview(details_window, columns=columns, show='headings', height=15)
        
        # Define headings
        tree.heading('hostname', text='Node')
        tree.heading('status', text='Status')
        tree.heading('cpu', text='CPU %')
        tree.heading('memory', text='Memory %')
        tree.heading('gpu', text='GPU %')
        tree.heading('cpu_temp', text='CPU Temp')
        tree.heading('gpu_temp', text='GPU Temp')
        tree.heading('last_seen', text='Last Seen')
        
        # Configure column widths
        tree.column('hostname', width=100)
        tree.column('status', width=80)
        tree.column('cpu', width=80)
        tree.column('memory', width=80)
        tree.column('gpu', width=80)
        tree.column('cpu_temp', width=80)
        tree.column('gpu_temp', width=80)
        tree.column('last_seen', width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(details_window, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        
        # Refresh button
        refresh_btn = ttk.Button(details_window, text="Refresh", 
                                command=lambda: self.refresh_node_details(tree))
        refresh_btn.pack(pady=5)
        
        # Load initial data
        self.refresh_node_details(tree)
    
    def refresh_node_details(self, tree):
        """Refresh node details in the treeview"""
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        try:
            conn = self.get_db()
            cur = conn.cursor()
            
            # Get all nodes with their metrics
            cur.execute("""
                SELECT hostname, node_type, status, system_metrics, last_seen
                FROM nodes 
                ORDER BY node_type, hostname
            """)
            
            nodes_data = cur.fetchall()
            
            for hostname, node_type, status, metrics_json, last_seen in nodes_data:
                # Parse metrics
                cpu_usage = "N/A"
                memory_usage = "N/A"
                gpu_usage = "N/A"
                cpu_temp = "N/A"
                gpu_temp = "N/A"
                
                if metrics_json:
                    try:
                        metrics = json.loads(metrics_json)
                        cpu_usage = f"{metrics.get('cpu_percent', 'N/A'):.1f}%" if metrics.get('cpu_percent') is not None else "N/A"
                        memory_usage = f"{metrics.get('memory_percent', 'N/A'):.1f}%" if metrics.get('memory_percent') is not None else "N/A"
                        gpu_usage = f"{metrics.get('gpu_usage', 'N/A'):.1f}%" if metrics.get('gpu_usage') is not None else "N/A"
                        cpu_temp = f"{metrics.get('cpu_temp', 'N/A'):.1f}°C" if metrics.get('cpu_temp') is not None else "N/A"
                        gpu_temp = f"{metrics.get('gpu_temp', 'N/A'):.1f}°C" if metrics.get('gpu_temp') is not None else "N/A"
                    except:
                        pass
                
                # Format last seen
                if last_seen:
                    time_diff = datetime.now() - last_seen
                    if time_diff.seconds < 60:
                        last_seen_str = f"{time_diff.seconds}s ago"
                    elif time_diff.seconds < 3600:
                        last_seen_str = f"{time_diff.seconds//60}m ago"
                    else:
                        last_seen_str = last_seen.strftime("%H:%M:%S")
                else:
                    last_seen_str = "Never"
                
                # Color code by status
                node_display = f"{hostname} ({node_type})"
                
                item = tree.insert('', tk.END, values=(
                    node_display, status, cpu_usage, memory_usage, 
                    gpu_usage, cpu_temp, gpu_temp, last_seen_str
                ))
                
                # Color code rows
                if status == 'online':
                    tree.set(item, 'status', '🟢 Online')
                elif status == 'offline':
                    tree.set(item, 'status', '🔴 Offline')
                else:
                    tree.set(item, 'status', f'🟡 {status}')
            
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"Error refreshing node details: {e}")
            tree.insert('', tk.END, values=('Error', str(e), '', '', '', '', '', ''))
    
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
    
    def on_closing(self):
        """Handle window close event"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
    
    def run(self):
        """Start the dashboard"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

if __name__ == "__main__":
    dashboard = TranscriptDashboard()
    dashboard.run()