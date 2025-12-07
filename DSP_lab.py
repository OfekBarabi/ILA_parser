# dsp_lab_mat_tab.py

import tkinter as tk
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

        # Signal Gen Vars
        self.signal_name = tk.StringVar()
        self.length_var = tk.StringVar(value="1024")
        self.is_complex_var = tk.BooleanVar(value=True)
        self.freq_var = tk.StringVar(value="1e3")  # Hz
        self.fs_var = tk.StringVar(value="1e6")    # Hz
        self.dc_var = tk.StringVar(value="0.0")    # DC offset

        # Filter / resampling vars
        self.interp_var = tk.StringVar(value="1")  # L
        self.decim_var = tk.StringVar(value="1")   # M
        self.filter_conv_full_var = tk.BooleanVar(value=False)

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

        # -------- Section 3: Operations -------- #
        sec3 = ttk.LabelFrame(self, text="3. Operations")
        sec3.pack(fill="x", padx=5, pady=5)

        ttk.Label(sec3, text="Use selected signal from list below").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5, 5)
        )

        # FFT
        ttk.Button(sec3, text="FFT", command=self.op_fft).grid(
            row=1, column=0, sticky="w", padx=10, pady=5
        )
        ttk.Button(
            sec3,
            text="FFT + FFTShift",
            command=lambda: self.op_fft(use_shift=True),
        ).grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Frequency shift (NCO-like)
        ttk.Button(sec3, text="Freq shift", command=self.op_freq_shift).grid(
            row=1, column=2, sticky="w", padx=10, pady=5
        )

        # Filter / interp / decim
        ttk.Button(sec3, text="FIR", command=self.open_filter_window).grid(
            row=1, column=3, sticky="w", padx=10, pady=5
        )

        # -------- Shared info list at the bottom -------- #
        self.info_list = tk.Listbox(self, height=10)
        self.info_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Double-click a line to preview the signal
        self.info_list.bind("<Double-1>", self._on_signal_double_click)

        # -------- Section 4: Plot -------- #
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

        self.signals[name] = sig
        self._refresh_info_box()

    # ---------------- Operations ---------------- #

    def op_fft(self, use_shift: bool = False):
        name, sig = self._get_selected_signal()
        if sig is None:
            return

        spec = np.fft.fft(sig)
        if use_shift:
            spec = np.fft.fftshift(spec)

        suffix = "_fftshift" if use_shift else "_fft"
        new_name = name + suffix
        self.signals[new_name] = spec
        self._refresh_info_box()

    def op_freq_shift(self):
        name, sig = self._get_selected_signal()
        if sig is None:
            return

        try:
            f_shift = float(self.freq_var.get())
            fs = float(self.fs_var.get())
            if fs <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid parameters",
                "Freq and Fs must be valid numbers (Fs > 0).",
            )
            return

        n = np.arange(len(sig))
        mixer = np.exp(1j * 2 * np.pi * f_shift * n / fs)
        sig_shifted = sig * mixer

        new_name = name + "_fshift"
        self.signals[new_name] = sig_shifted
        self._refresh_info_box()

    def open_filter_window(self):
        name, sig = self._get_selected_signal()
        if sig is None:
            return

        win = tk.Toplevel(self)
        win.title(f"FIR – {name}")

        ttk.Label(win, text="Coefficients (comma or space separated):").pack(
            anchor="w", padx=10, pady=(10, 2)
        )
        coeff_text = tk.Text(win, width=60, height=5)
        coeff_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        params_frame = ttk.Frame(win)
        params_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Interp / decim
        ttk.Label(params_frame, text="Interp (L):").grid(
            row=0, column=0, sticky="e", padx=(0, 5)
        )
        ttk.Entry(
            params_frame, textvariable=self.interp_var, width=6
        ).grid(row=0, column=1, sticky="w", padx=(0, 15))

        ttk.Label(params_frame, text="Decim (M):").grid(
            row=0, column=2, sticky="e", padx=(0, 5)
        )
        ttk.Entry(
            params_frame, textvariable=self.decim_var, width=6
        ).grid(row=0, column=3, sticky="w")

        # Convolution mode selector (same/full)
        ttk.Checkbutton(
            params_frame,
            text="Full convolution (unchecked = same)",
            variable=self.filter_conv_full_var,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))

        def apply_filter():
            coeff_str = coeff_text.get("1.0", "end").strip()
            if not coeff_str:
                messagebox.showerror("Invalid coeffs", "Please enter filter coefficients.")
                return

            tokens = coeff_str.replace(",", " ").split()
            try:
                h = np.array([float(tok) for tok in tokens], dtype=float)
                if h.size == 0:
                    raise ValueError

                L = int(self.interp_var.get())
                M = int(self.decim_var.get())
                if L <= 0 or M <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Invalid parameters",
                    "Coeffs must be numeric; L and M must be positive integers.",
                )
                return

            x = sig

            # Interpolation (upsample by L)
            if L > 1:
                up = np.zeros(len(x) * L, dtype=x.dtype)
                up[::L] = x
                x = up

            mode = "full" if self.filter_conv_full_var.get() else "same"
            y = np.convolve(x, h, mode=mode)

            # Decimation (downsample by M)
            if M > 1:
                y = y[::M]

            new_name = name + "_filt"
            if L != 1:
                new_name += f"_L{L}"
            if M != 1:
                new_name += f"_M{M}"

            self.signals[new_name] = y
            self._refresh_info_box()
            win.destroy()

        ttk.Button(win, text="Apply", command=apply_filter).pack(pady=(0, 10))

    # ---------------- Plot ---------------- #

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

    def plot_multi_signals(self):
        """Plot several converted signals together in one popup."""
        if not self.signals:
            messagebox.showerror("Error", "No data. Create a signal first.")
            return

        selection = self.info_list.curselection()
        if len(selection) < 2:
            messagebox.showerror(
                "Error",
                "Please select at least two signals for MultiPlot.\n"
                "For a single signal, use 'Plot signal…'."
            )
            return

        # Build dict: name -> numpy array
        series = {}
        lengths = set()

        for idx in selection:
            name = self.info_list.get(idx)
            samples = self.signals.get(name, {})
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
        names_list = [self.info_list.get(i) for i in selection]
        title = "MultiPlot: " + ", ".join(names_list)

        self._open_multi_plot_popup(series, title)

    def plot_selected_signal_popup(self):
        """Wrapper: plot currently selected converted signal."""
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

# ---- Optional standalone demo ----
if __name__ == "__main__":
    root = tk.Tk()
    root.title("DSP Lab + MAT Parser")

    tab = DSPLabMatTab(root)
    tab.pack(fill="both", expand=True)

    root.mainloop()