from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from helper_funcs import (
    convert_to_fixed,
    sample_is_valid,
    convert_db,
    load_signals_from_csv,
    filter_data,
    get_short_name
)

# ------------------------
#  GUI Application (Tkinter)
# ------------------------

class ILAGuiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ILA CSV Parser")

        self.db_raw = {}
        self.db_converted = {}

        self._build_vars()
        self._build_ui()

        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        try:
            self.eval('tk::PlaceWindow . center')
        except tk.TclError:
            pass

    # --- Variables ---

    def _build_vars(self):
        # Section 1 Browse & Search
        self.csv_path_var = tk.StringVar()
        self.signal_filter_var = tk.StringVar()
        self.search_status_var = tk.StringVar(value="No file loaded.")

        # Section 2 Settings
        self.name_display_mode = tk.StringVar(value="full")
        self.signals_full_names = []

        self.data_type_var = tk.StringVar(value="1")

        self.sign_bits_var = tk.StringVar(value="1")
        self.int_bits_var = tk.StringVar(value="0")
        self.frac_bits_var = tk.StringVar(value="15")

        self.exp_bits_var = tk.StringVar(value="6")
        self.man_bits_var = tk.StringVar(value="13")

        self.data_par_var = tk.StringVar(value="1")
        self.data_par_mode_var = tk.StringVar(value="serial")

        self.complex_var = tk.BooleanVar(value=True)

        self.valid_signal_var = tk.StringVar()
        self.use_valid_var = tk.BooleanVar(value=False)

        self.sop_signal_var = tk.StringVar()
        self.use_sop_var = tk.BooleanVar(value=False)

        self.eop_signal_var = tk.StringVar()
        self.use_eop_var = tk.BooleanVar(value=False)

        self.convert_status_var = tk.StringVar(value="")

        self.combine_mode_var = tk.StringVar(value="ri")
        self.combine_swap_var = tk.BooleanVar(value=False)

        # Section 3 Export
        self.output_dir_var = tk.StringVar(value=".")
        self.base_filename_var = tk.StringVar(value="")
        self.write_status_var = tk.StringVar(value="")
        self.BTE_format_var = tk.BooleanVar(value=False)
        self.wr_sign_bit_var = tk.StringVar(value="1")
        self.wr_int_bits_var = tk.StringVar(value="0")
        self.wr_frac_bits_var = tk.StringVar(value="15")

        # Section 4 Plot
        self.plot_from_file_bte_var = tk.BooleanVar(value=False)

    # --- UI Layout ---

    def _build_ui(self):
        # Section 1
        sec1 = ttk.LabelFrame(self, text="1. Select file and search signals")
        sec1.pack(fill="x", padx=10, pady=5)

        ttk.Label(sec1, text="CSV file:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        entry_csv = ttk.Entry(sec1, textvariable=self.csv_path_var)
        entry_csv.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        ttk.Button(sec1, text="Browse...", command=self.browse_csv).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(sec1, text="Signal name contains(Upper/Lower case sensitive):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(sec1, textvariable=self.signal_filter_var).grid(row=1, column=1, sticky="we", padx=5, pady=5)
        ttk.Button(sec1, text="Search", command=self.search_signals).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(sec1, textvariable=self.search_status_var).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=5, pady=5
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

        combine_row = ttk.Frame(settings)
        combine_row.grid(row=7, column=0, sticky="w", pady=2)

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
        btn_row.grid(row=8, column=0, sticky="w", pady=(6, 2))

        ttk.Button(btn_row, text="Convert selected", command=self.convert_data).pack(
            side="left"
        )
        ttk.Button(btn_row, text="Combine selected", command=self.combine_selected_signals).pack(
            side="left", padx=(6, 0)
        )

        ttk.Label(settings, textvariable=self.convert_status_var).grid(
            row=9, column=0, sticky="w", pady=(2, 0)
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

    # ------------- Core GUI methods (browse, search, convert, combine, plot, write) -------------

    # --- Section 1 actions ---

    def browse_csv(self):
        filename = filedialog.askopenfilename(
            title="Select ILA CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_path_var.set(filename)

    def search_signals(self):
        csv_path = Path(self.csv_path_var.get().strip())
        if not csv_path.is_file():
            messagebox.showerror("Error", "Please select a valid CSV file.")
            return

        name_filter = self.signal_filter_var.get().strip()

        try:
            db = load_signals_from_csv(csv_path, name_filter)
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
                disp = get_short_name(full)
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
                filtered = filter_data(sig_samples, valid_samples, sop_samples, eop_samples)

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
                sig1 = filter_data(sig1_raw, valid_samples, sop_samples, eop_samples)
                sig2 = filter_data(sig2_raw, valid_samples, sop_samples, eop_samples)

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
        listbox_width = min(max_len + 2, 100)  # clamp to something reasonable

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
            height=12,
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
        if not self.db_converted:
            messagebox.showerror("Error", "No converted data. Run Convert first.")
            return

        out_dir = Path(self.output_dir_var.get().strip() or ".")
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create directory: {e}")
            return

        file_name  = self.base_filename_var.get()

        BTE_format_check = self.BTE_format_var.get()
        bad_chars = '/\\:[],.'
        trans_table = str.maketrans({c: '_' for c in bad_chars})

        # use selection if any, otherwise write all
        selection = self.converted_listbox.curselection()
        if selection:
            # Only the selected converted signals
            selected_names = [self.converted_listbox.get(i) for i in selection]
        else:
            # Nothing selected → write all converted signals
            selected_names = list(self.db_converted.keys())

        for idx, sig_name in enumerate(selected_names):
            info = self.db_converted.get(sig_name)
            sig_corrected = sig_name.translate(trans_table)
            if file_name:
                sig_corrected = file_name.translate(trans_table)
            file_path = out_dir / f"{sig_corrected}_{str(idx)}.txt"
            samples = info["samples"]
            if BTE_format_check:
                sign_bit  = int(self.wr_sign_bit_var.get())
                int_bits  = int(self.wr_int_bits_var.get())
                frac_bits = int(self.wr_frac_bits_var.get())
                samples   = convert_to_fixed(info["samples"], sign_bit, int_bits, frac_bits)
            with open(file_path, mode="w", encoding="utf-8") as f:
                if BTE_format_check:
                    f.write("START 0\n")
                for sample in samples:
                    is_complex = np.iscomplexobj(sample)
                    real = np.real(sample)
                    if is_complex:
                        imag = np.imag(sample)
                    else:
                        imag = ""

                    if BTE_format_check:
                        f.write(f"{int(imag)} {int(real)}\n")
                    else:
                        f.write(str(imag) + " " + str(real) + "\n")

                if BTE_format_check:
                    f.write("END 0")

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

        try:
            if is_bte:
                # ----- BTE format: START ... data ... END -----
                with open(filename, "r", encoding="utf-8") as f:
                    # strip empty lines
                    lines = [ln.strip() for ln in f.readlines() if ln.strip()]

                    if not lines:
                        raise ValueError("File is empty.")

                    for i in range(len(lines)):
                        toks = lines[i].split()
                        if toks[0] == "START":
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

                            # Stopping after one packet, TODO need to add multiple packets handle
                            break

                    if im_vals:
                        data = np.array(re_vals, dtype=float) + 1j * np.array(im_vals, dtype=float)
                    else:
                        data = np.array(re_vals, dtype=float)

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
        self._open_plot_popup(data, name)

# --- Main ---
def main():
    app = ILAGuiApp()
    app.mainloop()

if __name__ == "__main__":
    main()
