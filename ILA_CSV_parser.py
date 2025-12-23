from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from helper_funcs import *

class ILACSVParserTab(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._build_vars()
        self._build_ui()

    # --- Variables ---

    def _build_vars(self):

        # Raw DBs by source type
        self.db_raw_ila = {}
        self.db_raw_stp = {}
        # Active raw DB
        self.db_raw = {}
        self.db_converted = {}

        self.csv_kind_var = tk.StringVar(value="unknown")

        # Section 1 Browse & Search
        self.csv_path_var      = tk.StringVar()
        self.signal_filter_var = tk.StringVar()
        self.search_status_var = tk.StringVar(value="No file loaded.")

        # Section 2 Settings
        self.name_display_mode  = tk.StringVar(value="full")
        self.signals_full_names = []

        self.data_type_var = tk.StringVar(value="1")

        self.sign_bits_var = tk.StringVar(value="1")
        self.int_bits_var  = tk.StringVar(value="0")
        self.frac_bits_var = tk.StringVar(value="15")

        self.exp_bits_var = tk.StringVar(value="6")
        self.man_bits_var = tk.StringVar(value="13")

        self.data_par_var      = tk.StringVar(value="1")
        self.data_par_mode_var = tk.StringVar(value="serial")

        self.complex_var = tk.BooleanVar(value=True)

        self.valid_signal_var = tk.StringVar()
        self.use_valid_var    = tk.BooleanVar(value=False)

        self.sop_signal_var = tk.StringVar()
        self.use_sop_var    = tk.BooleanVar(value=False)

        self.eop_signal_var = tk.StringVar()
        self.use_eop_var    = tk.BooleanVar(value=False)

        # Packet output selection when using VALID/SOP/EOP filtering
        # 'concat' -> one long array (all packets)
        # 'multi'  -> create multiple arrays (signal__pkt0, signal__pkt1, ...)
        self.packet_output_var = tk.StringVar(value="concat")

        self.convert_status_var = tk.StringVar(value="")

        self.combine_mode_var = tk.StringVar(value="ri")
        self.combine_swap_var = tk.BooleanVar(value=False)

        # Section 3 Export
        self.output_dir_var    = tk.StringVar(value=".")
        self.base_filename_var = tk.StringVar(value="")
        self.write_status_var  = tk.StringVar(value="")
        self.BTE_format_var    = tk.BooleanVar(value=False)
        self.export_format_var = tk.StringVar(value="as-is")
        self.wr_sign_bit_var   = tk.StringVar(value="1")
        self.wr_int_bits_var   = tk.StringVar(value="0")
        self.wr_frac_bits_var  = tk.StringVar(value="15")

        # Section 4 Plot
        self.plot_from_file_bte_var = tk.BooleanVar(value=False)
        self.num_of_packets_var     = tk.StringVar(value="1")
        self.same_plot_window_var = tk.BooleanVar(value=False)

    # --- UI Layout ---

    def _build_ui(self):
        # Section 1
        sec1 = ttk.LabelFrame(self, text="1. Select file and search signals")
        sec1.pack(fill="x", padx=10, pady=5)

        ttk.Label(sec1, text="CSV file:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        entry_csv = ttk.Entry(sec1, textvariable=self.csv_path_var)
        entry_csv.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        ttk.Button(sec1, text="Browse...", command=self.browse_csv).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(sec1, text="Detect file type", command=self.detect_file_type).grid(row=0, column=3, padx=(0, 5), pady=5)

        ttk.Label(sec1, text="Signal name contains:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(sec1, textvariable=self.signal_filter_var).grid(row=1, column=1, sticky="we", padx=5, pady=5)
        ttk.Button(sec1, text="Search", command=self.search_signals).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(sec1, textvariable=self.search_status_var).grid(
            row=2, column=0, columnspan=4, sticky="w", padx=5, pady=5
        )

        sec1.columnconfigure(1, weight=1)

        # Section 2
        sec2 = ttk.LabelFrame(self, text="2. Select signals, convert, and inspect")
        sec2.pack(fill="both", expand=True, padx=10, pady=5)

        name_row = ttk.Frame(sec2)
        name_row.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))

        ttk.Label(name_row, text="Signal name view:").pack(side="left")
        ttk.Radiobutton(
            name_row,
            text="Full name",
            variable=self.name_display_mode,
            value="full",
            command=self._refresh_signals_listbox,
        ).pack(side="left", padx=(5, 2))
        ttk.Radiobutton(
            name_row,
            text="Short name",
            variable=self.name_display_mode,
            value="short",
            command=self._refresh_signals_listbox,
        ).pack(side="left", padx=(2, 0))

        ttk.Label(sec2, text="Input signals:").grid(
            row=1, column=0, sticky="w", padx=5, pady=(5, 0)
        )

        input_frame = ttk.Frame(sec2)
        input_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))

        self.signals_listbox = tk.Listbox(input_frame, selectmode="extended", height=8)
        self.signals_listbox.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(input_frame, orient="vertical", command=self.signals_listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.signals_listbox.config(yscrollcommand=scroll.set)

        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        settings = ttk.Frame(sec2)
        settings.grid(row=3, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(settings, text="Data type & precision:").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )

        fixed_row = ttk.Frame(settings)
        fixed_row.grid(row=1, column=0, sticky="w", pady=1)

        self.rb_fixed = ttk.Radiobutton(
            fixed_row, text="Fixed", variable=self.data_type_var, value="1"
        )
        self.rb_fixed.pack(side="left")

        ttk.Label(fixed_row, text="  [sign, int, frac]:").pack(side="left", padx=(4, 2))
        ttk.Entry(fixed_row, width=4, textvariable=self.sign_bits_var).pack(side="left", padx=2)
        ttk.Entry(fixed_row, width=4, textvariable=self.int_bits_var).pack(side="left", padx=2)
        ttk.Entry(fixed_row, width=4, textvariable=self.frac_bits_var).pack(side="left", padx=2)

        float_row = ttk.Frame(settings)
        float_row.grid(row=2, column=0, sticky="w", pady=1)

        self.rb_float = ttk.Radiobutton(
            float_row, text="Float", variable=self.data_type_var, value="2"
        )
        self.rb_float.pack(side="left")

        ttk.Label(float_row, text="  [exp, mant]:").pack(side="left", padx=(4, 2))
        ttk.Entry(float_row, width=4, textvariable=self.exp_bits_var).pack(side="left", padx=(19, 0))
        ttk.Entry(float_row, width=4, textvariable=self.man_bits_var).pack(side="left", padx=4)

        self.rb_asis = ttk.Radiobutton(
            settings, text="As-is", variable=self.data_type_var, value="3"
        )
        self.rb_asis.grid(row=3, column=0, sticky="w", pady=(1, 5))

        ttk.Checkbutton(settings, text="Complex data (I/Q)", variable=self.complex_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=5
        )

        concat_row = ttk.Frame(settings)
        concat_row.grid(row=5, column=0, sticky="w", pady=2)

        ttk.Label(concat_row, text="Data concatenated:").pack(side="left")
        ttk.Entry(concat_row, width=4, textvariable=self.data_par_var).pack(
            side="left", padx=(4, 0)
        )
        ttk.Label(concat_row, text="Concatenation mode:").pack(side="left")
        ttk.Radiobutton(
            concat_row,
            text="Serial",
            variable=self.data_par_mode_var,
            value="serial",
        ).pack(side="left", padx=(4, 2))
        ttk.Radiobutton(
            concat_row,
            text="Parallel",
            variable=self.data_par_mode_var,
            value="parallel",
        ).pack(side="left", padx=(2, 4))

        valid_row = ttk.Frame(settings)
        valid_row.grid(row=6, column=0, sticky="w", pady=2)

        ttk.Label(valid_row, text="Valid:").pack(side="left")

        self.valid_signal_entry = ttk.Entry(
            valid_row,
            textvariable=self.valid_signal_var,
            state="readonly",
            width=30,
        )
        self.valid_signal_entry.pack(side="left", padx=(4, 0))

        ttk.Button(
            valid_row,
            text="Select…",
            command=lambda s="valid": self.open_selector(s),
        ).pack(side="left", padx=(4, 0))

        self.use_valid_check = ttk.Checkbutton(
            valid_row,
            text="Use",
            variable=self.use_valid_var,
        )
        self.use_valid_check.pack(side="left", padx=(4, 8))

        ttk.Label(valid_row, text="SOP:").pack(side="left")

        self.sop_signal_entry = ttk.Entry(
            valid_row,
            textvariable=self.sop_signal_var,
            state="readonly",
            width=30,
        )
        self.sop_signal_entry.pack(side="left", padx=(4, 0))

        ttk.Button(
            valid_row,
            text="Select…",
            command=lambda s="sop": self.open_selector(s),
        ).pack(side="left", padx=(4, 0))

        self.use_sop_check = ttk.Checkbutton(
            valid_row,
            text="Use",
            variable=self.use_sop_var,
        )
        self.use_sop_check.pack(side="left", padx=(4, 8))

        ttk.Label(valid_row, text="EOP:").pack(side="left")

        self.eop_signal_entry = ttk.Entry(
            valid_row,
            textvariable=self.eop_signal_var,
            state="readonly",
            width=30,
        )
        self.eop_signal_entry.pack(side="left", padx=(4, 0))

        ttk.Button(
            valid_row,
            text="Select…",
            command=lambda s="eop": self.open_selector(s),
        ).pack(side="left", padx=(4, 0))

        self.use_eop_check = ttk.Checkbutton(
            valid_row,
            text="Use",
            variable=self.use_eop_var,
        )
        self.use_eop_check.pack(side="left", padx=(4, 0))

        packet_row = ttk.Frame(settings)
        packet_row.grid(row=7, column=0, sticky="w", pady=2)

        ttk.Label(packet_row, text="Packet output:").pack(side="left")
        ttk.Radiobutton(
            packet_row,
            text="One long",
            variable=self.packet_output_var,
            value="concat",
        ).pack(side="left", padx=(6, 2))
        ttk.Radiobutton(
            packet_row,
            text="Multiple arrays",
            variable=self.packet_output_var,
            value="multi",
        ).pack(side="left", padx=(2, 0))

        combine_row = ttk.Frame(settings)
        combine_row.grid(row=8, column=0, sticky="w", pady=2)

        ttk.Label(combine_row, text="Combine mode:").pack(side="left")
        ttk.Radiobutton(
            combine_row,
            text="Real/Imag",
            variable=self.combine_mode_var,
            value="ri",
        ).pack(side="left", padx=(4, 2))
        ttk.Radiobutton(
            combine_row,
            text="Even/Odd",
            variable=self.combine_mode_var,
            value="eo",
        ).pack(side="left", padx=(2, 4))
        ttk.Checkbutton(
            combine_row,
            text="Swap roles (1→2)",
            variable=self.combine_swap_var,
        ).pack(side="left", padx=(4, 0))

        btn_row = ttk.Frame(settings)
        btn_row.grid(row=9, column=0, sticky="w", pady=(6, 2))

        ttk.Button(btn_row, text="Convert selected", command=self.convert_data).pack(
            side="left"
        )
        ttk.Button(btn_row, text="Combine selected", command=self.combine_selected_signals).pack(
            side="left", padx=(6, 0)
        )

        ttk.Label(settings, textvariable=self.convert_status_var).grid(
            row=10, column=0, sticky="w", pady=(2, 0)
        )

        sec2.columnconfigure(0, weight=1)
        sec2.rowconfigure(2, weight=1)
        sec2.rowconfigure(5, weight=1)

        ttk.Label(sec2, text="Converted signals (double-click to view):").grid(
            row=4, column=0, sticky="w", padx=5, pady=(10, 0)
        )

        conv_frame = ttk.Frame(sec2)
        conv_frame.grid(row=5, column=0, sticky="nsew", padx=5, pady=(0, 5))

        self.converted_listbox = tk.Listbox(conv_frame, selectmode="extended", height=8)
        self.converted_listbox.grid(row=0, column=0, sticky="nsew")
        conv_scroll = ttk.Scrollbar(conv_frame, orient="vertical", command=self.converted_listbox.yview)
        conv_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 5))
        self.converted_listbox.config(yscrollcommand=conv_scroll.set)

        conv_frame.columnconfigure(0, weight=1)
        conv_frame.rowconfigure(0, weight=1)

        self.converted_listbox.bind("<Double-Button-1>", self.show_converted_signal)

        # Section 3
        sec3 = ttk.LabelFrame(self, text="3. Write converted data to files")
        sec3.pack(fill="x", padx=10, pady=5)

        ttk.Label(sec3, text="Output directory:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        ttk.Entry(sec3, textvariable=self.output_dir_var).grid(
            row=0, column=1, columnspan=2, sticky="we", padx=5, pady=5
        )
        ttk.Button(sec3, text="Browse...", command=self.browse_output_dir).grid(
            row=0, column=3, padx=5, pady=5
        )
        ttk.Label(sec3, text="File name:").grid(
            row=0, column=4, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec3, width=18, textvariable=self.base_filename_var).grid(
            row=0, column=5, sticky="we", padx=(0, 5), pady=5
        )
        ttk.Button(sec3, text="Export files", command=self.write_files).grid(
            row=0, column=6, padx=5, pady=5
        )

        row1 = ttk.Frame(sec3)
        row1.grid(row=1, column=0, columnspan=7, sticky="w", padx=5, pady=5)

        self.BTE_format_check = ttk.Checkbutton(
            row1,
            text="Export in BTE Format",
            variable=self.BTE_format_var
        )
        self.BTE_format_check.pack(side="left")

        ttk.Label(row1, text="   Export format:").pack(side="left", padx=(8, 2))
        self.export_format_menu = ttk.Combobox(
            row1,
            state="readonly",
            width=8,
            textvariable=self.export_format_var,
            values=["as-is", "fixed", "float"],
        )
        self.export_format_menu.pack(side="left", padx=(0, 8))

        ttk.Label(row1, text="   Export fixed precision [sign, int, frac]:").pack(
            side="left", padx=(5, 2)
        )
        ttk.Entry(row1, width=4, textvariable=self.wr_sign_bit_var).pack(
            side="left", padx=2
        )
        ttk.Entry(row1, width=4, textvariable=self.wr_int_bits_var).pack(
            side="left", padx=2
        )
        ttk.Entry(row1, width=4, textvariable=self.wr_frac_bits_var).pack(
            side="left", padx=2
        )

        ttk.Label(sec3, textvariable=self.write_status_var).grid(
            row=2, column=0, columnspan=7, sticky="w", padx=5, pady=5
        )

        sec3.columnconfigure(1, weight=2)
        sec3.columnconfigure(5, weight=1)

        # Section 4
        sec4 = ttk.LabelFrame(self, text="4. Plot data")
        sec4.pack(fill="x", padx=10, pady=5)

        ttk.Label(sec4, text="Plot converted signal or data from file").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5
        )

        ttk.Button(sec4, text="Plot signal…", command=self.plot_selected_signal_popup).grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )

        ttk.Button(sec4, text="MultiPlot…", command=self.plot_multi_signals).grid(
            row=1, column=1, sticky="w", padx=5, pady=5
        )

        ttk.Button(sec4, text="Plot from file…", command=self.plot_from_file).grid(
            row=1, column=2, sticky="w", padx=5, pady=5
        )

        self.plot_from_file_bte_check = ttk.Checkbutton(
            sec4,
            text="BTE File",
            variable=self.plot_from_file_bte_var
        )
        self.plot_from_file_bte_check.grid(row=1, column=3, sticky="w", padx=5, pady=5)

        ttk.Label(sec4, text="Packets").grid(
            row=1, column=4, sticky="w", padx=5, pady=5
        )
        ttk.Entry(sec4, width=3, textvariable=self.num_of_packets_var).grid(
            row=1, column=5, sticky="w", padx=(2, 0), pady=5
        )

        self.same_plot_window_check = ttk.Checkbutton(
            sec4,
            text="Same plot window",
            variable=self.same_plot_window_var
        )
        self.same_plot_window_check.grid(row=1, column=6, sticky="w", padx=5, pady=5)

    # ------------- Core GUI methods (browse, search, convert, combine, plot, write) -------------

    # --- Section 1 actions ---

    def load_signals_from_stp_csv(self, csv_path: Path, name_filter: str = "") -> dict:
        name_filter_l = (name_filter or "").strip().lower()

        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [ln.rstrip("\n") for ln in f]

        # ---- Locate sections + collect "signals_list" from Groups: ----
        data_idx = None
        groups_idx = None

        for i, ln in enumerate(lines):
            s = ln.strip().lower()
            if s == "groups:":
                groups_idx = i
            if s == "data:":
                data_idx = i
                break  # important: stop scanning header sections once Data: starts

        if data_idx is None:
            raise ValueError("Not a Quartus SignalTap CSV: missing 'Data:' section.")
        if data_idx + 1 >= len(lines):
            raise ValueError("STP CSV is missing header row after 'Data:' section.")

        # signals_list: set of signal names defined in Groups section
        signals_list = set()
        if groups_idx is not None:
            # Between "Groups:" and "Data:" there are lines like:
            #   some_signal_name=...
            # We only take the left side of '='
            for ln in lines[groups_idx + 1: data_idx]:
                if "=" not in ln:
                    continue
                left = ln.split("=", 1)[0].strip()
                if left:
                    signals_list.add(left)

        # ---- Parse Data header row ----
        header_all = [t.strip() for t in lines[data_idx + 1].split(",") if t.strip() != ""]
        if len(header_all) < 2:
            raise ValueError("STP CSV header is too short.")

        # First column is time; remaining are signal columns
        sig_names_all = header_all[1:]

        # Apply signals_list filter ONLY if we actually found any signals in Groups:
        if signals_list:
            sig_names = [n for n in sig_names_all if n in signals_list]
        else:
            sig_names = sig_names_all

        if not sig_names:
            raise ValueError("No matching STP signals found (after applying signals_list filter).")

        cols = {name: [] for name in sig_names}

        # ---- Parse data rows ----
        # We need mapping from name -> original column index in the CSV row
        name_to_col = {name: (1 + sig_names_all.index(name)) for name in sig_names}

        for ln in lines[data_idx + 2:]:
            if not ln.strip():
                continue
            toks = [t.strip() for t in ln.split(",")]
            if len(toks) < 2:
                continue

            # For safety: pad rows
            need = 1 + len(sig_names_all)
            if len(toks) < need:
                toks += [""] * (need - len(toks))

            for name, col_idx in name_to_col.items():
                v = toks[col_idx].strip() if col_idx < len(toks) else ""
                if v == "":
                    v = "X"
                cols[name].append(v)

        def split_on_x(samples):
            segs, curr = [], []
            for v in samples:
                if str(v).strip().upper() == "X":
                    if curr:
                        segs.append(curr)
                        curr = []
                else:
                    curr.append(v)
            if curr:
                segs.append(curr)
            return segs

        db = {}
        for idx, name in enumerate(sig_names):
            if name_filter_l and name_filter_l not in name.lower():
                continue

            segs = split_on_x(cols.get(name, []))
            if not segs:
                continue

            if len(segs) == 1:
                db[name] = {"idx": idx, "samples": segs[0]}
            else:
                for k, seg in enumerate(segs):
                    db[f"{name}__seg{k}"] = {"idx": idx, "samples": seg}

        return db

    def browse_csv(self):
        filename = filedialog.askopenfilename(
            title="Select ILA/STP CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_path_var.set(filename)

    def detect_file_type(self):
        """Detect whether the selected CSV is Quartus SignalTap (STP) or Vivado ILA."""
        csv_path = Path(self.csv_path_var.get().strip())
        if not csv_path.is_file():
            messagebox.showerror("Detect", "Please select a valid CSV file.")
            return

        kind = detect_csv_kind(csv_path)
        self.csv_kind_var.set(kind)

        if kind == "quartus_stp":
            msg = "Detected: Quartus SignalTap (STP) CSV"
        elif kind == "vivado_ila":
            msg = "Detected: Vivado ILA CSV"
        else:
            msg = "Detected: Unknown CSV format (defaulting to Vivado ILA parser)"

        self.search_status_var.set(msg)
        messagebox.showinfo("Detect file type", msg)

    def search_signals(self):
        csv_path = Path(self.csv_path_var.get().strip())
        if not csv_path.is_file():
            messagebox.showerror("Error", "Please select a valid CSV file.")
            return

        name_filter = self.signal_filter_var.get().strip()

        kind = detect_csv_kind(csv_path)
        self.csv_kind_var.set(kind)

        try:
            if kind == "quartus_stp":
                db = self.load_signals_from_stp_csv(csv_path, name_filter)
                self.db_raw_stp = db
                self.db_raw_ila = {}
            else:
                db = load_signals_from_csv(csv_path, name_filter)
                self.db_raw_ila = db
                self.db_raw_stp = {}
        except Exception as e:
            self.db_raw = {}
            self.signals_listbox.delete(0, tk.END)
            self.search_status_var.set(f"Error: {e}")
            messagebox.showerror("Error", str(e))
            return

        self.db_raw = db
        self.db_converted = {}
        self.convert_status_var.set("")
        self.write_status_var.set("")
        self.converted_listbox.delete(0, tk.END)

        sigs_sorted = sorted(db.keys())
        self.signals_full_names = sigs_sorted

        # Refresh listbox according to current view mode
        self._refresh_signals_listbox()

        self.valid_signal_var.set("")  # no valid selected by default
        self.sop_signal_var.set("")  # no valid selected by default
        self.eop_signal_var.set("")  # no valid selected by default

        self.search_status_var.set(f"Found {len(db)} signal(s).")

    # --- Section 2 actions ---

    def _refresh_signals_listbox(self):
        """Refresh the input signals listbox according to name_display_mode."""
        # If we haven't loaded anything yet, nothing to do
        self.signals_listbox.delete(0, tk.END)

        mode = self.name_display_mode.get()
        for full in self.signals_full_names:
            if mode == "short":
                disp = full.split("/")[-1]
            else:
                disp = full
            self.signals_listbox.insert(tk.END, disp)

    def convert_data(self):
        if not self.db_raw:
            messagebox.showerror("Error", "No signals loaded. Run Search first.")
            return

        selection = self.signals_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select at least one signal to convert.")
            return

        selected_names = [self.signals_full_names[i] for i in selection]

        # Handle optional valid signal
        # Optional VALID filter (same logic as convert_data)
        use_valid = getattr(self, "use_valid_var", None)
        use_sop = getattr(self, "use_sop_var", None)
        use_eop = getattr(self, "use_eop_var", None)
        valid_name, sop_name, eop_name = "", "", ""
        if use_valid is not None and self.use_valid_var.get():
            valid_name = self.valid_signal_var.get().strip()
        if use_sop is not None and self.use_sop_var.get():
            sop_name = self.sop_signal_var.get().strip()
        if use_eop is not None and self.use_eop_var.get():
            eop_name = self.eop_signal_var.get().strip()

        db_selected = {}

        if use_valid and valid_name:
            if valid_name not in self.db_raw:
                messagebox.showerror("Error", f"Valid signal '{valid_name}' not found.")
                return

            valid_samples = self.db_raw[valid_name]["samples"]

            sop_samples, eop_samples = [], []
            if sop_name != "":
                sop_samples = self.db_raw[sop_name]["samples"]
            if eop_name != "":
                eop_samples = self.db_raw[eop_name]["samples"]

            L_valid = len(valid_samples)

            for name in selected_names:
                sig_info = self.db_raw[name]
                sig_samples = sig_info["samples"]
                L_sig = len(sig_samples)

                if L_sig != L_valid:
                    messagebox.showerror(
                        "Length mismatch",
                        f"Signal '{name}' has {L_sig} samples but valid signal "
                        f"'{valid_name}' has {L_valid}.\nThey must be the same length."
                    )
                    return

                # Filter samples where valid == 1, optional sop and eop
                multi_packets = (getattr(self, "packet_output_var", None) is not None) and (self.packet_output_var.get() == "multi")

                if multi_packets:
                    packets = filter_data_packets_list(sig_samples, valid_samples, sop_samples, eop_samples)
                    for k, pkt in enumerate(packets):
                        pkt_name = f"{name}__pkt{k}"
                        db_selected[pkt_name] = {
                            "idx": sig_info["idx"],
                            "samples": pkt,
                        }
                else:
                    filtered = filter_data_all_packets(sig_samples, valid_samples, sop_samples, eop_samples)
                    db_selected[name] = {
                        "idx": sig_info["idx"],
                        "samples": filtered,
                    }

        else:
            # No valid signal selected -> use all samples
            db_selected = {name: self.db_raw[name] for name in selected_names}

        data_type = self.data_type_var.get()

        try:
            if data_type == "1":  # Fixed
                sign_bits = int(self.sign_bits_var.get())
                int_bits = int(self.int_bits_var.get())
                frac_bits = int(self.frac_bits_var.get())
                data_prec = [sign_bits, int_bits, frac_bits]
                data_complex = "y" if self.complex_var.get() else "n"
            elif data_type == "2":  # Float
                exp_bits = int(self.exp_bits_var.get())
                man_bits = int(self.man_bits_var.get())
                data_prec = [exp_bits, man_bits]
                data_complex = ""  # not used
            else:  # As-is
                data_prec = []
                data_complex = ""

            data_par = int(self.data_par_var.get() or "1")
            data_par_mode = self.data_par_mode_var.get()

        except ValueError:
            messagebox.showerror("Error", "Precision fields must be integers.")
            return

        try:
            self.db_converted = convert_db(db_selected, data_type, data_prec, data_complex, data_par, data_par_mode)
        except Exception as e:
            messagebox.showerror("Conversion error", str(e))
            return

        if use_valid and valid_name:
            self.convert_status_var.set(
                f"Converted {len(self.db_converted)} signal(s) using valid='{valid_name}'."
            )
        else:
            self.convert_status_var.set(
                f"Converted {len(self.db_converted)} signal(s)."
            )

        # Update converted signals listbox
        self.converted_listbox.delete(0, tk.END)
        for sig in sorted(self.db_converted.keys()):
            self.converted_listbox.insert(tk.END, sig)

    def show_converted_signal(self, event):
        """Open a window showing the full data array of the double-clicked converted signal."""
        selection = self.converted_listbox.curselection()
        if not selection:
            return

        sig_name = self.converted_listbox.get(selection[0])
        info = self.db_converted.get(sig_name, {})
        samples = info.get("samples", [])

        win = tk.Toplevel(self)
        win.title(f"Data for {sig_name}")

        # Text widget + scrollbar
        text = tk.Text(win, wrap="none", width=100, height=30)
        text.pack(side="left", fill="both", expand=True)

        scroll_y = ttk.Scrollbar(win, orient="vertical", command=text.yview)
        scroll_y.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll_y.set)

        # Optional horizontal scrollbar
        scroll_x = ttk.Scrollbar(win, orient="horizontal", command=text.xview)
        scroll_x.pack(side="bottom", fill="x")
        text.configure(xscrollcommand=scroll_x.set)

        # Insert data
        for idx, sample in enumerate(samples):
            text.insert("end", f"{idx}: {sample}\n")

        text.configure(state="disabled")

    def combine_selected_signals(self):
        """Combine two input signals into one (Real/Imag or Even/Odd) and store as converted."""
        if not self.db_raw:
            messagebox.showerror("Error", "No signals loaded. Run Search first.")
            return

        selection = self.signals_listbox.curselection()
        if len(selection) != 2:
            messagebox.showerror(
                "Error",
                "Please select exactly TWO input signals (left list) to combine."
            )
            return

        # Get combine settings (same as convert_data)
        mode = self.combine_mode_var.get()
        # Get conversion settings (same as convert_data)
        data_type = self.data_type_var.get()
        # Get Data concantetion mode
        data_par_mode = self.data_par_mode_var.get()

        if data_par_mode == "parallel":
            messagebox.showerror(
                "Error",
                "Cannot combine two paralleled signals into one signal. Check the 'Serial' par mode."
            )
            return

        if self.complex_var.get() and mode == "ri":
            messagebox.showerror(
                "Error",
                "Cannot combine two complex signals into one complex signal. Uncheck [Complex data (I/Q)] to continue."
            )
            return

        if data_type == "2" and mode == "ri":
            messagebox.showerror(
                "Unsupported",
                "Real/Imag combine is only supported for scalar fixed-point data.\n"
                "Your float format is inherently complex (I/Q mantissas)."
            )
            return

        name1 = self.signals_full_names[selection[0]]
        name2 = self.signals_full_names[selection[1]]

        sig1_raw = self.db_raw[name1]["samples"]
        sig2_raw = self.db_raw[name2]["samples"]

        if len(sig1_raw) != len(sig2_raw):
            messagebox.showerror(
                "Error",
                f"Signals '{name1}' and '{name2}' have different lengths "
                f"({len(sig1_raw)} vs {len(sig2_raw)})."
            )
            return

        # Optional VALID filter (same logic as convert_data)
        use_valid = getattr(self, "use_valid_var", None)
        use_sop = getattr(self, "use_sop_var", None)
        use_eop = getattr(self, "use_eop_var", None)
        valid_name, sop_name, eop_name = "", "", ""
        if use_valid is not None and self.use_valid_var.get():
            valid_name = self.valid_signal_var.get().strip()
        if use_sop is not None and self.use_sop_var.get():
            sop_name = self.sop_signal_var.get().strip()
        if use_eop is not None and self.use_eop_var.get():
            eop_name = self.eop_signal_var.get().strip()

        if valid_name:
            if valid_name not in self.db_raw:
                messagebox.showerror("Error", f"Valid signal '{valid_name}' not found.")
                return

            valid_samples = self.db_raw[valid_name]["samples"]
            sop_samples, eop_samples = [], []
            if sop_name != "":
                sop_samples = self.db_raw[sop_name]["samples"]
            if eop_name != "":
                eop_samples = self.db_raw[eop_name]["samples"]

            if len(valid_samples) != len(sig1_raw):
                messagebox.showerror(
                    "Error",
                    f"Valid signal '{valid_name}' length ({len(valid_samples)}) "
                    f"does not match data length ({len(sig1_raw)})."
                )
                return

            if sop_samples is None and eop_samples is None:
                sig1 = [s for s, v in zip(sig1_raw, valid_samples) if sample_is_valid(v)]
                sig2 = [s for s, v in zip(sig2_raw, valid_samples) if sample_is_valid(v)]
            else:
                multi_packets = (getattr(self, "packet_output_var", None) is not None) and (self.packet_output_var.get() == "multi")

                if multi_packets:
                    pkts1 = filter_data_packets_list(sig1_raw, valid_samples, sop_samples, eop_samples)
                    pkts2 = filter_data_packets_list(sig2_raw, valid_samples, sop_samples, eop_samples)
                    packets_pair = (pkts1, pkts2)
                    # Keep non-empty placeholders to pass the existing empty-check below
                    sig1 = pkts1[0] if pkts1 else []
                    sig2 = pkts2[0] if pkts2 else []
                else:
                    packets_pair = None
                    sig1 = filter_data_all_packets(sig1_raw, valid_samples, sop_samples, eop_samples)
                    sig2 = filter_data_all_packets(sig2_raw, valid_samples, sop_samples, eop_samples)

        else:
            sig1 = sig1_raw
            sig2 = sig2_raw

        if not sig1 or not sig2:
            messagebox.showwarning(
                "Warning",
                "After applying valid filtering, no samples remain to combine."
            )
            return


        try:
            if data_type == "1":  # Fixed
                sign_bits = int(self.sign_bits_var.get())
                int_bits = int(self.int_bits_var.get())
                frac_bits = int(self.frac_bits_var.get())
                data_prec = [sign_bits, int_bits, frac_bits]
                data_complex = "y" if self.complex_var.get() else "n"
            elif data_type == "2":  # Float
                exp_bits = int(self.exp_bits_var.get())
                man_bits = int(self.man_bits_var.get())
                data_prec = [exp_bits, man_bits]
                data_complex = ""  # not used
            else:
                messagebox.showerror(
                    "Error",
                    "Combine is only supported for Fixed or Float types (not 'As-is')."
                )
                return

            data_par = int(self.data_par_var.get() or "1")

        except ValueError:
            messagebox.showerror("Error", "Precision fields must be integers.")
            return

        # If multi-packet mode is enabled, combine each packet separately
        if 'packets_pair' in locals() and packets_pair is not None:
            pkts1, pkts2 = packets_pair
            if not pkts1 or not pkts2:
                messagebox.showwarning("Warning", "After applying packet filtering, no samples remain to combine.")
                return

            n_pkts = min(len(pkts1), len(pkts2))
            if n_pkts == 0:
                messagebox.showwarning("Warning", "No complete packets found to combine.")
                return

            for k in range(n_pkts):
                temp_db = {
                    name1: {"idx": 0, "samples": pkts1[k]},
                    name2: {"idx": 0, "samples": pkts2[k]},
                }

                try:
                    conv_db = convert_db(temp_db, data_type, data_prec, data_complex, data_par, data_par_mode)
                except Exception as e:
                    messagebox.showerror("Conversion error", str(e))
                    return

                arr1 = conv_db[name1]["samples"]
                arr2 = conv_db[name2]["samples"]

                # handle swap roles
                local_name1, local_name2 = name1, name2
                if self.combine_swap_var.get():
                    arr1, arr2 = arr2, arr1
                    local_name1, local_name2 = name2, name1

                if len(arr1) != len(arr2):
                    messagebox.showerror("Error", "Converted packet signals have different lengths; cannot combine.")
                    return

                if mode == 'ri':
                    combined_samples = [complex(a, b) for a, b in zip(arr1, arr2)]
                    combined_base = f"{local_name1}_ReIm_{local_name2}"
                elif mode == 'eo':
                    combined_samples = []
                    for a, b in zip(arr1, arr2):
                        combined_samples.append(a)
                        combined_samples.append(b)
                    combined_base = f"{local_name1}_EvenOdd_{local_name2}"
                else:
                    messagebox.showerror("Error", "Unknown combine mode.")
                    return

                combined_name = f"{combined_base}__pkt{k}"

                self.db_converted[combined_name] = {"samples": combined_samples}

                existing = self.converted_listbox.get(0, tk.END)
                if combined_name not in existing:
                    self.converted_listbox.insert(tk.END, combined_name)

            mode_str = 'Real/Imag' if mode == 'ri' else 'Even/Odd'
            if valid_name:
                self.convert_status_var.set(
                    f"Combined {n_pkts} packet(s): '{name1}' + '{name2}' ({mode_str}, valid='{valid_name}')."
                )
            else:
                self.convert_status_var.set(
                    f"Combined {n_pkts} packet(s): '{name1}' + '{name2}' ({mode_str})."
                )
            return

        # Convert both signals using existing convert_db helper
        temp_db = {
            name1: {"idx": 0, "samples": sig1},
            name2: {"idx": 0, "samples": sig2},
        }

        try:
            conv_db = convert_db(temp_db, data_type, data_prec, data_complex, data_par, data_par_mode)
        except Exception as e:
            messagebox.showerror("Conversion error", str(e))
            return

        arr1 = conv_db[name1]["samples"]
        arr2 = conv_db[name2]["samples"]

        # handle swap roles
        if self.combine_swap_var.get():
            arr1, arr2 = arr2, arr1
            name1, name2 = name2, name1

        if len(arr1) != len(arr2):
            messagebox.showerror(
                "Error",
                "Converted signals have different lengths; cannot combine."
            )
            return

        if mode == "ri":
            # Interpret arr1 as real, arr2 as imag → complex
            combined_samples = [complex(a, b) for a, b in zip(arr1, arr2)]
            combined_name = f"{name1}_ReIm_{name2}"
        elif mode == "eo":
            # Interleave arr1 (even indices) and arr2 (odd indices)
            combined_samples = []
            for a, b in zip(arr1, arr2):
                combined_samples.append(a)  # even
                combined_samples.append(b)  # odd
            combined_name = f"{name1}_EvenOdd_{name2}"
        else:
            messagebox.showerror("Error", "Unknown combine mode.")
            return

        # Store in db_converted
        self.db_converted[combined_name] = {"samples": combined_samples}

        # Add to converted listbox (if not already there)
        existing = self.converted_listbox.get(0, tk.END)
        if combined_name not in existing:
            self.converted_listbox.insert(tk.END, combined_name)

        # Update status
        mode_str = "Real/Imag" if mode == "ri" else "Even/Odd"
        if valid_name:
            self.convert_status_var.set(
                f"Combined '{name1}' + '{name2}' -> '{combined_name}' "
                f"({mode_str}, valid='{valid_name}')."
            )
        else:
            self.convert_status_var.set(
                f"Combined '{name1}' + '{name2}' -> '{combined_name}' ({mode_str})."
            )

    def open_selector(self, selector: str):
        """Open a popup window to select a valid signal by double-click."""
        if not self.db_raw:
            messagebox.showerror("Error", "No signals loaded. Run Search first.")
            return

        # Source list of full names
        items = self.signals_full_names or sorted(self.db_raw.keys())

        # Decide what to DISPLAY in the popup: full or short
        # (change this to short_name if you prefer)
        display_names = []
        for full in items:
            # If you stored short_name in db_raw:
            # disp = self.db_raw[full].get("short_name", full)
            disp = full
            display_names.append(disp)

        # Compute width in characters based on longest display name
        max_len = max(len(s) for s in display_names) if display_names else 20
        listbox_width = max_len+2#min(max_len + 2, 250)  # clamp to something reasonable

        # Popup window
        win = tk.Toplevel(self)
        title = "Select " + selector + " signal"
        win.title(title)
        win.transient(self)  # keep on top of main window
        win.grab_set()  # modal

        ttk.Label(win, text=("Double-click a signal to use as " + selector + ":")).pack(
            side="top", anchor="w", padx=10, pady=(10, 5)
        )

        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        lb = tk.Listbox(
            frame,
            selectmode="browse",
            height=max(len(self.signals_full_names),20),
            width=listbox_width  # <- width in characters
        )
        lb.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=lb.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        lb.config(yscrollcommand=scroll.set)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        # Fill listbox
        for disp in display_names:
            lb.insert(tk.END, disp)

        def on_ok(event=None):
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            full_name = items[idx]  # always store FULL name
            if selector == "valid": # Valid
                self.valid_signal_var.set(full_name)
            elif selector == "sop": # SOP
                self.sop_signal_var.set(full_name)
            else: # EOP
                self.eop_signal_var.set(full_name)
            win.destroy()

        # Double-click / Enter to select
        lb.bind("<Double-Button-1>", on_ok)
        lb.bind("<Return>", on_ok)

        # Let Tk compute required size, then lock it as minimum so everything fits
        win.update_idletasks()
        win.minsize(win.winfo_reqwidth(), win.winfo_reqheight())

    # --- Section 3 actions ---

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.output_dir_var.set(directory)

    def write_files(self):
            """
            Write signals to TXT files.

            Export source preference:
              - If converted DB exists -> export from converted (selection in converted listbox, else all).
              - Else -> export from raw (selection in raw listbox, else all).

            Export format:
              - as-is : write values as they are (strings/numbers)
              - fixed : quantize numbers to integer fixed-point using [sign,int,frac]
              - float : write numeric values as floats (text)
            """
            export_fmt = (self.export_format_var.get() or "as-is").strip().lower()
            bte_enabled = bool(self.BTE_format_var.get())

            if bte_enabled and export_fmt != "fixed":
                messagebox.showerror("Export", "BTE format is only supported with Export format = 'fixed'.")
                return

            out_dir = Path(self.output_dir_var.get().strip() or ".")
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output directory:\n{e}")
                return

            bad_chars = r'\/:*?"<>|'
            trans_table = str.maketrans({c: '_' for c in bad_chars})

            # Choose export source DB + selection listbox
            if self.db_converted:
                src_db = self.db_converted
                lb = self.converted_listbox
                selection = lb.curselection()
                if selection:
                    selected_names = [lb.get(i) for i in selection]
                else:
                    selected_names = list(src_db.keys())
            else:
                if not self.db_raw:
                    messagebox.showerror("Export", "No signals loaded. Run Search first.")
                    return
                src_db = self.db_raw
                lb = self.signals_listbox
                selection = lb.curselection()
                if selection:
                    selected_names = [self.signals_full_names[i] for i in selection]
                else:
                    selected_names = list(src_db.keys())
            # Fixed export precision (only needed for Export format = fixed or BTE)
            sign_bit = int_bits = frac_bits = None
            if export_fmt == "fixed" or bte_enabled:
                try:
                    sign_bit  = int(self.wr_sign_bit_var.get())
                    int_bits  = int(self.wr_int_bits_var.get())
                    frac_bits = int(self.wr_frac_bits_var.get())
                except Exception:
                    messagebox.showerror(
                        "Export",
                        "Invalid fixed precision fields (sign/int/frac). Must be integers."
                    )
                    return

            base_name = self.base_filename_var.get().strip()

            for idx, sig_name in enumerate(selected_names):
                info = src_db.get(sig_name)
                if info is None:
                    continue

                sig_corrected = sig_name.translate(trans_table)
                if base_name:
                    sig_corrected = base_name.translate(trans_table)

                file_path = out_dir / f"{sig_corrected}_{idx}.txt"
                samples = info.get("samples", [])

                # Normalize to numpy array for vector ops where possible
                arr = np.asarray(samples)

                if export_fmt == "fixed":
                    # We expect numeric samples (real or complex). Best-effort conversion for string arrays.
                    if arr.dtype.kind in ("U", "S", "O"):
                        # Try to coerce to float (works for "123", "12.3"), else error
                        try:
                            arr = arr.astype(float)
                        except Exception:
                            messagebox.showerror(
                                "Export",
                                f"Signal '{sig_name}' cannot be exported as fixed: samples are not numeric."
                            )
                            return

                    if np.iscomplexobj(arr):
                        real_fixed = convert_to_fixed(np.real(arr), sign_bit, int_bits, frac_bits)
                        imag_fixed = convert_to_fixed(np.imag(arr), sign_bit, int_bits, frac_bits)
                    else:
                        real_fixed = convert_to_fixed(arr, sign_bit, int_bits, frac_bits)
                        imag_fixed = np.zeros(len(real_fixed), dtype=int)

                    # Defensive: ensure convert_to_fixed() output is real-valued integers.
                    # Some pipelines return complex dtype with 0j imaginary part.
                    real_fixed = np.asarray(real_fixed)
                    imag_fixed = np.asarray(imag_fixed)
                    if np.iscomplexobj(real_fixed):
                        real_fixed = np.real(real_fixed)
                    if np.iscomplexobj(imag_fixed):
                        imag_fixed = np.real(imag_fixed)
                    try:
                        real_fixed = np.round(real_fixed).astype(np.int64)
                        imag_fixed = np.round(imag_fixed).astype(np.int64)
                    except Exception:
                        # Fallback for object arrays
                        real_fixed = np.array([int(float(v)) for v in real_fixed], dtype=np.int64)
                        imag_fixed = np.array([int(float(v)) for v in imag_fixed], dtype=np.int64)

                    with open(file_path, mode="w", encoding="utf-8") as f:
                        if bte_enabled:
                            f.write("START 0\n")
                        for im, re_ in zip(imag_fixed, real_fixed):
                            if bte_enabled:
                                f.write(f"{int(im)} {int(re_)}\n")
                            else:
                                f.write(f"{int(im)} {int(re_)}\n")
                        if bte_enabled:
                            f.write("END 0")

                elif export_fmt == "float":
                    # Write numeric as float text; if not numeric, fall back to str()
                    if np.iscomplexobj(arr):
                        real_vals = np.real(arr)
                        imag_vals = np.imag(arr)
                        with open(file_path, mode="w", encoding="utf-8") as f:
                            for im, re_ in zip(imag_vals, real_vals):
                                try:
                                    f.write(f"{float(im)} {float(re_)}\n")
                                except Exception:
                                    f.write(f"{im} {re_}\n")
                    else:
                        with open(file_path, mode="w", encoding="utf-8") as f:
                            for v in arr:
                                try:
                                    f.write(f"0.0 {float(v)}\n")
                                except Exception:
                                    f.write(f"0 {v}\n")

                else:  # as-is
                    with open(file_path, mode="w", encoding="utf-8") as f:
                        if np.iscomplexobj(arr):
                            for v in arr:
                                f.write(f"{np.imag(v)} {np.real(v)}\n")
                        else:
                            for v in arr:
                                f.write(f"0 {v}\n")

            self.write_status_var.set(f"Wrote {len(selected_names)} signal(s) to {out_dir}")

    # --- Section 4 actions ---

    def _open_multi_plot_popup(self, series_dict, window_title):
        """
        Plot multiple series together.
        series_dict: {name: np.array([...])} (all same length)
        """
        # Convert to numpy and figure out if any is complex
        series = {name: np.array(data) for name, data in series_dict.items()}
        if not series:
            messagebox.showwarning("Warning", "No data to plot.")
            return

        first_len = len(next(iter(series.values())))
        if first_len == 0:
            messagebox.showwarning("Warning", "Selected signals have no samples.")
            return

        is_complex = any(np.iscomplexobj(arr) for arr in series.values())

        win = tk.Toplevel(self)
        win.title(window_title)
        win.geometry("1000x680")

        # Controls
        controls = ttk.Frame(win)
        controls.pack(side="top", fill="x", padx=5, pady=5)

        ttk.Label(controls, text="Plot type:").pack(side="left", padx=(0, 5))

        plot_options = [
            "Time - Real",
            "Time - Imag",
            "Time - Magnitude",
            "Time - Phase",
            "FFT - Magnitude",
            "FFT - dB",
        ]
        plot_type_var = tk.StringVar(
            value="Time - Real" if is_complex else "Time - Magnitude"
        )

        plot_menu = ttk.Combobox(
            controls,
            textvariable=plot_type_var,
            values=plot_options,
            state="readonly",
            width=20,
        )
        plot_menu.pack(side="left", padx=5)

        # Fs (for FFT)
        ttk.Label(controls, text="Fs (Hz):").pack(side="left", padx=(15, 5))
        fs_var = tk.StringVar(value="")
        fs_entry = ttk.Entry(controls, textvariable=fs_var, width=12)
        fs_entry.pack(side="left", padx=5)

        # X-limits
        ttk.Label(controls, text="Xmin:").pack(side="left", padx=(15, 5))
        xmin_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmin_var, width=10).pack(side="left", padx=2)

        ttk.Label(controls, text="Xmax:").pack(side="left", padx=(5, 5))
        xmax_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmax_var, width=10).pack(side="left", padx=2)

        ttk.Button(controls, text="Update", command=lambda: update_plot()).pack(
            side="left", padx=10
        )

        # Matplotlib figure
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side="top", fill="both", expand=True)

        toolbar_frame = ttk.Frame(win)
        toolbar_frame.pack(side="bottom", fill="x")
        NavigationToolbar2Tk(canvas, toolbar_frame)

        def get_fs():
            fs_str = fs_var.get().strip()
            if not fs_str:
                return None
            try:
                fs_val = float(fs_str)
                if fs_val <= 0:
                    raise ValueError
                return fs_val
            except ValueError:
                messagebox.showwarning(
                    "Invalid Fs",
                    "Sample rate (Fs) must be a positive number.\n"
                    "Using bin index instead.",
                )
                return None

        def get_xlim():
            xmin_str = xmin_var.get().strip()
            xmax_str = xmax_var.get().strip()
            xmin = xmax = None

            if xmin_str:
                try:
                    xmin = float(xmin_str)
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Xmin", "Xmin must be a number. Ignoring Xmin."
                    )
                    xmin = None

            if xmax_str:
                try:
                    xmax = float(xmax_str)
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Xmax", "Xmax must be a number. Ignoring Xmax."
                    )
                    xmax = None

            if (xmin is not None) and (xmax is not None) and (xmin >= xmax):
                messagebox.showwarning(
                    "Invalid range",
                    "Xmin must be less than Xmax. Ignoring both.",
                )
                return None, None

            return xmin, xmax

        def apply_xlim():
            xmin, xmax = get_xlim()
            if xmin is not None or xmax is not None:
                ax.set_xlim(
                    left=xmin if xmin is not None else None,
                    right=xmax if xmax is not None else None,
                )

        def update_plot():
            ax.clear()
            kind = plot_type_var.get()

            if "Time" in kind:
                x = np.arange(first_len)

                for name, y in series.items():
                    name = name.split("/")[-1]
                    if kind == "Time - Real":
                        if np.iscomplexobj(y):
                            ax.plot(x, y.real, label=f"{name} (Re)")
                        else:
                            ax.plot(x, y, label=name)

                    elif kind == "Time - Imag":
                        if np.iscomplexobj(y):
                            ax.plot(x, y.imag, label=f"{name} (Im)")
                        else:
                            # Real-only → imag = 0
                            ax.plot(x, np.zeros_like(y), label=f"{name} (Im=0)")

                    elif kind == "Time - Magnitude":
                        mag = np.abs(y)
                        ax.plot(x, mag, label=f"{name} |.|")

                    elif kind == "Time - Phase":
                        if np.iscomplexobj(y):
                            phase = np.angle(y)
                        else:
                            phase = np.zeros_like(y)
                        ax.plot(x, phase, label=f"{name} ∠")

                ax.set_xlabel("Sample index")
                ax.set_ylabel(kind.replace("Time - ", ""))
                ax.set_title(kind)
                ax.grid(True)
                ax.legend(loc="best")

            elif "FFT" in kind:
                # All have same length (checked earlier)
                N = first_len
                fs = get_fs()
                if fs is not None:
                    freq = np.fft.fftshift(np.fft.fftfreq(N, d=1.0 / fs))
                    x = freq
                    xlabel = "Frequency (Hz)"
                else:
                    x = np.arange(N)
                    xlabel = "Bin index"

                for name, y in series.items():
                    name = name.split("/")[-1]
                    Y = np.fft.fftshift(np.fft.fft(y))
                    mag = np.abs(Y)

                    if kind == "FFT - Magnitude":
                        ax.plot(x, mag, label=name)
                        ax.set_ylabel("Magnitude")
                    elif kind == "FFT - dB":
                        mag_db = 20 * np.log10(mag + 1e-12)
                        ax.plot(x, mag_db, label=name)
                        ax.set_ylabel("Magnitude [dB]")

                ax.set_xlabel(xlabel)
                ax.set_title(kind)
                ax.grid(True)
                ax.legend(loc="best")

            apply_xlim()
            fig.tight_layout()
            canvas.draw_idle()

        update_plot()

    def _open_plot_popup(self, data_array, name):
        """Generic plot popup for a given 1D array (real or complex)."""
        data = np.array(data_array)
        if data.size == 0:
            messagebox.showwarning("Warning", f"No samples to plot for '{name}'.")
            return

        win = tk.Toplevel(self)
        win.title(f"Plot: {name}")
        win.geometry("1000x680")

        # Top controls frame
        controls = ttk.Frame(win)
        controls.pack(side="top", fill="x", padx=5, pady=5)

        ttk.Label(controls, text="Plot type:").pack(side="left", padx=(0, 5))

        is_complex = np.iscomplexobj(data)
        plot_options = [
            "Time - Real",
            "Time - Imag",
            "Time - Magnitude",
            "Time - Phase",
            "FFT - Magnitude",
            "FFT - dB",
        ]
        plot_type_var = tk.StringVar(
            value="Time - Real" if is_complex else "Time - Magnitude"
        )

        plot_menu = ttk.Combobox(
            controls,
            textvariable=plot_type_var,
            values=plot_options,
            state="readonly",
            width=20,
        )
        plot_menu.pack(side="left", padx=5)

        # Sample rate (for FFT)
        ttk.Label(controls, text="Fs (Hz):").pack(side="left", padx=(15, 5))
        fs_var = tk.StringVar(value="")
        fs_entry = ttk.Entry(controls, textvariable=fs_var, width=12)
        fs_entry.pack(side="left", padx=5)

        # X-limits
        ttk.Label(controls, text="Xmin:").pack(side="left", padx=(15, 5))
        xmin_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmin_var, width=10).pack(side="left", padx=2)

        ttk.Label(controls, text="Xmax:").pack(side="left", padx=(5, 5))
        xmax_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmax_var, width=10).pack(side="left", padx=2)

        ttk.Button(controls, text="Update", command=lambda: update_plot()).pack(
            side="left", padx=10
        )

        # Matplotlib figure
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side="top", fill="both", expand=True)

        toolbar_frame = ttk.Frame(win)
        toolbar_frame.pack(side="bottom", fill="x")
        NavigationToolbar2Tk(canvas, toolbar_frame)

        def get_fs():
            fs_str = fs_var.get().strip()
            if not fs_str:
                return None
            try:
                fs_val = float(fs_str)
                if fs_val <= 0:
                    raise ValueError
                return fs_val
            except ValueError:
                messagebox.showwarning(
                    "Invalid Fs",
                    "Sample rate (Fs) must be a positive number.\n"
                    "Using bin index instead.",
                )
                return None

        def get_xlim():
            xmin_str = xmin_var.get().strip()
            xmax_str = xmax_var.get().strip()
            xmin = xmax = None

            if xmin_str:
                try:
                    xmin = float(xmin_str)
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Xmin", "Xmin must be a number. Ignoring Xmin."
                    )
                    xmin = None

            if xmax_str:
                try:
                    xmax = float(xmax_str)
                except ValueError:
                    messagebox.showwarning(
                        "Invalid Xmax", "Xmax must be a number. Ignoring Xmax."
                    )
                    xmax = None

            if (xmin is not None) and (xmax is not None) and (xmin >= xmax):
                messagebox.showwarning(
                    "Invalid range",
                    "Xmin must be less than Xmax. Ignoring both.",
                )
                return None, None

            return xmin, xmax

        def apply_xlim():
            xmin, xmax = get_xlim()
            if xmin is not None or xmax is not None:
                ax.set_xlim(
                    left=xmin if xmin is not None else None,
                    right=xmax if xmax is not None else None,
                )

        def update_plot():
            ax.clear()
            kind = plot_type_var.get()
            y = data

            if "Time" in kind:
                x = np.arange(len(y))

                if kind == "Time - Real":
                    if is_complex:
                        ax.plot(x, y.real, label="Real")
                        ax.set_ylabel("Real")
                    else:
                        ax.plot(x, y, label="Value")
                        ax.set_ylabel("Value")

                elif kind == "Time - Imag":
                    if is_complex:
                        ax.plot(x, y.imag, label="Imag")
                        ax.set_ylabel("Imag")
                    else:
                        messagebox.showwarning(
                            "Warning", "Data is not complex; imag part is zero."
                        )
                        ax.plot(x, np.zeros_like(y), label="Imag (0)")
                        ax.set_ylabel("Imag")

                elif kind == "Time - Magnitude":
                    mag = np.abs(y)
                    ax.plot(x, mag, label="Magnitude")
                    ax.set_ylabel("Magnitude")

                elif kind == "Time - Phase":
                    if is_complex:
                        phase = np.angle(y)
                        ax.plot(x, phase, label="Phase")
                        ax.set_ylabel("Phase [rad]")
                    else:
                        messagebox.showwarning(
                            "Warning", "Data is not complex; phase is undefined."
                        )
                        phase = np.zeros_like(y)
                        ax.plot(x, phase, label="Phase (0)")
                        ax.set_ylabel("Phase")

                ax.set_xlabel("Sample index")
                ax.set_title(f"{name} - {kind}")
                ax.grid(True)
                ax.legend(loc="best")

            elif "FFT" in kind:
                y_fft = np.fft.fftshift(np.fft.fft(y))
                mag = np.abs(y_fft)
                N = len(mag)

                fs = get_fs()
                if fs is not None:
                    freq = np.fft.fftshift(np.fft.fftfreq(N, d=1.0 / fs))
                    x = freq
                    xlabel = "Frequency (Hz)"
                else:
                    x = np.arange(N)
                    xlabel = "Bin index"

                if kind == "FFT - Magnitude":
                    ax.plot(x, mag, label="|FFT|")
                    ax.set_ylabel("Magnitude")
                elif kind == "FFT - dB":
                    mag_db = 20 * np.log10(mag + 1e-12)
                    ax.plot(x, mag_db, label="|FFT| dB")
                    ax.set_ylabel("Magnitude [dB]")

                ax.set_xlabel(xlabel)
                ax.set_title(f"{name} - {kind}")
                ax.grid(True)
                ax.legend(loc="best")

            apply_xlim()
            fig.tight_layout()
            canvas.draw_idle()

        update_plot()

    def plot_multi_signals(self):
        """Plot several converted signals together in one popup."""
        if not self.db_converted:
            messagebox.showerror("Error", "No converted data. Run Convert first.")
            return

        selection = self.converted_listbox.curselection()
        if len(selection) < 2:
            messagebox.showerror(
                "Error",
                "Please select at least two converted signals for MultiPlot.\n"
                "For a single signal, use 'Plot signal…'."
            )
            return

        # Build dict: name -> numpy array
        series = {}
        lengths = set()

        for idx in selection:
            name = self.converted_listbox.get(idx)
            info = self.db_converted.get(name, {})
            samples = info.get("samples", [])
            arr = np.array(samples)
            series[name] = arr
            lengths.add(arr.size)

        if len(lengths) > 1:
            messagebox.showerror(
                "Error",
                "All selected signals must have the same number of samples\n"
                f"(found lengths: {sorted(lengths)})."
            )
            return

        # Title for window
        names_list = [self.converted_listbox.get(i) for i in selection]
        title = "MultiPlot: " + ", ".join(names_list)

        self._open_multi_plot_popup(series, title)

    def plot_selected_signal_popup(self):
        """Wrapper: plot currently selected converted signal."""
        if not self.db_converted:
            messagebox.showerror("Error", "No converted data. Run Convert first.")
            return

        selection = self.converted_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a converted signal to plot.")
            return

        sig_name = self.converted_listbox.get(selection[0])
        info = self.db_converted.get(sig_name, {})
        samples = info.get("samples", [])

        self._open_plot_popup(samples, sig_name)

    def plot_from_file(self):
        """Read a 1/2-column file (real[, imag]) or a BTE-style file and plot it."""
        filename = filedialog.askopenfilename(
            title="Select data file",
            filetypes=(
                ("Text/CSV files", "*.txt *.csv"),
                ("All files", "*.*"),
            ),
        )
        if not filename:
            return

        is_bte = self.plot_from_file_bte_var.get()
        num_of_pkts = 1

        try:
            if is_bte:
                num_of_pkts = int(self.num_of_packets_var.get())
                data = [[] for _ in range(num_of_pkts)]
                curr_packet = 0
                pkts_found  = 0
                # ----- BTE format: START ... data ... END -----
                with open(filename, "r", encoding="utf-8") as f:
                    # strip empty lines
                    lines = [ln.strip() for ln in f.readlines() if ln.strip()]

                    if not lines:
                        raise ValueError("File is empty.")

                    for i in range(len(lines)):
                        toks = lines[i].split()
                        if toks[0] == "START":
                            pkts_found += 1
                            if pkts_found > num_of_pkts: # check to avoid overflow
                                break
                            re_vals = []
                            im_vals = []
                            i += 1
                            toks = lines[i].split()
                            while toks[0] != "END":
                                if len(toks) == 1:
                                    # Real-only
                                    re_vals.append(float(toks[0]))
                                else:
                                    # Assume first two columns are real, imag
                                    re_vals.append(float(toks[1]))
                                    im_vals.append(float(toks[0]))
                                i += 1
                                toks = lines[i].split()

                            if im_vals:
                                data[curr_packet] = np.array(re_vals, dtype=float) + 1j * np.array(im_vals, dtype=float)
                            else:
                                data[curr_packet] = np.array(re_vals, dtype=float)

                            curr_packet += 1

            else:
                # ----- Normal format: 1 or 2 numeric columns -----
                try:
                    arr = np.loadtxt(filename, delimiter=",")
                except Exception:
                    arr = np.loadtxt(filename)  # fallback: whitespace

                if arr.ndim == 1:
                    data = arr.astype(float)
                elif arr.ndim == 2 and arr.shape[1] >= 2:
                    data = arr[:, 1].astype(float) + 1j * arr[:, 0].astype(float)
                else:
                    raise ValueError("Expected 1 column (real) or 2 columns (real, imag).")

        except Exception as e:
            messagebox.showerror(
                "File error",
                f"Failed to read data from file:\n{filename}\n\n{e}",
            )
            return

        name = Path(filename).name

        if is_bte:
            # BTE: multiple packets possible
            if self.same_plot_window_var.get():
                # Plot ALL packets in a single window using MultiPlot logic
                series = {}
                for i in range(num_of_pkts):
                    # Skip empty packets, just in case
                    if i < len(data) and len(data[i]) > 0:
                        series[f"{name}_pkt_{i}"] = np.array(data[i])
                if series:
                    self._open_multi_plot_popup(series, f"{name} - all packets")
                else:
                    messagebox.showwarning("Warning", "No non-empty packets to plot.")
            else:
                # Original behavior: one popup per packet
                for i in range(num_of_pkts):
                    if i >= len(data):
                        break
                    curr_name = f"{name}_pkt_{i}"
                    self._open_plot_popup(data[i], curr_name)
        else:
            # Non-BTE: single array → single window
            self._open_plot_popup(data, name)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("DSP Lab + MAT Parser")

    tab = ILACSVParserTab(root)
    tab.pack(fill="both", expand=True)

    root.mainloop()