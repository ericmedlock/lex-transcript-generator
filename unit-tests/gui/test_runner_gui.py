#!/usr/bin/env python3
"""
Test Runner GUI - Comprehensive test execution interface
"""

import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from datetime import datetime
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework import TestRunner, TestStatus, TestResult
import importlib

class TestRunnerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM Transcript Platform - Test Runner")
        self.root.geometry("1200x800")
        
        self.test_runner = TestRunner()
        self.current_results = []
        self.running_tests = False
        
        self.setup_ui()
        self.load_test_modules()
        self.refresh_test_list()
        
        # Setup test runner callbacks
        self.test_runner.add_callback(self.on_test_event)
        
        # Force refresh after loading
        self.root.after(100, self.refresh_test_list)
    
    def setup_ui(self):
        """Setup the GUI interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Test Runner", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Left panel - Test selection
        left_frame = ttk.LabelFrame(main_frame, text="Test Selection", padding="5")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        # Test suite selection
        suite_frame = ttk.Frame(left_frame)
        suite_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        suite_frame.columnconfigure(1, weight=1)
        
        ttk.Label(suite_frame, text="Suite:").grid(row=0, column=0, sticky=tk.W)
        self.suite_var = tk.StringVar(value="All Suites")
        self.suite_combo = ttk.Combobox(suite_frame, textvariable=self.suite_var, state="readonly")
        self.suite_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        self.suite_combo.bind('<<ComboboxSelected>>', self.on_suite_selected)
        
        # Test list
        self.test_tree = ttk.Treeview(left_frame, columns=("status", "duration"), show="tree headings")
        self.test_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure treeview columns
        self.test_tree.heading("#0", text="Test")
        self.test_tree.heading("status", text="Status")
        self.test_tree.heading("duration", text="Duration")
        self.test_tree.column("#0", width=300)
        self.test_tree.column("status", width=80)
        self.test_tree.column("duration", width=80)
        
        # Scrollbar for test list
        test_scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.test_tree.yview)
        test_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.test_tree.configure(yscrollcommand=test_scrollbar.set)
        
        # Right panel - Results and controls
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)
        
        # Control buttons
        button_frame = ttk.Frame(right_frame)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.run_all_btn = ttk.Button(button_frame, text="Run All Tests", command=self.run_all_tests)
        self.run_all_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.run_selected_btn = ttk.Button(button_frame, text="Run Selected", command=self.run_selected_test)
        self.run_selected_btn.grid(row=0, column=1, padx=5)
        
        self.run_suite_btn = ttk.Button(button_frame, text="Run Suite", command=self.run_current_suite)
        self.run_suite_btn.grid(row=0, column=2, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop", command=self.stop_tests, state="disabled")
        self.stop_btn.grid(row=0, column=3, padx=(5, 0))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(right_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Results panel
        results_frame = ttk.LabelFrame(right_frame, text="Test Results", padding="5")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Results text area
        self.results_text = tk.Text(results_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Results scrollbar
        results_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        results_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_text.configure(yscrollcommand=results_scrollbar.set)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Menu bar
        self.setup_menu()
    
    def setup_menu(self):
        """Setup application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Results...", command=self.export_results)
        file_menu.add_command(label="Load Test Results...", command=self.load_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Tests", command=self.refresh_test_list)
        view_menu.add_command(label="Clear Results", command=self.clear_results)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Test Plan", command=self.show_test_plan)
        help_menu.add_command(label="About", command=self.show_about)
    
    def load_test_modules(self):
        """Load all test modules"""
        test_dir = Path(__file__).parent.parent
        
        # Import test modules
        test_modules = [
            "core.test_config_manager",
            "core.test_database", 
            "data.test_pii_processor",
            "integration.test_ai_catalyst"
        ]
        
        for module_name in test_modules:
            try:
                # Add test directory to path
                if str(test_dir) not in sys.path:
                    sys.path.insert(0, str(test_dir))
                
                importlib.import_module(module_name)
                self.log_message(f"Loaded test module: {module_name}")
            except Exception as e:
                self.log_message(f"Failed to load {module_name}: {e}")
                import traceback
                self.log_message(f"Traceback: {traceback.format_exc()}")
    
    def refresh_test_list(self):
        """Refresh the test list display"""
        # Clear existing items
        for item in self.test_tree.get_children():
            self.test_tree.delete(item)
        
        # Update suite combo
        suite_names = ["All Suites"] + list(self.test_runner.test_suites.keys())
        self.suite_combo['values'] = suite_names
        
        # Populate test tree
        if self.suite_var.get() == "All Suites":
            # Show all tests grouped by suite
            for suite_name, suite in self.test_runner.test_suites.items():
                suite_item = self.test_tree.insert("", "end", text=f"Suite: {suite_name}", 
                                                  values=("", ""), tags=("suite",))
                
                for test in suite.tests:
                    status = "Pending"
                    duration = ""
                    if test.result:
                        status = test.result.status.value.title()
                        duration = f"{test.result.duration:.2f}s"
                    
                    self.test_tree.insert(suite_item, "end", text=test.name,
                                        values=(status, duration), tags=("test",))
        else:
            # Show tests for selected suite
            suite_name = self.suite_var.get()
            if suite_name in self.test_runner.test_suites:
                suite = self.test_runner.test_suites[suite_name]
                for test in suite.tests:
                    status = "Pending"
                    duration = ""
                    if test.result:
                        status = test.result.status.value.title()
                        duration = f"{test.result.duration:.2f}s"
                    
                    self.test_tree.insert("", "end", text=test.name,
                                        values=(status, duration), tags=("test",))
        
        # Configure tags
        self.test_tree.tag_configure("suite", background="#f0f0f0")
        self.test_tree.tag_configure("test", background="white")
    
    def on_suite_selected(self, event):
        """Handle suite selection change"""
        self.refresh_test_list()
    
    def on_test_event(self, event: str, data):
        """Handle test runner events"""
        if event == "test_started":
            test = data
            self.log_message(f"Starting test: {test.name}")
            self.update_test_status(test.test_id, "Running")
            
        elif event == "test_completed":
            result = data
            self.log_message(f"Completed test: {result.name} - {result.status.value.title()}")
            if result.error_message:
                self.log_message(f"  Error: {result.error_message}")
            self.update_test_status(result.test_id, result.status.value.title(), 
                                  f"{result.duration:.2f}s")
            
        elif event == "suite_started":
            suite = data
            self.log_message(f"Starting suite: {suite.name}")
            
        elif event == "suite_completed":
            results = data
            passed = sum(1 for r in results if r.status == TestStatus.PASSED)
            total = len(results)
            self.log_message(f"Suite completed: {passed}/{total} tests passed")
    
    def update_test_status(self, test_id: str, status: str, duration: str = ""):
        """Update test status in the tree view"""
        # Find and update the test item
        for item in self.test_tree.get_children():
            if self.test_tree.item(item, "tags")[0] == "suite":
                # Check children of suite
                for child in self.test_tree.get_children(item):
                    test = self.get_test_by_tree_item(child)
                    if test and test.test_id == test_id:
                        self.test_tree.item(child, values=(status, duration))
                        return
            else:
                # Direct test item
                test = self.get_test_by_tree_item(item)
                if test and test.test_id == test_id:
                    self.test_tree.item(item, values=(status, duration))
                    return
    
    def get_test_by_tree_item(self, item):
        """Get test case by tree item"""
        test_name = self.test_tree.item(item, "text")
        for test in self.test_runner.get_all_tests():
            if test.name == test_name:
                return test
        return None
    
    def run_all_tests(self):
        """Run all registered tests"""
        if self.running_tests:
            return
        
        self.start_test_run()
        threading.Thread(target=self._run_all_tests_thread, daemon=True).start()
    
    def run_selected_test(self):
        """Run the currently selected test"""
        if self.running_tests:
            return
        
        selection = self.test_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a test to run.")
            return
        
        item = selection[0]
        test = self.get_test_by_tree_item(item)
        if not test:
            messagebox.showwarning("Invalid Selection", "Please select a test (not a suite).")
            return
        
        self.start_test_run()
        threading.Thread(target=self._run_single_test_thread, args=(test.test_id,), daemon=True).start()
    
    def run_current_suite(self):
        """Run the currently selected suite"""
        if self.running_tests:
            return
        
        suite_name = self.suite_var.get()
        if suite_name == "All Suites":
            self.run_all_tests()
            return
        
        if suite_name not in self.test_runner.test_suites:
            messagebox.showerror("Error", f"Suite '{suite_name}' not found.")
            return
        
        self.start_test_run()
        threading.Thread(target=self._run_suite_thread, args=(suite_name,), daemon=True).start()
    
    def start_test_run(self):
        """Prepare UI for test execution"""
        self.running_tests = True
        self.run_all_btn.config(state="disabled")
        self.run_selected_btn.config(state="disabled")
        self.run_suite_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set(0)
        self.status_var.set("Running tests...")
        self.clear_results()
    
    def stop_test_run(self):
        """Clean up after test execution"""
        self.running_tests = False
        self.run_all_btn.config(state="normal")
        self.run_selected_btn.config(state="normal")
        self.run_suite_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress_var.set(100)
        self.status_var.set("Ready")
        self.refresh_test_list()
    
    def stop_tests(self):
        """Stop running tests"""
        self.running_tests = False
        self.status_var.set("Stopping tests...")
    
    def _run_all_tests_thread(self):
        """Thread function to run all tests"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.test_runner.run_all())
        except Exception as e:
            self.log_message(f"Error running tests: {e}")
        finally:
            self.root.after(0, self.stop_test_run)
    
    def _run_single_test_thread(self, test_id: str):
        """Thread function to run a single test"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.test_runner.run_test(test_id))
        except Exception as e:
            self.log_message(f"Error running test: {e}")
        finally:
            self.root.after(0, self.stop_test_run)
    
    def _run_suite_thread(self, suite_name: str):
        """Thread function to run a test suite"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.test_runner.run_suite(suite_name))
        except Exception as e:
            self.log_message(f"Error running suite: {e}")
        finally:
            self.root.after(0, self.stop_test_run)
    
    def log_message(self, message: str):
        """Add message to results log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.results_text.insert(tk.END, formatted_message)
        self.results_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_results(self):
        """Clear the results display"""
        self.results_text.delete(1.0, tk.END)
    
    def export_results(self):
        """Export test results to file"""
        if not self.test_runner.results:
            messagebox.showinfo("No Results", "No test results to export.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                self.test_runner.export_results(Path(filename))
                messagebox.showinfo("Export Complete", f"Results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results: {e}")
    
    def load_results(self):
        """Load test results from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                import json
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.clear_results()
                self.log_message(f"Loaded results from {filename}")
                self.log_message(f"Test run from: {data.get('timestamp', 'Unknown')}")
                
                summary = data.get('summary', {})
                for status, count in summary.items():
                    if count > 0:
                        self.log_message(f"{status.title()}: {count}")
                
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load results: {e}")
    
    def show_test_plan(self):
        """Show the test plan document"""
        test_plan_path = Path(__file__).parent.parent / "TEST_PLAN.md"
        if test_plan_path.exists():
            os.startfile(str(test_plan_path))
        else:
            messagebox.showinfo("Test Plan", "Test plan document not found.")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
LLM Transcript Platform Test Runner

A comprehensive testing suite for the distributed transcript 
intelligence platform with GUI interface for test execution 
and result analysis.

Features:
• Individual test execution
• Suite-based test organization  
• Full regression testing
• Real-time result monitoring
• Test result export/import
• Performance benchmarking

Version: 1.0.0
        """
        messagebox.showinfo("About", about_text.strip())

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = TestRunnerGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Application interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")

if __name__ == "__main__":
    main()