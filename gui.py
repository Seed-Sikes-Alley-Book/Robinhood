"""
Tkinter GUI for the W-pattern stock screener.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path

from config import (
    DEFAULT_RESIDUAL_TOLERANCE, RESIDUAL_TOLERANCE_RANGE,
    CHARTS_DIR
)
from screener import run_screen, export_results, generate_all_charts, plot_pattern

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt


class ScreenerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("W-Pattern Stock Screener (Forming Double Bottom)")
        self.root.geometry("1200x800")
        
        self.results = []
        self.level_used = {}
        self.current_chart_index = 0
        
        self._build_ui()
    
    def _build_ui(self):
        # Control frame
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        # Residual tolerance slider
        ttk.Label(control_frame, text="Residual Tolerance (%):").pack(side=tk.LEFT)
        
        self.tolerance_var = tk.DoubleVar(value=DEFAULT_RESIDUAL_TOLERANCE)
        self.tolerance_slider = ttk.Scale(
            control_frame,
            from_=RESIDUAL_TOLERANCE_RANGE[0],
            to=RESIDUAL_TOLERANCE_RANGE[1],
            variable=self.tolerance_var,
            orient=tk.HORIZONTAL,
            length=200
        )
        self.tolerance_slider.pack(side=tk.LEFT, padx=10)
        
        self.tolerance_label = ttk.Label(
            control_frame, 
            text=f"{DEFAULT_RESIDUAL_TOLERANCE:.1f}%"
        )
        self.tolerance_label.pack(side=tk.LEFT)
        self.tolerance_var.trace("w", self._update_tolerance_label)
        
        # Buttons
        self.run_button = ttk.Button(
            control_frame, text="Run Screener", command=self._run_screener
        )
        self.run_button.pack(side=tk.LEFT, padx=20)
        
        self.refresh_button = ttk.Button(
            control_frame, text="Refresh Data", command=self._refresh_data
        )
        self.refresh_button.pack(side=tk.LEFT)
        
        # Progress
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.progress_var).pack(side=tk.RIGHT)
        
        # Main content area
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left: Results list
        list_frame = ttk.Frame(content_frame, width=300)
        list_frame.pack(side=tk.LEFT, fill=tk.Y)
        list_frame.pack_propagate(False)
        
        ttk.Label(list_frame, text="Results (by Shape Score)", font=("", 10, "bold")).pack()
        
        # Treeview for results
        columns = ("rank", "ticker", "score", "nearness")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=25)
        self.tree.heading("rank", text="#")
        self.tree.heading("ticker", text="Ticker")
        self.tree.heading("score", text="Score")
        self.tree.heading("nearness", text="Near Low %")
        
        self.tree.column("rank", width=30)
        self.tree.column("ticker", width=70)
        self.tree.column("score", width=60)
        self.tree.column("nearness", width=80)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        # Right: Chart area
        self.chart_frame = ttk.Frame(content_frame)
        self.chart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Chart navigation
        nav_frame = ttk.Frame(self.chart_frame)
        nav_frame.pack(fill=tk.X)
        
        self.prev_button = ttk.Button(nav_frame, text="◀ Prev", command=self._prev_chart)
        self.prev_button.pack(side=tk.LEFT)
        
        self.chart_label = ttk.Label(nav_frame, text="Select a stock to view chart")
        self.chart_label.pack(side=tk.LEFT, expand=True)
        
        self.next_button = ttk.Button(nav_frame, text="Next ▶", command=self._next_chart)
        self.next_button.pack(side=tk.RIGHT)
        
        # Canvas for matplotlib
        self.canvas_frame = ttk.Frame(self.chart_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = None
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Adjust tolerance and click 'Run Screener' to begin")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        self.level_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.level_var).pack(side=tk.RIGHT)
    
    def _update_tolerance_label(self, *args):
        self.tolerance_label.config(text=f"{self.tolerance_var.get():.1f}%")
    
    def _run_screener(self, force_refresh: bool = False):
        self.run_button.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.progress_var.set("Running...")
        
        def run():
            try:
                tolerance = self.tolerance_var.get()
                
                def progress(current, total, ticker):
                    self.progress_var.set(f"Scanning {ticker} ({current}/{total})")
                    self.root.update_idletasks()
                
                self.results, self.level_used = run_screen(
                    residual_tolerance=tolerance,
                    force_refresh=force_refresh,
                    progress_callback=progress
                )
                
                # Export and generate charts
                if self.results:
                    export_results(self.results, self.level_used)
                    generate_all_charts(self.results)
                
                self.root.after(0, self._update_results)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, self._enable_buttons)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def _refresh_data(self):
        self._run_screener(force_refresh=True)
    
    def _enable_buttons(self):
        self.run_button.config(state=tk.NORMAL)
        self.refresh_button.config(state=tk.NORMAL)
        self.progress_var.set("Ready")
    
    def _update_results(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Populate tree
        for i, r in enumerate(self.results):
            nearness = abs(r.current_price - r.first_low_price) / r.first_low_price * 100
            self.tree.insert("", tk.END, values=(
                i + 1,
                r.ticker,
                f"{r.shape_score:.3f}",
                f"{nearness:.1f}%"
            ))
        
        # Update status
        self.status_var.set(f"Found {len(self.results)} matching patterns")
        self.level_var.set(f"Relaxation Level: {self.level_used.get('name', 'N/A')}")
        
        # Select first item
        if self.results:
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
            self.current_chart_index = 0
            self._show_chart(0)
    
    def _on_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            rank = int(item["values"][0]) - 1
            self.current_chart_index = rank
            self._show_chart(rank)
    
    def _show_chart(self, index: int):
        if not self.results or index < 0 or index >= len(self.results):
            return
        
        result = self.results[index]
        
        # Clear previous canvas
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        # Generate chart
        fig = plot_pattern(result)
        
        self.canvas = FigureCanvasTkAgg(fig, self.canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        plt.close(fig)
        
        # Update label
        self.chart_label.config(
            text=f"{result.ticker} ({index + 1}/{len(self.results)})"
        )
    
    def _prev_chart(self):
        if self.results and self.current_chart_index > 0:
            self.current_chart_index -= 1
            self._show_chart(self.current_chart_index)
            # Update tree selection
            children = self.tree.get_children()
            self.tree.selection_set(children[self.current_chart_index])
    
    def _next_chart(self):
        if self.results and self.current_chart_index < len(self.results) - 1:
            self.current_chart_index += 1
            self._show_chart(self.current_chart_index)
            # Update tree selection
            children = self.tree.get_children()
            self.tree.selection_set(children[self.current_chart_index])


def run_gui():
    root = tk.Tk()
    app = ScreenerGUI(root)
    root.mainloop()
