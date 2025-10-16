import tkinter as tk
from tkinter import ttk, messagebox, font
import pandas as pd
import os
import json
import csv
import re
import string

class VerificationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Human Verification of Requirement Matches")
        self.root.geometry("1200x1000")

        # --- Data & State ---
        self.mode = None
        self.analysis_df = None
        self.results_data = None
        self.ground_truth_reqs = {}
        self.state = {'single': {}, 'meta': {}}
        self.mode_state = {} 
        self.req_columns = []
        self.current_req_index = 0
        self.match_widgets = {}
        self.current_locations = []
        
        # --- State for match selection ---
        self.match_frames = []
        self.selected_match_index = None
        self.highlight_color = '#cce5ff' # A pleasant light blue
        self.default_bg_color = None

        # --- File Paths ---
        self.state_file_path = os.path.join('results', 'human_verification_state.json')
        self.paths = {
            'single': {
                'analysis': os.path.join('results', 'analysis_single.csv'),
                'results': os.path.join('results', 'single_results.csv'),
                'human_csv': os.path.join('results', 'analysis_single_human.csv'),
            },
            'meta': {
                'analysis': os.path.join('results', 'analysis_meta.csv'),
                'results': os.path.join('results', 'meta_results.csv'),
                'human_csv': os.path.join('results', 'analysis_meta_human.csv'),
            }
        }
        
        self.load_ground_truth_reqs()
        self.create_welcome_screen()

    # --- Keyboard & Event Handlers ---

    def handle_arrow_keys(self, event):
        key = event.keysym
        if key == 'Left': self.prev_req()
        elif key == 'Right': self.next_req()
        elif key == 'Up': self.select_adjacent_match(-1)
        elif key == 'Down': self.select_adjacent_match(1)

    def handle_decision_key(self, event):
        if self.selected_match_index is None or not self.match_frames: return
        decision = 'Yes' if event.keysym.lower() == 'y' else 'No'
        loc = self.current_locations[self.selected_match_index]
        if string_var := self.match_widgets.get(loc):
            string_var.set(decision)
            self.save_and_write()
            self.select_adjacent_match(1)

    def on_req_listbox_select(self, event):
        if not (selection_indices := self.req_listbox.curselection()): return
        new_index = selection_indices[0]
        if new_index != self.current_req_index:
            self.save_and_write(show_status=False)
            self.current_req_index = new_index
            self.display_requirement()

    def bind_shortcuts(self):
        for key in ['<Left>', '<Right>', '<Up>', '<Down>']: self.root.bind(key, self.handle_arrow_keys)
        self.root.bind('<y>', self.handle_decision_key)
        self.root.bind('<n>', self.handle_decision_key)

    def unbind_shortcuts(self):
        for key in ['<Left>', '<Right>', '<Up>', '<Down>', '<y>', '<n>']: self.root.unbind(key)

    # --- Match Selection & Highlighting Logic ---

    def select_match(self, index_to_select):
        if not self.match_frames: return
        self.selected_match_index = index_to_select
        self.update_match_highlights()
        self.root.after(100, self.scroll_to_selected)

    def scroll_to_selected(self):
        if self.selected_match_index is None or not self.match_frames: return
        self.root.update_idletasks()
        frame_to_see = self.match_frames[self.selected_match_index]
        canvas_height, scroll_region_height = self.canvas.winfo_height(), self.scrollable_frame.winfo_height()
        if scroll_region_height > canvas_height:
            item_top_frac = frame_to_see.winfo_y() / scroll_region_height
            self.canvas.yview_moveto(item_top_frac)

    def select_adjacent_match(self, direction):
        if not self.match_frames: return
        if self.selected_match_index is None:
            new_index = 0 if direction == 1 else len(self.match_frames) - 1
        else:
            new_index = self.selected_match_index + direction
        if 0 <= new_index < len(self.match_frames):
            self.select_match(new_index)

    def update_match_highlights(self):
        for i, frame in enumerate(self.match_frames):
            is_selected = (i == self.selected_match_index)
            new_color = self.highlight_color if is_selected else self.default_bg_color
            relief = 'solid' if is_selected else 'flat'
            borderwidth = 1 if is_selected else 0
            try:
                frame.config(bg=new_color, relief=relief, borderwidth=borderwidth)
                for widget in frame.winfo_children():
                    widget.config(bg=new_color)
            except tk.TclError: pass

    def bind_recursive_click(self, widget, index):
        widget.bind("<Button-1>", lambda e: self.select_match(index))
        for child in widget.winfo_children():
            self.bind_recursive_click(child, index)

    # --- UI Creation & Display ---

    def create_welcome_screen(self):
        self.clear_window()
        self.unbind_shortcuts()
        self.welcome_frame = ttk.Frame(self.root, padding="20"); self.welcome_frame.pack(expand=True)
        ttk.Label(self.welcome_frame, text="Select Analysis File to Verify", font=("Helvetica", 16, "bold")).pack(pady=20)
        ttk.Button(self.welcome_frame, text="Analyze analysis_single.csv", command=lambda: self.setup_mode('single')).pack(pady=10, ipadx=10, ipady=5)
        ttk.Button(self.welcome_frame, text="Analyze analysis_meta.csv", command=lambda: self.setup_mode('meta')).pack(pady=10, ipadx=10, ipady=5)

    def setup_mode(self, mode):
        if self.mode: self.save_and_write(show_status=False)
        self.mode = mode
        
        req_files = [self.paths[self.mode]['analysis'], self.paths[self.mode]['results'], 'requirements_list.csv']
        if missing_files := [f for f in req_files if not os.path.exists(f)]:
            messagebox.showerror("File Not Found", f"Missing files:\n\n{', '.join(missing_files)}"); self.mode = None; return

        self.analysis_df = pd.read_csv(self.paths[self.mode]['analysis'], sep=';', dtype=str).fillna('')
        with open(self.paths[self.mode]['results'], 'r', encoding='utf-8') as f: self.results_data = list(csv.reader(f, delimiter=';'))
        
        self.load_state()
        self.req_columns = [col for col in self.analysis_df.columns if col.strip().startswith('R.')]
        self.current_req_index = 0
        self.create_main_ui()

        self.req_listbox.delete(0, tk.END)
        for req_id in self.req_columns: self.req_listbox.insert(tk.END, req_id)
        self.display_requirement()

    def create_main_ui(self):
        self.clear_window()
        self.bind_shortcuts()
        if self.default_bg_color is None: self.default_bg_color = self.root.cget('bg')
        
        main_pane = ttk.Frame(self.root); main_pane.pack(fill='both', expand=True)
        left_frame = ttk.Frame(main_pane, width=200, padding=5); left_frame.pack(side='left', fill='y')
        ttk.Label(left_frame, text="Requirements", font=("Helvetica", 12, "bold")).pack(anchor='w', pady=(0, 5))
        list_frame = ttk.Frame(left_frame); list_frame.pack(fill='both', expand=True)
        list_scrollbar = ttk.Scrollbar(list_frame, orient='vertical')
        self.req_listbox = tk.Listbox(list_frame, yscrollcommand=list_scrollbar.set, exportselection=False, font=("Courier", 10))
        list_scrollbar.config(command=self.req_listbox.yview)
        list_scrollbar.pack(side='right', fill='y'); self.req_listbox.pack(side='left', fill='both', expand=True)
        self.req_listbox.bind('<<ListboxSelect>>', self.on_req_listbox_select)

        right_frame = ttk.Frame(main_pane, padding="10"); right_frame.pack(side='left', fill='both', expand=True)
        
        control_frame = ttk.Frame(right_frame); control_frame.pack(fill='x', side='top')
        ttk.Button(control_frame, text="< Previous", command=self.prev_req).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Next >", command=self.next_req).pack(side='left', padx=5)
        self.nav_label = ttk.Label(control_frame, text="", font=("Helvetica", 10)); self.nav_label.pack(side='left', padx=20)
        
        # --- NEW: Validate button and Switch frame ---
        switch_frame = ttk.Frame(control_frame); switch_frame.pack(side='right')
        validate_btn = ttk.Button(control_frame, text="Validate Output", command=self.validate_all_matches)
        validate_btn.pack(side='right', padx=(0, 20))
        ttk.Label(switch_frame, text="Switch to:").pack(side='left', padx=5)
        single_btn = ttk.Button(switch_frame, text="Single Analysis", command=lambda: self.setup_mode('single')); single_btn.pack(side='left')
        meta_btn = ttk.Button(switch_frame, text="Meta Analysis", command=lambda: self.setup_mode('meta')); meta_btn.pack(side='left', padx=5)
        if self.mode == 'single': single_btn['state'] = 'disabled'
        else: meta_btn['state'] = 'disabled'
        
        gt_frame = ttk.Frame(right_frame); gt_frame.pack(fill='x', side='top', pady=5)
        self.gt_id_label = ttk.Label(gt_frame, text="ID: R.XX.X", font=("Helvetica", 14, "bold")); self.gt_id_label.pack(anchor='w')
        self.gt_text_label = tk.Message(gt_frame, text="Req text", width=950, font=("Helvetica", 13, "bold")); self.gt_text_label.pack(anchor='w', fill='x', pady=5)
        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=5)

        canvas_frame = ttk.Frame(right_frame); canvas_frame.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0); scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")
        
        self.status_bar = ttk.Label(
            self.root,
            text=f"Mode: {self.mode}  |  Tips: Use Up and Down to change selection, Left and Right for next or previous, Y or N for yes or no",
            relief=tk.SUNKEN,
            anchor='w',
            padding=5
        )
        self.status_bar.pack(side='bottom', fill='x')

    def display_requirement(self):
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        
        self.match_widgets, self.current_locations, self.match_frames = {}, [], []
        self.selected_match_index = None
        
        if not self.req_columns: return

        req_id = self.req_columns[self.current_req_index]
        self.nav_label.config(text=f"Requirement {self.current_req_index + 1} of {len(self.req_columns)}")
        self.gt_id_label.config(text=f"ID: {req_id}")
        self.gt_text_label.config(text=self.ground_truth_reqs.get(req_id, "Requirement text not found."))
        
        all_locations = sorted(self._get_all_locations_for_req(req_id), key=self.sort_cell_location)
        self.current_locations = all_locations
        
        if not all_locations:
            ttk.Label(self.scrollable_frame, text="No matches found for this requirement.", font=("Helvetica", 10, "italic")).pack(pady=10)
        else:
            for i, loc in enumerate(all_locations):
                frame = tk.Frame(self.scrollable_frame, bg=self.default_bg_color); frame.pack(fill='x', anchor='w', padx=2, pady=2)
                self.match_frames.append(frame)
                self.bind_recursive_click(frame, i)

                content = self.get_cell_content(loc)
                decision_var = tk.StringVar() 
                if decision := self.mode_state.get(req_id, {}).get(loc): decision_var.set(decision)
                self.match_widgets[loc] = decision_var

                loc_label = tk.Label(frame, text=f"{loc}:", font=("Courier", 11, "bold")); loc_label.grid(row=0, column=0, sticky='nw', padx=(0, 10))
                content_label = tk.Message(frame, text=content, width=700); content_label.grid(row=0, column=1, sticky='w')
                
                radio_yes = tk.Radiobutton(frame, text="Yes", variable=decision_var, value="Yes", command=self.save_and_write, activebackground=self.highlight_color, selectcolor=self.default_bg_color)
                radio_yes.grid(row=0, column=2, sticky='e', padx=10)
                radio_no = tk.Radiobutton(frame, text="No", variable=decision_var, value="No", command=self.save_and_write, activebackground=self.highlight_color, selectcolor=self.default_bg_color)
                radio_no.grid(row=0, column=3, sticky='e', padx=5)
                
                frame.grid_columnconfigure(1, weight=1)
                if i < len(all_locations) - 1:
                    ttk.Separator(self.scrollable_frame, orient='horizontal').pack(fill='x', pady=5, padx=10)

        if self.match_frames: self.select_match(0)
        
        if self.req_listbox.size() > 0:
            self.req_listbox.selection_clear(0, tk.END)
            self.req_listbox.selection_set(self.current_req_index)
            self.req_listbox.activate(self.current_req_index)
            self.req_listbox.see(self.current_req_index)

    # --- Core Logic & File I/O ---

    def next_req(self):
        if not self.req_columns: return
        self.save_and_write()
        if self.current_req_index < len(self.req_columns) - 1:
            self.current_req_index += 1; self.display_requirement()
        else: self.status_bar.config(text="Already at the last requirement.")

    def prev_req(self):
        if not self.req_columns: return
        self.save_and_write()
        if self.current_req_index > 0:
            self.current_req_index -= 1; self.display_requirement()
        else: self.status_bar.config(text="Already at the first requirement.")
            
    def save_and_write(self, show_status=True):
        if not self.req_columns or not self.mode: return
        req_id = self.req_columns[self.current_req_index]
        if req_id not in self.mode_state: self.mode_state[req_id] = {}
        for location, var in self.match_widgets.items(): self.mode_state[req_id][location] = var.get()
        self.save_state_to_json()
        self.write_human_csv()
        if show_status:
            self.status_bar.config(text=f"Saved state for {req_id} at {pd.Timestamp.now().strftime('%H:%M:%S')}")

    def write_human_csv(self):
        df_copy = self.analysis_df.copy()
        for req_id in self.req_columns:
            if req_id in self.mode_state:
                df_copy[req_id] = df_copy[req_id].apply(lambda cell: self.filter_cell_locations(cell, self.mode_state[req_id]))
        df_copy.to_csv(self.paths[self.mode]['human_csv'], sep=';', index=False)
        
    def filter_cell_locations(self, cell_value, decisions):
        if not cell_value or pd.isna(cell_value): return ''
        locations = str(cell_value).split(',')
        return ','.join([loc for loc in locations if decisions.get(loc) == 'Yes'])

    # --- NEW: Validation Logic ---

    def _get_all_locations_for_req(self, req_id):
        """Helper to parse the dataframe for all unique match locations for a req_id."""
        matches = self.analysis_df[req_id].dropna().unique()
        return list(set(loc for group in matches if group for loc in str(group).split(',')))

    def validate_all_matches(self):
        """Checks if all matches for the current mode have a 'Yes' or 'No' decision."""
        self.save_and_write(show_status=False) # Save any pending changes first

        requirements_with_issues = []
        for req_id in self.req_columns:
            all_locations = self._get_all_locations_for_req(req_id)
            if not all_locations: continue

            for loc in all_locations:
                decision = self.mode_state.get(req_id, {}).get(loc)
                if not decision: # Checks for None or empty string ''
                    requirements_with_issues.append(req_id)
                    break # Move to the next requirement ID
        
        if requirements_with_issues:
            message = "The following requirements still have undecided matches:\n\n- " + "\n- ".join(requirements_with_issues)
            messagebox.showwarning("Validation Incomplete", message)
        else:
            messagebox.showinfo("Validation Complete", "All matches have been reviewed for the current mode. Well done!")

    # --- Utility and File I/O ---

    def load_state(self):
        try:
            if os.path.exists(self.state_file_path):
                with open(self.state_file_path, 'r') as f: self.state = json.load(f)
            else: self.state = {'single': {}, 'meta': {}}
        except json.JSONDecodeError: self.state = {'single': {}, 'meta': {}}
        if 'single' not in self.state: self.state['single'] = {}
        if 'meta' not in self.state: self.state['meta'] = {}
        self.mode_state = self.state[self.mode]

    def save_state_to_json(self):
        self.state[self.mode] = self.mode_state
        with open(self.state_file_path, 'w') as f: json.dump(self.state, f, indent=2)
    
    def load_ground_truth_reqs(self):
        try:
            req_df = pd.read_csv('requirements_list.csv', quotechar='"')
            self.ground_truth_reqs = pd.Series(req_df.Requirement.values, index=req_df['Interview ID']).to_dict()
        except FileNotFoundError: pass

    def get_cell_content(self, location_str):
        match = re.match(r"([A-Z]+)(\d+)", location_str)
        if not match: return f"Invalid location format: {location_str}"
        col_str, row_str = match.groups()
        row_idx, col_idx = int(row_str) - 1, 0
        for char in col_str: col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
        col_idx -= 1
        try: return self.results_data[row_idx][col_idx]
        except IndexError: return f"Error: Location {location_str} is out of bounds."

    def sort_cell_location(self, loc):
        match = re.match(r"([A-Z]+)(\d+)", loc)
        if match: return (match.groups()[0], int(match.groups()[1]))
        return (loc, 0)

    def clear_window(self):
        for widget in self.root.winfo_children(): widget.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    os.makedirs('results', exist_ok=True)
    app = VerificationApp(root)
    root.mainloop()