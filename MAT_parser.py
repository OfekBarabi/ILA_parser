# mat_file_parser_tab.py
import tkinter as tk
from tkinter import ttk


class MatFileParserTab(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # Placeholder content – tab is effectively "empty" for now
        ttk.Label(self, text="Mat file parser (coming soon)").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
