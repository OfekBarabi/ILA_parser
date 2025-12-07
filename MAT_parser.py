# mat_file_parser_tab.py
import tkinter as tk
from tkinter import ttk,  filedialog, messagebox
from helper_funcs import *


class MatFileParserTab(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._build_vars()
        self._build_ui()

    # --- Variables ---

    def _build_vars(self):
        self.signals = {}  # {name: np.ndarray}

    # --- UI Layout ---

    def _build_ui(self):
        # --- Top bar: Browse button ---
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        browse_btn = ttk.Button(top, text="Browse", command=self._on_browse)
        browse_btn.pack(side="left")

        # --- Listbox + scrollbar for flattened signal names ---
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.info_list = tk.Listbox(list_frame, height=20)
        self.info_list.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self.info_list.yview)
        scrollbar.pack(side="right", fill="y")

        self.info_list.configure(yscrollcommand=scrollbar.set)

        # Double-click to open preview window
        self.info_list.bind("<Double-Button-1>", self._on_double_click)

    # ------------- Core GUI methods ------------- #
    def _on_browse(self):
        path = filedialog.askopenfilename(
            title="Open MAT file (v5/v7.2)",
            filetypes=[("MATLAB files", "*.mat"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.signals = collect_signals_v5(path)
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

        self._refresh_listbox()

    def _refresh_listbox(self):
        self.info_list.delete(0, "end")
        for name in self.signals:
            sig = self.signals[name]
            display = f"{name}  |  dtype={sig.dtype}, size={sig.size}"
            self.info_list.insert("end", display)

    def _on_double_click(self, event):
        selection = self.info_list.curselection()
        if not selection:
            return

        idx = selection[0]
        name = self.info_list.get(idx)
        name = name.split("|", 1)[0].strip()
        data = self.signals.get(name)
        if data is None:
            return

        self._show_signal_preview(name, data)

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