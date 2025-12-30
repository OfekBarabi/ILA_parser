import tkinter as tk
from tkinter import ttk

from CSV_parser import CSVParserTab
from DSP_lab import DSPLabMatTab

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DSP Toolbox")
        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.csv_tab = CSVParserTab(notebook)
        self.dsp_mat_tab = DSPLabMatTab(notebook)

        notebook.add(self.csv_tab, text="CSV Parser")
        notebook.add(self.dsp_mat_tab, text="DSP-MAT-Lab")


def main():
    app = MainApp()
    app.mainloop()

if __name__ == "__main__":
    main()
