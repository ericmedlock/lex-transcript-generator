#!/usr/bin/env python3
"""
Clean Lex Quality Analysis GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class LexQualityGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Lex Export Quality Analysis")
        self.root.geometry("800x600")
        
        # Data from analysis
        self.health_data = {
            'total_files': 633,
            'sample_size': 100,
            'format_compliance': 100.0,
            'pii_detection': 0.0,
            'avg_turns': 45.8,
            'avg_words': 21.4,
            'alternation': 44.7,
            'quality_score': 100.0,
            'lex_readiness': 91.1
        }
        
        self.lex_data = {
            'total_files': 509,
            'sample_size': 100,
            'format_compliance': 99.0,
            'pii_detection': 0.0,
            'avg_turns': 13.5,
            'avg_words': 9.3,
            'alternation': 99.0,
            'quality_score': 100.0,
            'lex_readiness': 98.5
        }
        
        self.setup_gui()
    
    def setup_gui(self):
        # Main title
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=10)
        
        ttk.Label(title_frame, text="Lex Export Quality Analysis", 
                 font=('Arial', 16, 'bold')).pack()
        
        # Overall confidence
        confidence = (self.health_data['lex_readiness'] + self.lex_data['lex_readiness']) / 2
        color = '#2ecc71' if confidence >= 85 else '#f39c12' if confidence >= 70 else '#e74c3c'
        
        conf_frame = ttk.Frame(self.root)
        conf_frame.pack(pady=10)
        
        ttk.Label(conf_frame, text=f"Overall Lex Readiness: {confidence:.1f}%", 
                 font=('Arial', 14, 'bold')).pack()
        
        status = "✅ READY FOR DEPLOYMENT" if confidence >= 85 else "⚠️ NEEDS MINOR FIXES" if confidence >= 70 else "❌ NOT READY"
        ttk.Label(conf_frame, text=status, font=('Arial', 12)).pack()
        
        # Dataset comparison
        self.create_comparison_chart()
        
        # Action buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Detailed Metrics", 
                  command=self.show_detailed_metrics).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(button_frame, text="Sample Content", 
                  command=self.show_sample_content).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(button_frame, text="Recommendations", 
                  command=self.show_recommendations).pack(side=tk.LEFT, padx=10)
        
        # Summary table
        self.create_summary_table()
    
    def create_comparison_chart(self):
        # Create matplotlib figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        
        # Readiness comparison
        datasets = ['Health Calls', 'Lex Export']
        readiness = [self.health_data['lex_readiness'], self.lex_data['lex_readiness']]
        colors = ['#3498db', '#2ecc71']
        
        bars = ax1.bar(datasets, readiness, color=colors, alpha=0.8)
        ax1.set_ylabel('Readiness %')
        ax1.set_title('Lex Readiness Confidence')
        ax1.set_ylim(0, 100)
        
        for bar, val in zip(bars, readiness):
            ax1.text(bar.get_x() + bar.get_width()/2., val + 1, f'{val:.1f}%', 
                    ha='center', va='bottom', fontweight='bold')
        
        # Quality metrics comparison
        metrics = ['Format\nCompliance', 'PII\nSafety', 'Quality\nScore']
        health_vals = [self.health_data['format_compliance'], 
                      100 - self.health_data['pii_detection'], 
                      self.health_data['quality_score']]
        lex_vals = [self.lex_data['format_compliance'], 
                   100 - self.lex_data['pii_detection'], 
                   self.lex_data['quality_score']]
        
        x = np.arange(len(metrics))
        width = 0.35
        
        ax2.bar(x - width/2, health_vals, width, label='Health Calls', alpha=0.8, color='#3498db')
        ax2.bar(x + width/2, lex_vals, width, label='Lex Export', alpha=0.8, color='#2ecc71')
        
        ax2.set_ylabel('Score %')
        ax2.set_title('Quality Metrics Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(metrics)
        ax2.legend()
        ax2.set_ylim(0, 100)
        
        plt.tight_layout()
        
        # Embed in tkinter
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(pady=10)
        
        canvas = FigureCanvasTkAgg(fig, canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()
    
    def create_summary_table(self):
        # Summary table
        table_frame = ttk.LabelFrame(self.root, text="Quick Summary")
        table_frame.pack(pady=10, padx=20, fill='x')
        
        # Headers
        ttk.Label(table_frame, text="Dataset", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=10, pady=5)
        ttk.Label(table_frame, text="Files", font=('Arial', 10, 'bold')).grid(row=0, column=1, padx=10, pady=5)
        ttk.Label(table_frame, text="Sample", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=10, pady=5)
        ttk.Label(table_frame, text="Format OK", font=('Arial', 10, 'bold')).grid(row=0, column=3, padx=10, pady=5)
        ttk.Label(table_frame, text="PII Safe", font=('Arial', 10, 'bold')).grid(row=0, column=4, padx=10, pady=5)
        ttk.Label(table_frame, text="Readiness", font=('Arial', 10, 'bold')).grid(row=0, column=5, padx=10, pady=5)
        
        # Health Calls row
        ttk.Label(table_frame, text="Health Calls").grid(row=1, column=0, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.health_data['total_files']:,}").grid(row=1, column=1, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.health_data['sample_size']}").grid(row=1, column=2, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.health_data['format_compliance']:.0f}%").grid(row=1, column=3, padx=10, pady=2)
        ttk.Label(table_frame, text="✓ 0%").grid(row=1, column=4, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.health_data['lex_readiness']:.1f}%", 
                 foreground='#2ecc71' if self.health_data['lex_readiness'] >= 85 else '#f39c12').grid(row=1, column=5, padx=10, pady=2)
        
        # Lex Export row
        ttk.Label(table_frame, text="Lex Export").grid(row=2, column=0, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.lex_data['total_files']:,}").grid(row=2, column=1, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.lex_data['sample_size']}").grid(row=2, column=2, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.lex_data['format_compliance']:.0f}%").grid(row=2, column=3, padx=10, pady=2)
        ttk.Label(table_frame, text="✓ 0%").grid(row=2, column=4, padx=10, pady=2)
        ttk.Label(table_frame, text=f"{self.lex_data['lex_readiness']:.1f}%", 
                 foreground='#2ecc71' if self.lex_data['lex_readiness'] >= 85 else '#f39c12').grid(row=2, column=5, padx=10, pady=2)
    
    def show_detailed_metrics(self):
        # Popup window with detailed metrics
        popup = tk.Toplevel(self.root)
        popup.title("Detailed Metrics")
        popup.geometry("600x400")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(popup)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Health Calls tab
        health_frame = ttk.Frame(notebook)
        notebook.add(health_frame, text="Health Calls Output")
        
        health_text = f"""
Dataset: Health Calls Output
Total Files: {self.health_data['total_files']:,}
Sample Analyzed: {self.health_data['sample_size']} ({self.health_data['sample_size']/self.health_data['total_files']*100:.1f}% coverage)

Quality Metrics:
• Format Compliance: {self.health_data['format_compliance']:.1f}%
• PII Detection Rate: {self.health_data['pii_detection']:.1f}%
• Average Conversation Length: {self.health_data['avg_turns']:.1f} turns
• Average Turn Length: {self.health_data['avg_words']:.1f} words
• Speaker Alternation Rate: {self.health_data['alternation']:.1f}%
• Overall Quality Score: {self.health_data['quality_score']:.1f}/100

Lex Readiness: {self.health_data['lex_readiness']:.1f}%

Characteristics:
• Longer, detailed medical conversations
• Proper PII scrubbing with placeholders
• Realistic appointment scheduling scenarios
• Good for complex interaction training
        """
        
        ttk.Label(health_frame, text=health_text, font=('Courier', 10), justify='left').pack(padx=10, pady=10)
        
        # Lex Export tab
        lex_frame = ttk.Frame(notebook)
        notebook.add(lex_frame, text="Lex Export")
        
        lex_text = f"""
Dataset: Lex Export
Total Files: {self.lex_data['total_files']:,}
Sample Analyzed: {self.lex_data['sample_size']} ({self.lex_data['sample_size']/self.lex_data['total_files']*100:.1f}% coverage)

Quality Metrics:
• Format Compliance: {self.lex_data['format_compliance']:.1f}%
• PII Detection Rate: {self.lex_data['pii_detection']:.1f}%
• Average Conversation Length: {self.lex_data['avg_turns']:.1f} turns
• Average Turn Length: {self.lex_data['avg_words']:.1f} words
• Speaker Alternation Rate: {self.lex_data['alternation']:.1f}%
• Overall Quality Score: {self.lex_data['quality_score']:.1f}/100

Lex Readiness: {self.lex_data['lex_readiness']:.1f}%

Characteristics:
• Shorter, focused conversations
• Excellent speaker alternation
• Clean, well-structured format
• Perfect for concise interaction training
        """
        
        ttk.Label(lex_frame, text=lex_text, font=('Courier', 10), justify='left').pack(padx=10, pady=10)
    
    def show_sample_content(self):
        # Popup with sample conversation content
        popup = tk.Toplevel(self.root)
        popup.title("Sample Content")
        popup.geometry("700x500")
        
        notebook = ttk.Notebook(popup)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Health Calls sample
        health_frame = ttk.Frame(notebook)
        notebook.add(health_frame, text="Health Calls Sample")
        
        health_sample = """
Sample from Health Calls Output:

AGENT: Thank you for calling <NAME> Diagnostics. Please listen to all 
       of the prompts before making a selection...

CUSTOMER: Hi there, I'm just wondering if I could book an appointment 
          for my <NAME>'s child please.

AGENT: OK, which <ADDRESS>?

CUSTOMER: Um, the <ITEM> location is that <NAME>?

AGENT: Yes, we only have one location here in <ADDRESS>. What type 
       of ultrasound?

CUSTOMER: It's renal. So <NAME>, ureter and bladder.

AGENT: OK, let me check... The earliest <NAME> that we have... 
       We actually have a cancellation for <DATE> one o'clock. 
       Would you like that?

CUSTOMER: Yes, please.

AGENT: Alright, so I'll be needing some additional information...

Key Features:
• Proper PII scrubbing with <NAME>, <DATE>, <ADDRESS> placeholders
• Natural conversation flow
• Medical terminology and procedures
• Realistic appointment booking scenario
        """
        
        text_widget1 = tk.Text(health_frame, wrap=tk.WORD, font=('Courier', 9))
        text_widget1.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget1.insert('1.0', health_sample)
        text_widget1.config(state='disabled')
        
        # Lex Export sample
        lex_frame = ttk.Frame(notebook)
        notebook.add(lex_frame, text="Lex Export Sample")
        
        lex_sample = """
Sample from Lex Export:

CUSTOMER: Hi I'd like to book an appointment please

AGENT: Good morning, thank you for calling <NAME>'s office, 
       how can I help you today?

CUSTOMER: I need a checkup and some blood work done

AGENT: Okay could you please state your full <NAME> and <DATE> of birth

CUSTOMER: It's <NAME> DOB <DATE>

AGENT: Thank you <NAME> let me just pull that up one moment please

CUSTOMER: Sure <NAME>.

AGENT: Alright we have availability on <DATE> the 23rd or <DATE> 
       the 24th at 10am or 2pm would either of those work for you

CUSTOMER: The <DATE> at <TIME> is perfect

AGENT: Fantastic let's get that booked then I'll just need to 
       confirm your <PHONE>.

Key Features:
• Clean, focused conversations
• Excellent speaker alternation
• Proper PII handling
• Concise, efficient interactions
        """
        
        text_widget2 = tk.Text(lex_frame, wrap=tk.WORD, font=('Courier', 9))
        text_widget2.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget2.insert('1.0', lex_sample)
        text_widget2.config(state='disabled')
    
    def show_recommendations(self):
        # Popup with recommendations
        popup = tk.Toplevel(self.root)
        popup.title("Deployment Recommendations")
        popup.geometry("600x400")
        
        confidence = (self.health_data['lex_readiness'] + self.lex_data['lex_readiness']) / 2
        
        recommendations = f"""
LEX DEPLOYMENT RECOMMENDATIONS

Overall Assessment: {confidence:.1f}% Readiness
Status: {'✅ READY FOR DEPLOYMENT' if confidence >= 85 else '⚠️ NEEDS MINOR FIXES' if confidence >= 70 else '❌ NOT READY'}

Key Findings:
• Format Compliance: Excellent (99-100%)
• PII Safety: Perfect (0% leakage detected)
• Content Quality: High-quality, realistic conversations
• Statistical Confidence: 95% with ±10% margin of error

Deployment Strategy:

1. IMMEDIATE ACTIONS:
   ✓ Both datasets are ready for Lex import
   ✓ No blocking issues identified
   ✓ PII scrubbing is working correctly

2. DATASET USAGE:
   • Health Calls Output: Use for complex, detailed scenarios
   • Lex Export: Use for focused, efficient interactions
   • Consider combining both for comprehensive training

3. MONITORING:
   • Import both datasets into Lex
   • Monitor initial bot performance
   • Collect user feedback for iterations
   • Track conversation success rates

4. OPTIMIZATION:
   • Health Calls: Excellent conversation depth
   • Lex Export: Perfect speaker alternation
   • Both datasets complement each other well

5. NEXT STEPS:
   • Proceed with Lex deployment
   • Set up performance monitoring
   • Plan for iterative improvements
   • Consider generating additional scenarios

Confidence Level: HIGH
Risk Level: LOW
Recommendation: PROCEED WITH DEPLOYMENT
        """
        
        text_widget = tk.Text(popup, wrap=tk.WORD, font=('Courier', 10))
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', recommendations)
        text_widget.config(state='disabled')

def main():
    root = tk.Tk()
    app = LexQualityGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()