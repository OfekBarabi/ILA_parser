# dsp_lab_mat_tab.py

import tkinter as tk
import json
from tkinter import ttk, filedialog, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import numpy as np
from helper_funcs import *  # expects collect_signals_v5, etc.


class DSPLabMatTab(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._build_vars()
        self._build_ui()

    # ---------------- Variables ---------------- #

    def _build_vars(self):

        # Shared signals DB: name -> np.ndarray
        self.signals = {}

        # DSP chain state
        self.dsp_chain = []  # list of dicts: {"op": str, "params": {k: v}}

        # Operation registry (extend freely)
        self.OP_REGISTRY = {
            "Gain": {
                "params": [("gain", float, 1.0)],
                "func": lambda x, gain: x * gain,
            },
            "DC Offset": {
                "params": [("offset", float, 0.0)],
                "func": lambda x, offset: x + offset,
            },
            "Normalize (peak=1)": {
                "params": [],
                "func": lambda x: (x / (np.max(np.abs(x)) + 1e-12)),
            },
            "Abs": {
                "params": [],
                "func": lambda x: np.abs(x),
            },
            "Moving Average": {
                "params": [("window", int, 8)],
                "func": self._op_moving_average,
            },
            "FIR Filter (L/M)": {
                "params": [
                    ("dec_factor", int, 1),
                    ("interp_factor", int, 1),

                    # coeff source selection
                    ("coeff_source", str, "manual"),  # manual/file/signal
                    ("h_manual", str, "1.0"),
                    ("h_file", str, ""),
                    ("h_signal", str, ""),

                    ("fir_type", str, "same"),  # same/full
                ],
                "func": self._op_fir_filter,
            },
            "FFT": {
                "params": [],
                "func": lambda x: np.fft.fftshift(np.fft.fft(x)),
            },
            "IFFT": {
                "params": [],
                "func": lambda x: np.fft.ifft(x),
            },
            "NCO": {
                "params": [("fs", float, 1e6), ("freq", float, 0.0)],
                "func": lambda x, fs, freq: x * np.exp(1j * 2 * np.pi * freq * np.arange(len(x)) / fs),
            },
        }

        # Signal Gen Vars
        self.signal_name = tk.StringVar()
        self.length_var = tk.StringVar(value="1024")
        self.is_complex_var = tk.BooleanVar(value=True)
        self.freq_var = tk.StringVar(value="1e3")  # Hz
        self.fs_var = tk.StringVar(value="1e6")    # Hz
        self.dc_var = tk.StringVar(value="0.0")    # DC offset

        # Export Vars
        self.export_header_var = tk.BooleanVar(value=True)
        self.export_index_var = tk.BooleanVar(value=True)
        self.export_split_complex_var = tk.BooleanVar(value=True)
        self.export_delim = "\t"

        # Quantization (signal gen)
        self.use_quan_var = tk.BooleanVar(value=False)
        self.q_s_var = tk.StringVar(value="1")
        self.q_m_var = tk.StringVar(value="0")
        self.q_n_var = tk.StringVar(value="15")

        # Per-step quantization (DSP chain step)
        self.step_quan_var = tk.BooleanVar(value=False)
        self.step_q_s_var = tk.StringVar(value="1")
        self.step_q_m_var = tk.StringVar(value="0")
        self.step_q_n_var = tk.StringVar(value="15")

    # ---------------- UI Layout ---------------- #

    def _build_ui(self):
        # -------- Section 1: MAT File Browser -------- #
        sec1 = ttk.LabelFrame(self, text="1. MAT File Browser")
        sec1.pack(fill="x", padx=5, pady=5)

        ttk.Label(sec1, text="Load MAT (v5/v7.2) file and add arrays as signals.").grid(
            row=0, column=0, sticky="w", padx=10, pady=(5, 5)
        )

        ttk.Button(sec1, text="Browse…", command=self._on_browse).grid(
            row=1, column=0, sticky="w", padx=10, pady=(0, 10)
        )

        # -------- Section 2: Signal Generation -------- #
        sec2 = ttk.LabelFrame(self, text="2. Signal Generation")
        sec2.pack(fill="x", padx=5, pady=5)

        # Name
        ttk.Label(sec2, text="Name:").grid(
            row=0, column=0, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec2, textvariable=self.signal_name, width=10).grid(
            row=0, column=1, sticky="w", padx=(0, 10), pady=5
        )

        # Length
        ttk.Label(sec2, text="Length:").grid(
            row=0, column=2, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec2, textvariable=self.length_var, width=10).grid(
            row=0, column=3, sticky="w", padx=(0, 10), pady=5
        )

        # Frequency
        ttk.Label(sec2, text="Freq (Hz):").grid(
            row=1, column=0, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec2, textvariable=self.freq_var, width=10).grid(
            row=1, column=1, sticky="w", padx=(0, 10), pady=5
        )

        # Sample rate
        ttk.Label(sec2, text="Fs (Hz):").grid(
            row=1, column=2, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec2, textvariable=self.fs_var, width=10).grid(
            row=1, column=3, sticky="w", padx=(0, 10), pady=5
        )

        # DC offset
        ttk.Label(sec2, text="DC:").grid(
            row=1, column=4, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec2, textvariable=self.dc_var, width=10).grid(
            row=1, column=5, sticky="w", padx=(0, 10), pady=5
        )

        # Complex checkbox
        ttk.Checkbutton(sec2, text="Complex", variable=self.is_complex_var).grid(
            row=2, column=0, sticky="w", padx=(10, 10), pady=5
        )

        # Generate buttons
        ttk.Button(
            sec2,
            text="Random",
            command=lambda: self.generate_signal("rand"),
        ).grid(row=2, column=1, sticky="w", padx=1, pady=(5, 10))

        ttk.Button(
            sec2,
            text="Sine",
            command=lambda: self.generate_signal("sine"),
        ).grid(row=2, column=2, sticky="w", padx=1, pady=(5, 10))

        ttk.Button(
            sec2,
            text="Cosine",
            command=lambda: self.generate_signal("cosine"),
        ).grid(row=2, column=3, sticky="w", padx=1, pady=(5, 10))

        # Quantization controls (Signal Generation)
        ttk.Checkbutton(sec2, text="Quantize (s.m.n):", variable=self.use_quan_var).grid(
            row=3, column=0, sticky="w", padx=(10, 2), pady=(0, 10)
        )
        ttk.Label(sec2, text="s:").grid(row=3, column=1, sticky="e", padx=(0, 2))
        ttk.Entry(sec2, textvariable=self.q_s_var, width=5).grid(row=3, column=2, sticky="w", padx=(0, 10))

        ttk.Label(sec2, text="m:").grid(row=3, column=3, sticky="e", padx=(0, 2))
        ttk.Entry(sec2, textvariable=self.q_m_var, width=5).grid(row=3, column=4, sticky="w", padx=(0, 10))

        ttk.Label(sec2, text="n:").grid(row=3, column=5, sticky="e", padx=(0, 2))
        ttk.Entry(sec2, textvariable=self.q_n_var, width=5).grid(row=3, column=6, sticky="w", padx=(0, 10))

        # -------- Section 3: Operations -------- #
        sec3 = ttk.LabelFrame(self, text="3. Operations (DSP Chain)")
        sec3.pack(fill="x", padx=10, pady=5)

        top = ttk.Frame(sec3)
        top.pack(fill="x", padx=5, pady=5)

        # Quantization controls (Operations / after each op)
        qrow = ttk.Frame(sec3)
        qrow.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Checkbutton(qrow, text="Quantize after each op (s.m.n):", variable=self.use_quan_var).pack(side="left")
        ttk.Label(qrow, text="s:").pack(side="left", padx=(10, 2))
        ttk.Entry(qrow, textvariable=self.q_s_var, width=5).pack(side="left")
        ttk.Label(qrow, text="m:").pack(side="left", padx=(10, 2))
        ttk.Entry(qrow, textvariable=self.q_m_var, width=5).pack(side="left")
        ttk.Label(qrow, text="n:").pack(side="left", padx=(10, 2))
        ttk.Entry(qrow, textvariable=self.q_n_var, width=5).pack(side="left")

        ttk.Label(top, text="Operation:").pack(side="left")
        self.chain_op_cb = ttk.Combobox(
            top,
            state="readonly",
            values=list(self.OP_REGISTRY.keys()),
            width=22,
        )
        self.chain_op_cb.pack(side="left", padx=(5, 10))
        self.chain_op_cb.bind("<<ComboboxSelected>>", self._chain_on_select_op)

        ttk.Label(top, text="Output name:").pack(side="left")
        self.chain_out_name = tk.StringVar(value="(auto)")
        ttk.Entry(top, textvariable=self.chain_out_name, width=22).pack(side="left", padx=5)

        ttk.Button(top, text="Add step", command=self._chain_add_step).pack(side="left", padx=5)
        ttk.Button(top, text="Apply chain", command=self._chain_apply).pack(side="left", padx=5)

        # Per-step quantization controls (stored into each added step)
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Checkbutton(top, text="Step quan", variable=self.step_quan_var).pack(side="left")
        ttk.Label(top, text="s:").pack(side="left", padx=(6, 2))
        ttk.Entry(top, textvariable=self.step_q_s_var, width=4).pack(side="left")
        ttk.Label(top, text="m:").pack(side="left", padx=(6, 2))
        ttk.Entry(top, textvariable=self.step_q_m_var, width=4).pack(side="left")
        ttk.Label(top, text="n:").pack(side="left", padx=(6, 2))
        ttk.Entry(top, textvariable=self.step_q_n_var, width=4).pack(side="left")

        mid = ttk.Frame(sec3)
        mid.pack(fill="x", padx=5, pady=(0, 5))

        # Params area (dynamic)
        self.chain_params_frame = ttk.LabelFrame(mid, text="Parameters")
        self.chain_params_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._chain_param_vars = {}  # filled dynamically

        # Chain steps table
        right = ttk.Frame(mid)
        right.pack(side="left", fill="both")

        self.chain_tree = ttk.Treeview(
            right,
            columns=("op", "params"),
            show="headings",
            height=6,
        )
        self.chain_tree.heading("op", text="Step")
        self.chain_tree.heading("params", text="Params")
        self.chain_tree.column("op", width=140, anchor="w")
        self.chain_tree.column("params", width=260, anchor="w")
        self.chain_tree.pack(fill="both", expand=True)

        btns = ttk.Frame(sec3)
        btns.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Button(btns, text="Up", command=lambda: self._chain_move(-1)).pack(side="left")
        ttk.Button(btns, text="Down", command=lambda: self._chain_move(+1)).pack(side="left", padx=5)
        ttk.Button(btns, text="Remove", command=self._chain_remove).pack(side="left")
        ttk.Button(btns, text="Clear", command=self._chain_clear).pack(side="left", padx=5)

        ttk.Separator(btns, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Button(btns, text="Save preset…", command=self._chain_save_preset).pack(side="left")
        ttk.Button(btns, text="Load preset…", command=self._chain_load_preset).pack(side="left", padx=5)

        # Default selection
        if self.chain_op_cb["values"]:
            self.chain_op_cb.current(0)
            self._chain_on_select_op()

        # --- Signals / Info list (in Section 3) ---
        sig_box = ttk.LabelFrame(sec3, text="Signals")
        sig_box.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        sig_inner = ttk.Frame(sig_box)
        sig_inner.pack(fill="both", expand=True, padx=5, pady=5)

        self.info_list = tk.Listbox(sig_inner, height=7, selectmode="extended")
        self.info_list.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(sig_inner, orient="vertical", command=self.info_list.yview)
        sb.pack(side="left", fill="y")
        self.info_list.configure(yscrollcommand=sb.set)

        # Double click → preview window
        self.info_list.bind("<Double-1>", self._on_signal_double_click)


        # -------- Section 4: Export -------- #
        sec4 = ttk.LabelFrame(self, text="4. Export")
        sec4.pack(fill="x", padx=10, pady=5)

        ttk.Label(sec4, text="Export selected signals to a TXT file (columns).").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=5, pady=(5, 2)
        )

        ttk.Button(sec4, text="Export selected…", command=self.export_selected_signals_txt).grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )

        ttk.Checkbutton(sec4, text="Header", variable=self.export_header_var).grid(
            row=1, column=1, sticky="w", padx=5, pady=5
        )
        ttk.Checkbutton(sec4, text="Index", variable=self.export_index_var).grid(
            row=1, column=2, sticky="w", padx=5, pady=5
        )
        ttk.Checkbutton(sec4, text="Split complex (Re/Im)", variable=self.export_split_complex_var).grid(
            row=1, column=3, sticky="w", padx=5, pady=5
        )

        # -------- Section 5: Plot -------- #
        sec5 = ttk.LabelFrame(self, text="5. Plot data")
        sec5.pack(fill="x", padx=10, pady=5)

        ttk.Label(sec5, text="Plot converted signal or data from file").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5
        )

        ttk.Button(sec5, text="Plot signal…", command=self.plot_selected_signal_popup).grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )

        ttk.Button(sec5, text="MultiPlot…", command=self.plot_multi_signals).grid(
            row=1, column=1, sticky="w", padx=5, pady=5
        )

    # ---------------- MAT Browser logic ---------------- #

    def _on_browse(self):
        path = filedialog.askopenfilename(
            title="Open MAT file (v5/v7.2)",
            filetypes=[("MATLAB files", "*.mat"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            mat_signals = collect_signals_v5(path)
        except NotImplementedError:
            messagebox.showerror(
                "Error",
                "This looks like a v7.3 MAT file.\n"
                "Current parser only supports non-v7.3."
            )
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open MAT file:\n{e}")
            return

        # Merge MAT signals into shared DB (avoid name collisions)
        for name, sig in mat_signals.items():
            base = name
            new_name = base
            i = 1
            while new_name in self.signals:
                new_name = f"{base}_mat{i}"
                i += 1
            self.signals[new_name] = sig

        self._refresh_info_box()

    # ---------------- Shared list / selection ---------------- #

    def _refresh_info_box(self):
        """Show name + basic metadata for all signals."""
        self.info_list.delete(0, tk.END)
        for name in sorted(self.signals.keys(), key=str.lower):
            sig = np.array(self.signals[name])
            display = (
                f"{name}  |  shape={sig.shape}, "
                f"dtype={sig.dtype}, size={sig.size}"
            )
            self.info_list.insert(tk.END, display)

        self._update_chain_signal_choices()

    def _get_selected_signal(self):
        """Return (name, signal) for the currently selected entry in info_list."""
        selection = self.info_list.curselection()
        if not selection:
            messagebox.showwarning(
                "No signal selected", "Please select a signal from the list."
            )
            return None, None

        idx = selection[0]
        line = self.info_list.get(idx)
        name = line.split("|", 1)[0].strip()
        sig = self.signals.get(name)
        if sig is None:
            messagebox.showerror("Error", f"Signal '{name}' not found.")
            return None, None

        return name, sig

    def _on_signal_double_click(self, event):
        """On double-click: open a window showing signal info + preview."""
        name, sig = self._get_selected_signal()
        if sig is None:
            return
        self._show_signal_preview(name, sig)

    def _show_signal_preview(self, name, data):
        win = tk.Toplevel(self)
        win.title(f"Signal: {name}")

        arr = np.array(data)

        info = (
            f"Name:  {name}\n"
            f"Shape: {arr.shape}\n"
            f"Dtype: {arr.dtype}\n"
            f"Size:  {arr.size}"
        )
        ttk.Label(win, text=info, justify="left").pack(
            anchor="w", padx=10, pady=5
        )

        text = tk.Text(win, width=80, height=20)
        text.pack(fill="both", expand=True, padx=10, pady=5)

        max_elements = 200
        if arr.size > max_elements:
            preview = arr.ravel()[:max_elements]
            text.insert(
                "1.0",
                f"Showing first {max_elements} elements out of {arr.size}:\n\n{preview}"
            )
        else:
            text.insert("1.0", repr(arr))

        text.configure(state="disabled")

    # ---------------- Signal generation ---------------- #

    def generate_signal(self, sig_type: str):
        """Generate a random/analytic real/complex signal of length N and store it by name."""
        try:
            n = int(self.length_var.get())
            if n <= 0:
                raise ValueError

            # Name
            name = self.signal_name.get().strip()
            if not name:
                name = f"sig_{len(self.signals) + 1}"

            # For sine / cosine we need f, fs, dc
            if sig_type != "rand":
                f = float(self.freq_var.get())
                fs = float(self.fs_var.get())
                dc = float(self.dc_var.get())
                t = np.arange(n) / fs

        except ValueError:
            messagebox.showerror("Invalid parameters", "Check N, Freq, Fs and DC.")
            return

        # Generate
        if sig_type == "rand":
            if self.is_complex_var.get():
                real = np.random.randn(n)
                imag = np.random.randn(n)
                sig = real + 1j * imag
            else:
                sig = np.random.randn(n)
        elif sig_type == "sine":
            sig = dc + np.sin(2 * np.pi * f * t)
        elif sig_type == "cosine":
            sig = dc + np.cos(2 * np.pi * f * t)
        else:
            messagebox.showerror("Error", f"Unknown signal type '{sig_type}'.")
            return

        if self.use_quan_var.get():
            x_prec = self._get_x_prec()
            sig = ba_quan(sig, x_prec)
            sig = sig.quantize()

        self.signals[name] = sig
        self._refresh_info_box()

    def _get_x_prec(self):
        try:
            s = int(self.q_s_var.get())
            m = int(self.q_m_var.get())
            n = int(self.q_n_var.get())
        except Exception:
            raise ValueError("Invalid quantization precision. s/m/n must be integers.")

        x_prec = {"s": s, "m": m, "n": n}
        return x_prec

    # ---------------- Operations ---------------- #

    def _chain_on_select_op(self, event=None):
        op = self.chain_op_cb.get()
        self._chain_build_param_widgets(op)

    def _chain_build_param_widgets(self, op_name: str):
        # Clear old widgets
        for w in self.chain_params_frame.winfo_children():
            w.destroy()
        self._chain_param_vars.clear()

        # ---- Special UI for FIR Filter op ----
        if op_name == "FIR Filter (L/M)":
            grid = ttk.Frame(self.chain_params_frame)
            grid.pack(fill="x", padx=6, pady=6)

            def add_row(r, label, var, width=16, widget=None):
                ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", padx=(0, 8), pady=2)
                if widget is None:
                    widget = ttk.Entry(grid, textvariable=var, width=width)
                widget.grid(row=r, column=1, sticky="w", pady=2)
                return widget

            # Vars
            dec_var = tk.StringVar(value="1")
            int_var = tk.StringVar(value="1")
            fir_type_var = tk.StringVar(value="same")

            coeff_src_var = tk.StringVar(value="manual")
            h_manual_var = tk.StringVar(value="1.0")
            h_file_var = tk.StringVar(value="")
            h_signal_var = tk.StringVar(value="")

            # Store in param map so _chain_read_params works
            self._chain_param_vars["dec_factor"] = (dec_var, int)
            self._chain_param_vars["interp_factor"] = (int_var, int)
            self._chain_param_vars["fir_type"] = (fir_type_var, str)

            self._chain_param_vars["coeff_source"] = (coeff_src_var, str)
            self._chain_param_vars["h_manual"] = (h_manual_var, str)
            self._chain_param_vars["h_file"] = (h_file_var, str)
            self._chain_param_vars["h_signal"] = (h_signal_var, str)

            # Basic params
            add_row(0, "dec_factor (M):", dec_var)
            add_row(1, "interp_factor (L):", int_var)

            fir_cb = ttk.Combobox(
                grid,
                textvariable=fir_type_var,
                state="readonly",
                values=("same", "full"),
                width=14,
            )
            add_row(2, "fir_type:", fir_type_var, widget=fir_cb)

            # Coeff source selector
            ttk.Label(grid, text="h source:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(8, 2))
            src_frame = ttk.Frame(grid)
            src_frame.grid(row=3, column=1, sticky="w", pady=(8, 2))

            for txt, val in (("Manual", "manual"), ("File", "file"), ("Signal", "signal")):
                ttk.Radiobutton(
                    src_frame,
                    text=txt,
                    value=val,
                    variable=coeff_src_var,
                    command=self._chain_filter_coeff_source_changed,
                ).pack(side="left", padx=(0, 10))

            # Manual taps
            self._chain_h_manual_frame = ttk.Frame(grid)
            self._chain_h_manual_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=2)
            ttk.Label(self._chain_h_manual_frame, text="h (manual):").pack(side="left", padx=(0, 8))
            ttk.Entry(self._chain_h_manual_frame, textvariable=h_manual_var, width=44).pack(side="left")

            # File taps
            self._chain_h_file_frame = ttk.Frame(grid)
            self._chain_h_file_frame.grid(row=5, column=0, columnspan=2, sticky="w", pady=2)
            ttk.Label(self._chain_h_file_frame, text="h (file):").pack(side="left", padx=(0, 8))
            ttk.Entry(self._chain_h_file_frame, textvariable=h_file_var, width=36).pack(side="left")
            ttk.Button(
                self._chain_h_file_frame,
                text="Browse…",
                command=lambda: self._chain_browse_h_file(h_file_var),
            ).pack(side="left", padx=6)

            # Signal taps
            self._chain_h_signal_frame = ttk.Frame(grid)
            self._chain_h_signal_frame.grid(row=6, column=0, columnspan=2, sticky="w", pady=2)
            ttk.Label(self._chain_h_signal_frame, text="h (signal):").pack(side="left", padx=(0, 8))

            self._chain_h_signal_var = h_signal_var
            self._chain_h_signal_cb = ttk.Combobox(
                self._chain_h_signal_frame,
                textvariable=h_signal_var,
                state="readonly",
                values=sorted(self.signals.keys(), key=str.lower),
                width=30,
            )
            self._chain_h_signal_cb.pack(side="left")

            # show/hide frames based on selection
            self._chain_filter_coeff_source_changed()
            return
        # ---- End special UI ----

        # Generic UI for all other ops
        opdef = self.OP_REGISTRY.get(op_name, {})
        params = opdef.get("params", [])

        if not params:
            ttk.Label(self.chain_params_frame, text="(No parameters)").pack(anchor="w", padx=6, pady=6)
            return

        grid = ttk.Frame(self.chain_params_frame)
        grid.pack(fill="x", padx=6, pady=6)

        for r, (pname, ptype, pdefault) in enumerate(params):
            ttk.Label(grid, text=f"{pname}:").grid(row=r, column=0, sticky="w", padx=(0, 8), pady=2)
            var = tk.StringVar(value=str(pdefault))
            ent = ttk.Entry(grid, textvariable=var, width=16)
            ent.grid(row=r, column=1, sticky="w", pady=2)
            self._chain_param_vars[pname] = (var, ptype)

    def _chain_read_params(self, op_name: str) -> dict:
        opdef = self.OP_REGISTRY[op_name]
        out = {}
        for pname, ptype, pdefault in opdef.get("params", []):
            var, _ptype = self._chain_param_vars.get(pname, (None, ptype))
            s = var.get().strip() if var is not None else str(pdefault)
            try:
                # int("2.0") fails, so allow float->int if user types 2.0
                if ptype is int:
                    out[pname] = int(float(s))
                else:
                    out[pname] = ptype(s)
            except Exception:
                raise ValueError(f"Bad value for '{pname}': '{s}'")
        return out

    def _chain_add_step(self):
        op = self.chain_op_cb.get()
        if not op:
            return
        try:
            params = self._chain_read_params(op)
            step_prec = None
            if self.step_quan_var.get():
                step_prec = self._get_step_x_prec()

        except ValueError as e:
            messagebox.showerror("DSP Chain", str(e))
            return

        self.dsp_chain.append({"op": op, "params": params, "x_prec": step_prec})
        self._chain_refresh_view()

    def _chain_refresh_view(self):
        self.chain_tree.delete(*self.chain_tree.get_children())
        for i, step in enumerate(self.dsp_chain, start=1):
            op = step["op"]
            params = step.get("params", {})
            ptxt = ", ".join(f"{k}={v}" for k, v in params.items()) if params else "-"
            xp = step.get("x_prec", None)
            if xp is not None:
                ptxt = f"{ptxt} | quan={xp['s']}.{xp['m']}.{xp['n']}"

            self.chain_tree.insert("", "end", iid=str(i - 1), values=(f"{i}. {op}", ptxt))

    def _chain_selected_index(self):
        sel = self.chain_tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def _chain_move(self, delta: int):
        idx = self._chain_selected_index()
        if idx is None:
            return

        new_idx = idx + int(delta)
        if new_idx < 0 or new_idx >= len(self.dsp_chain):
            return

        self.dsp_chain[new_idx], self.dsp_chain[idx] = self.dsp_chain[idx], self.dsp_chain[new_idx]
        self._chain_refresh_view()
        self.chain_tree.selection_set(str(new_idx))

    def _chain_remove(self):
        idx = self._chain_selected_index()
        if idx is None:
            return
        self.dsp_chain.pop(idx)
        self._chain_refresh_view()

    def _chain_clear(self):
        self.dsp_chain.clear()
        self._chain_refresh_view()

    def _chain_apply(self):
        if not self.dsp_chain:
            messagebox.showinfo("DSP Chain", "Chain is empty.")
            return

        name, x = self._get_selected_signal()
        if x is None:
            return

        y = np.asarray(x)

        try:
            x_prec = None
            if self.use_quan_var.get():
                x_prec = self._get_x_prec()

            for step in self.dsp_chain:
                op = step["op"]
                params = step.get("params", {})
                fn = self.OP_REGISTRY[op]["func"]
                y = fn(y, **params) if params else fn(y)
                step_prec = step.get("x_prec", None)
                if step_prec is not None:
                    y = ba_quan(y, x_prec)  # pseudo: x = quan(x, x_prec)
                    y = y.quantize()
                y = np.asarray(y)
        except Exception as e:
            messagebox.showerror("DSP Chain", f"Failed at op '{op}':\n{e}")
            return

        out_name = self.chain_out_name.get().strip()
        if (not out_name) or (out_name == "(auto)"):
            out_name = f"{name} | chain({len(self.dsp_chain)})"

        self.signals[out_name] = y
        self._refresh_info_box()
        messagebox.showinfo("DSP Chain", f"Created new signal:\n{out_name}")

    def _chain_save_preset(self):
        if not self.dsp_chain:
            messagebox.showinfo("DSP Chain", "Chain is empty.")
            return
        path = filedialog.asksaveasfilename(
            title="Save DSP Chain Preset",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.dsp_chain, f, indent=2)
        except Exception as e:
            messagebox.showerror("DSP Chain", str(e))

    def _chain_load_preset(self):
        path = filedialog.askopenfilename(
            title="Load DSP Chain Preset",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                chain = json.load(f)
            if not isinstance(chain, list):
                raise ValueError("Invalid preset format.")
            for step in chain:
                if step.get("op") not in self.OP_REGISTRY:
                    raise ValueError(f"Unknown op in preset: {step.get('op')}")
            self.dsp_chain = chain
            self._chain_refresh_view()
        except Exception as e:
            messagebox.showerror("DSP Chain", str(e))

    def _op_moving_average(self, x, window: int):
        window = max(1, int(window))
        if window == 1:
            return x
        k = np.ones(window, dtype=float) / float(window)
        return np.convolve(x, k, mode="same")

    def _chain_filter_coeff_source_changed(self):
        src = ""
        if "coeff_source" in self._chain_param_vars:
            src = self._chain_param_vars["coeff_source"][0].get().strip().lower()

        # Hide all
        if hasattr(self, "_chain_h_manual_frame"):
            self._chain_h_manual_frame.grid_remove()
        if hasattr(self, "_chain_h_file_frame"):
            self._chain_h_file_frame.grid_remove()
        if hasattr(self, "_chain_h_signal_frame"):
            self._chain_h_signal_frame.grid_remove()

        # Show selected
        if src == "file":
            self._chain_h_file_frame.grid()
        elif src == "signal":
            self._chain_h_signal_frame.grid()
            self._update_chain_signal_choices()
        else:
            self._chain_h_manual_frame.grid()

    def _chain_browse_h_file(self, h_file_var: tk.StringVar):
        path = filedialog.askopenfilename(
            title="Load FIR coefficients",
            filetypes=[("Text", "*.txt *.dat *.csv"), ("All files", "*.*")]
        )
        if path:
            h_file_var.set(path)

    def _update_chain_signal_choices(self):
        if hasattr(self, "_chain_h_signal_cb") and self._chain_h_signal_cb.winfo_exists():
            vals = sorted(self.signals.keys(), key=str.lower)
            self._chain_h_signal_cb["values"] = vals
            cur = getattr(self, "_chain_h_signal_var", None)
            if cur is not None and cur.get() and cur.get() not in self.signals:
                cur.set("")

    def _parse_fir_coeffs_from_string(self, s: str) -> np.ndarray:
        s = (s or "").strip()
        if not s:
            return np.array([], dtype=float)

        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        s = s.replace(";", " ").replace("\n", " ")

        import re
        parts = [p for p in re.split(r"[,\s]+", s) if p]
        try:
            return np.array([complex(p) for p in parts])
        except Exception:
            return np.array([float(p) for p in parts], dtype=float)

    def _load_fir_coeffs_from_file(self, path: str) -> np.ndarray:
        path = (path or "").strip()
        if not path:
            return np.array([], dtype=float)
        return np.loadtxt(path).reshape(-1)

    def _op_fir_filter(self, x, dec_factor: int, interp_factor: int,
                       coeff_source: str, h_manual: str, h_file: str, h_signal: str,
                       fir_type: str):
        x = np.asarray(x)
        M = max(1, int(dec_factor))
        L = max(1, int(interp_factor))

        src = (coeff_source or "manual").strip().lower()
        if src == "file":
            h = self._load_fir_coeffs_from_file(h_file)
        elif src == "signal":
            key = (h_signal or "").strip()
            if key not in self.signals:
                raise ValueError(f"h_signal '{key}' not found in signals.")
            h = np.asarray(self.signals[key]).reshape(-1)
        else:
            h = self._parse_fir_coeffs_from_string(h_manual)

        if h.size == 0:
            raise ValueError("Filter coefficients are empty/invalid.")

        mode = (fir_type or "same").strip().lower()
        if mode not in ("same", "full"):
            raise ValueError("fir_type must be 'same' or 'full'.")

        if L > 1:
            up = np.zeros(x.size * L, dtype=x.dtype)
            up[::L] = x
            x_u = up
        else:
            x_u = x

        y = np.convolve(x_u, h, mode=mode)

        if M > 1:
            y = y[::M]

        return y

    def _get_step_x_prec(self):
        try:
            s = int(self.step_q_s_var.get())
            m = int(self.step_q_m_var.get())
            n = int(self.step_q_n_var.get())
        except Exception:
            raise ValueError("Invalid STEP precision. s/m/n must be integers.")
        return {"s": s, "m": m, "n": n}

    # ---------------- Plot ---------------- #

    def _open_plot_popup(self, data_array, name):
        data = np.array(data_array)
        if data.size == 0:
            messagebox.showwarning("Warning", f"No samples to plot for '{name}'.")
            return

        win = tk.Toplevel(self)
        win.title(f"Plot: {name}")
        win.geometry("1000x680")

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
        plot_type_var = tk.StringVar(value="Time - Real" if is_complex else "Time - Magnitude")

        plot_menu = ttk.Combobox(
            controls,
            textvariable=plot_type_var,
            values=plot_options,
            state="readonly",
            width=20,
        )
        plot_menu.pack(side="left", padx=5)

        ttk.Label(controls, text="Fs (Hz):").pack(side="left", padx=(15, 5))
        fs_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=fs_var, width=12).pack(side="left", padx=5)

        ttk.Label(controls, text="Xmin:").pack(side="left", padx=(15, 5))
        xmin_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmin_var, width=10).pack(side="left", padx=2)

        ttk.Label(controls, text="Xmax:").pack(side="left", padx=(5, 5))
        xmax_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmax_var, width=10).pack(side="left", padx=2)

        ttk.Button(controls, text="Update", command=lambda: update_plot()).pack(side="left", padx=10)

        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

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
                    "Sample rate (Fs) must be a positive number.\nUsing bin index instead.",
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
                    messagebox.showwarning("Invalid Xmin", "Xmin must be a number. Ignoring Xmin.")
                    xmin = None

            if xmax_str:
                try:
                    xmax = float(xmax_str)
                except ValueError:
                    messagebox.showwarning("Invalid Xmax", "Xmax must be a number. Ignoring Xmax.")
                    xmax = None

            if (xmin is not None) and (xmax is not None) and (xmin >= xmax):
                messagebox.showwarning("Invalid range", "Xmin must be less than Xmax. Ignoring both.")
                return None, None

            return xmin, xmax

        def apply_xlim():
            xmin, xmax = get_xlim()
            if xmin is not None or xmax is not None:
                ax.set_xlim(left=xmin if xmin is not None else None, right=xmax if xmax is not None else None)

        def update_plot():
            ax.clear()
            kind = plot_type_var.get()
            y = data

            if "Time" in kind:
                x = np.arange(len(y))

                if kind == "Time - Real":
                    ax.plot(x, y.real if is_complex else y)
                    ax.set_ylabel("Real" if is_complex else "Value")

                elif kind == "Time - Imag":
                    ax.plot(x, y.imag if is_complex else np.zeros_like(y))
                    ax.set_ylabel("Imag")

                elif kind == "Time - Magnitude":
                    ax.plot(x, np.abs(y))
                    ax.set_ylabel("Magnitude")

                elif kind == "Time - Phase":
                    ax.plot(x, np.angle(y) if is_complex else np.zeros_like(y))
                    ax.set_ylabel("Phase [rad]")

                ax.set_xlabel("Sample index")
                ax.set_title(f"{name} - {kind}")
                ax.grid(True)

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
                    ax.plot(x, mag)
                    ax.set_ylabel("Magnitude")
                elif kind == "FFT - dB":
                    mag_db = 20 * np.log10(mag + 1e-12)
                    ax.plot(x, mag_db)
                    ax.set_ylabel("Magnitude [dB]")

                ax.set_xlabel(xlabel)
                ax.set_title(f"{name} - {kind}")
                ax.grid(True)

            apply_xlim()
            fig.tight_layout()
            canvas.draw_idle()

        update_plot()

    def _open_multi_plot_popup(self, series_dict, window_title):
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
        plot_type_var = tk.StringVar(value="Time - Real" if is_complex else "Time - Magnitude")

        plot_menu = ttk.Combobox(
            controls,
            textvariable=plot_type_var,
            values=plot_options,
            state="readonly",
            width=20,
        )
        plot_menu.pack(side="left", padx=5)

        ttk.Label(controls, text="Fs (Hz):").pack(side="left", padx=(15, 5))
        fs_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=fs_var, width=12).pack(side="left", padx=5)

        ttk.Label(controls, text="Xmin:").pack(side="left", padx=(15, 5))
        xmin_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmin_var, width=10).pack(side="left", padx=2)

        ttk.Label(controls, text="Xmax:").pack(side="left", padx=(5, 5))
        xmax_var = tk.StringVar(value="")
        ttk.Entry(controls, textvariable=xmax_var, width=10).pack(side="left", padx=2)

        ttk.Button(controls, text="Update", command=lambda: update_plot()).pack(side="left", padx=10)

        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

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
                    "Sample rate (Fs) must be a positive number.\nUsing bin index instead.",
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
                    messagebox.showwarning("Invalid Xmin", "Xmin must be a number. Ignoring Xmin.")
                    xmin = None

            if xmax_str:
                try:
                    xmax = float(xmax_str)
                except ValueError:
                    messagebox.showwarning("Invalid Xmax", "Xmax must be a number. Ignoring Xmax.")
                    xmax = None

            if (xmin is not None) and (xmax is not None) and (xmin >= xmax):
                messagebox.showwarning("Invalid range", "Xmin must be less than Xmax. Ignoring both.")
                return None, None

            return xmin, xmax

        def apply_xlim():
            xmin, xmax = get_xlim()
            if xmin is not None or xmax is not None:
                ax.set_xlim(left=xmin if xmin is not None else None, right=xmax if xmax is not None else None)

        def update_plot():
            ax.clear()
            kind = plot_type_var.get()

            if "Time" in kind:
                x = np.arange(first_len)

                for nm, y in series.items():
                    lbl = nm.split("/")[-1]
                    if kind == "Time - Real":
                        ax.plot(x, y.real if np.iscomplexobj(y) else y, label=lbl)
                    elif kind == "Time - Imag":
                        ax.plot(x, y.imag if np.iscomplexobj(y) else np.zeros_like(y), label=lbl)
                    elif kind == "Time - Magnitude":
                        ax.plot(x, np.abs(y), label=lbl)
                    elif kind == "Time - Phase":
                        ax.plot(x, np.angle(y) if np.iscomplexobj(y) else np.zeros_like(y), label=lbl)

                ax.set_xlabel("Sample index")
                ax.set_ylabel(kind.replace("Time - ", ""))
                ax.set_title(kind)
                ax.grid(True)
                ax.legend(loc="best")

            elif "FFT" in kind:
                N = first_len
                fs = get_fs()
                if fs is not None:
                    freq = np.fft.fftshift(np.fft.fftfreq(N, d=1.0 / fs))
                    x = freq
                    xlabel = "Frequency (Hz)"
                else:
                    x = np.arange(N)
                    xlabel = "Bin index"

                for nm, y in series.items():
                    lbl = nm.split("/")[-1]
                    Y = np.fft.fftshift(np.fft.fft(y))
                    mag = np.abs(Y)

                    if kind == "FFT - Magnitude":
                        ax.plot(x, mag, label=lbl)
                        ax.set_ylabel("Magnitude")
                    elif kind == "FFT - dB":
                        mag_db = 20 * np.log10(mag + 1e-12)
                        ax.plot(x, mag_db, label=lbl)
                        ax.set_ylabel("Magnitude [dB]")

                ax.set_xlabel(xlabel)
                ax.set_title(kind)
                ax.grid(True)
                ax.legend(loc="best")

            apply_xlim()
            fig.tight_layout()
            canvas.draw_idle()

        update_plot()

    def plot_multi_signals(self):
        if not self.signals:
            messagebox.showerror("Error", "No data. Create a signal first.")
            return

        selection = self.info_list.curselection()
        if len(selection) < 2:
            messagebox.showerror(
                "Error",
                "Please select at least two signals for MultiPlot.\nFor a single signal, use 'Plot signal…'."
            )
            return

        series = {}
        lengths = set()

        for idx in selection:
            line = self.info_list.get(idx)
            base = line.split("|", 1)[0].strip()
            arr = np.array(self.signals.get(base, []))
            series[base] = arr
            lengths.add(arr.size)

        if len(lengths) > 1:
            messagebox.showerror(
                "Error",
                "All selected signals must have the same number of samples\n"
                f"(found lengths: {sorted(lengths)})."
            )
            return

        names_list = [self.info_list.get(i).split("|", 1)[0].strip() for i in selection]
        title = "MultiPlot: " + ", ".join(names_list)

        self._open_multi_plot_popup(series, title)

    def plot_selected_signal_popup(self):
        if not self.signals:
            messagebox.showerror("Error", "No converted data. Run Convert first.")
            return

        selection = self.info_list.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a converted signal to plot.")
            return

        sig_name = self.info_list.get(selection[0])
        sig_name = sig_name.split("|", 1)[0].strip()
        samples = self.signals.get(sig_name, {})

        self._open_plot_popup(samples, sig_name)

    # ---------------- Export ---------------- #

    def export_selected_signals_txt(self):
        """Export selected signals to a TXT file as columns (tab-delimited)."""
        if not self.signals:
            messagebox.showerror("Export", "No signals to export.")
            return

        selection = self.info_list.curselection()
        if not selection:
            messagebox.showerror("Export", "Please select one or more signals from the list.")
            return

        # Resolve selected base names (strip metadata after '|')
        names = []
        seen = set()
        for idx in selection:
            line = self.info_list.get(idx)
            base = line.split("|", 1)[0].strip()
            if base and base in self.signals and base not in seen:
                names.append(base)
                seen.add(base)

        if not names:
            messagebox.showerror("Export", "No valid signals selected.")
            return

        path = filedialog.asksaveasfilename(
            title="Export selected signals",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        split_cplx = bool(self.export_split_complex_var.get())
        include_header = bool(self.export_header_var.get())
        include_index = bool(self.export_index_var.get())
        delim = self.export_delim

        cols = []
        headers = []
        any_object = False

        for name in names:
            arr = np.asarray(self.signals[name]).reshape(-1)

            if np.iscomplexobj(arr):
                if split_cplx:
                    cols.append(arr.real.astype(float))
                    cols.append(arr.imag.astype(float))
                    headers.extend([f"{name}_re", f"{name}_im"])
                else:
                    # Export complex as strings in a single column
                    cols.append(np.array([str(v) for v in arr], dtype=object))
                    headers.append(name)
                    any_object = True
            else:
                # numeric real
                try:
                    cols.append(arr.astype(float))
                except Exception:
                    cols.append(np.array([str(v) for v in arr], dtype=object))
                    any_object = True
                headers.append(name)

        if not cols:
            messagebox.showerror("Export", "Nothing to export.")
            return

        max_len = max(c.size for c in cols)

        # Optional index column
        if include_index:
            idx_col = np.arange(max_len, dtype=float)
            cols.insert(0, idx_col)
            headers.insert(0, "n")

        # Pad columns to same length
        padded = []
        for c in cols:
            if c.size == max_len:
                padded.append(c)
                continue
            if c.dtype == object:
                pad_val = ""
            else:
                pad_val = np.nan
            out = np.empty(max_len, dtype=c.dtype)
            out[:] = pad_val
            out[:c.size] = c
            padded.append(out)

        # Write
        try:
            if any_object or any(p.dtype == object for p in padded):
                with open(path, "w", encoding="utf-8") as f:
                    if include_header and headers:
                        f.write(delim.join(headers) + "\n")
                    for i in range(max_len):
                        row = []
                        for c in padded:
                            v = c[i]
                            if isinstance(v, float) and np.isnan(v):
                                row.append("")
                            else:
                                row.append(str(v))
                        f.write(delim.join(row) + "\n")
            else:
                data = np.column_stack(padded).astype(float)
                header = delim.join(headers) if (include_header and headers) else ""
                np.savetxt(
                    path,
                    data,
                    delimiter=delim,
                    header=header,
                    comments="" if header else "# ",
                    fmt="%.12g",
                )
        except Exception as e:
            messagebox.showerror("Export", f"Failed to export:\n{e}")
            return

        messagebox.showinfo("Export", f"Exported {len(names)} signal(s) to:\n{path}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("DSP Lab + MAT Parser")

    tab = DSPLabMatTab(root)
    tab.pack(fill="both", expand=True)

    root.mainloop()
