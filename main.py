import tkinter as tk
from tkinter import ttk

from ILA_CSV_parser import ILACSVParserTab
from DSP_lab import DSPLabTab
from MAT_parser import MatFileParserTab


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DSP Toolbox")
        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.ila_tab = ILACSVParserTab(notebook)
        self.dsp_tab = DSPLabTab(notebook)
        self.mat_tab = MatFileParserTab(notebook)

        notebook.add(self.ila_tab, text="ILA CSV Parser")
        notebook.add(self.dsp_tab, text="DSP-Lab")
        notebook.add(self.mat_tab, text="MAT Parser")


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
