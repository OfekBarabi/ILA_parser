# dsp_lab_tab.py
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np

class DSPLabTab(ttk.Frame):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._build_vars()
        self._build_ui()

    def _build_vars(self):

        # Signal Gen Vars
        self.signals        = {}                 # name -> np.ndarray
        self.signal_name    = tk.StringVar()
        self.length_var     = tk.StringVar(value="1024")
        self.is_complex_var = tk.BooleanVar(value=True)
        self.freq_var = tk.StringVar(value="1e3")    # Hz
        self.fs_var   = tk.StringVar(value="1e6")    # Hz
        self.dc_var   = tk.StringVar(value="0.0")    # DC offset

        # FFT Vars
        # FIR Vars
        # Filter / resampling vars
        self.interp_var = tk.StringVar(value="1")   # L
        self.decim_var  = tk.StringVar(value="1")   # M
        self.filter_conv_full_var = tk.BooleanVar(value=False)  # False = "same", True = "full"

        # NCO Vars

    def _build_ui(self):

        # Section 1 - Signal Gen
        sec1 = ttk.LabelFrame(self, text="1. Signal Gen")
        sec1.pack(fill="x", padx=5, pady=5)

        # Name
        ttk.Label(sec1, text="Name:").grid(
            row=0, column=0, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec1, textvariable=self.signal_name, width=10).grid(
            row=0, column=1, sticky="w", padx=(0, 10), pady=5
        )

        # Length
        ttk.Label(sec1, text="Length:").grid(
            row=0, column=2, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec1, textvariable=self.length_var, width=10).grid(
            row=0, column=3, sticky="w", padx=(0, 10), pady=5
        )

        # Frequency
        ttk.Label(sec1, text="Freq (Hz):").grid(
            row=1, column=0, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec1, textvariable=self.freq_var, width=10).grid(
            row=1, column=1, sticky="w", padx=(0, 10), pady=5
        )

        # Sample rate
        ttk.Label(sec1, text="Fs (Hz):").grid(
            row=1, column=2, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec1, textvariable=self.fs_var, width=10).grid(
            row=1, column=3, sticky="w", padx=(0, 10), pady=5
        )

        # DC offset
        ttk.Label(sec1, text="DC:").grid(
            row=1, column=4, sticky="e", padx=(10, 2), pady=5
        )
        ttk.Entry(sec1, textvariable=self.dc_var, width=10).grid(
            row=1, column=5, sticky="w", padx=(0, 10), pady=5
        )

        # Complex
        ttk.Checkbutton(sec1, text="Complex", variable=self.is_complex_var).grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=5
        )

        # Generate button (random)
        ttk.Button(
            sec1,
            text="Random",
            command=lambda: self.generate_signal("rand")
        ).grid(row=2, column=1, columnspan=5, sticky="w", padx=1, pady=(5, 10))

        # Sine
        ttk.Button(
            sec1,
            text="Sine",
            command=lambda: self.generate_signal("sine")
        ).grid(row=2, column=2, sticky="w", padx=1, pady=(5, 10))

        # Cosine
        ttk.Button(
            sec1,
            text="Cosine",
            command=lambda: self.generate_signal("cosine")
        ).grid(row=2, column=3, sticky="w", padx=1, pady=(5, 10))

        # Section 2 - Operations
        sec2 = ttk.LabelFrame(self, text="2. Operations")
        sec2.pack(fill="x", padx=5, pady=5)

        ttk.Label(sec2, text="Use selected signal from list below").grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5, 5)
        )

        # FFT
        ttk.Button(sec2, text="FFT", command=self.op_fft).grid(
            row=1, column=0, sticky="w", padx=10, pady=5
        )
        ttk.Button(sec2, text="FFT + FFTShift", command=lambda: self.op_fft(use_shift=True)).grid(
            row=1, column=1, sticky="w", padx=10, pady=5
        )

        # Frequency shift (NCO-like)
        ttk.Button(sec2, text="Freq shift", command=self.op_freq_shift).grid(
            row=1, column=2, sticky="w", padx=10, pady=5
        )

        # Filter / interp / decim
        ttk.Button(sec2, text="FIR", command=self.open_filter_window).grid(
            row=1, column=3, sticky="w", padx=10, pady=5
        )

        # --- Info box: list of signal names ---
        self.info_list = tk.Listbox(self, height=8)
        self.info_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Double-click a name to show the signal
        self.info_list.bind("<Double-1>", self._on_signal_double_click)

    # ------------- Core GUI methods ------------- #

    def generate_signal(self, sig_type: str):
        """Generate a random real/complex signal of length N and store it by name."""
        # Parse N
        try:
            n = int(self.length_var.get())
            if n <= 0:
                raise ValueError

            # Get / assign name
            name = self.signal_name.get().strip()
            if not name:
                name = f"sig_{len(self.signals) + 1}"

            # Get Settings
            if sig_type != "rand":
                f = float(self.freq_var.get())
                fs = float(self.fs_var.get())
                dc = float(self.dc_var.get())
                # Time index
                t = np.arange(n) / fs

        except ValueError:
            messagebox.showerror("Invalid N", "N must be a positive integer.")
            return

        # Generate signal
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

        self.signals[name] = sig
        self._update_info_box()

    def _update_info_box(self):
        """Show only the names of the generated signals in the info box."""
        self.info_list.delete(0, tk.END)
        for name in self.signals.keys():
            self.info_list.insert(tk.END, name)

    def _get_selected_signal(self):
        """Return (name, signal) for the currently selected entry in info_list."""
        selection = self.info_list.curselection()
        if not selection:
            messagebox.showwarning("No signal selected", "Please select a signal from the list.")
            return None, None

        idx = selection[0]
        name = self.info_list.get(idx)
        sig = self.signals.get(name)
        if sig is None:
            messagebox.showerror("Error", f"Signal '{name}' not found.")
            return None, None

        return name, sig

    def _on_signal_double_click(self, event):
        """On double-click: open a window showing the selected signal values."""
        name, sig = self._get_selected_signal()
        if sig is None:
            return

        win = tk.Toplevel(self)
        win.title(f"Signal: {name}")

        text = tk.Text(win, width=80, height=20)
        text.pack(fill="both", expand=True)

        text.insert("1.0", f"Signal '{name}' (length {sig.shape[0]}):\n\n")
        # Indexed values
        for i, v in enumerate(sig):
            text.insert("end", f"[{i}] {v}\n")

        text.configure(state="disabled")

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
        self._update_info_box()

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
        self._update_info_box()

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
        ttk.Label(params_frame, text="Interp (L):").grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Entry(params_frame, textvariable=self.interp_var, width=6).grid(
            row=0, column=1, sticky="w", padx=(0, 15)
        )

        ttk.Label(params_frame, text="Decim (M):").grid(row=0, column=2, sticky="e", padx=(0, 5))
        ttk.Entry(params_frame, textvariable=self.decim_var, width=6).grid(
            row=0, column=3, sticky="w"
        )

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
            self._update_info_box()
            win.destroy()

        ttk.Button(win, text="Apply", command=apply_filter).pack(
            pady=(0, 10)
        )
