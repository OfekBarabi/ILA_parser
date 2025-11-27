# ILA CSV Parser -- README

A small desktop tool for exploring, decoding, exporting, and plotting
data captured from Vivado ILA CSV files.\
The app is built with Tkinter and matplotlib and wraps the
parsing/formatting logic in a simple GUI.

------------------------------------------------------------------------

## Overview

Typical Vivado ILA captures export data as CSV: many probes, packed hex
words, custom fixed-point or float formats, VALID/SOP/EOP handshakes,
etc. Manually decoding and plotting that data is annoying.

This application lets you:

1.  Load an ILA CSV.
2.  Search and select signals by substring.
3.  Decode packed fixed-point or custom float formats, including complex
    I/Q and parallel concatenation.
4.  Optionally filter by VALID/SOP/EOP signals.
5.  Combine two signals into complex or even/odd interleaved data.
6.  Export decoded signals to text/BTE format.
7.  Plot time-domain waveforms and FFTs (single or multiple signals), or
    plot data from existing files.

------------------------------------------------------------------------

## Main Features

### 1. CSV Loading & Signal Search

-   Load a Vivado ILA CSV file from disk.
-   Specify a substring to search for in the **short** signal name (last
    component of the path).
-   Search is **case-sensitive** (`Upper/Lower case sensitive`).
-   Displays all matching signals in an input signal list.
-   Switch between **full hierarchical names** and **short names** for
    display.

### 2. Data Type & Precision Configuration

-   Supports three input data modes:
    -   **Fixed**: `s.int.frac` format
        -   Configure `[sign_bits, int_bits, frac_bits]`.
        -   Handles signed two's-complement conversion.
    -   **Float**: custom format
        -   `[exp_bits, mantissa_bits]`.
        -   Interprets word as `[exp][mant_I][mant_Q]` and converts
            mantissas to signed fixed.
    -   **As-is**:
        -   Leave samples as raw strings (no numeric conversion).
-   **Complex data (I/Q)** toggle:
    -   For fixed, allows decoding complex words where I/Q are packed
        into a single word.
-   **Data concatenation**:
    -   `data_par` -- number of packed samples in one word.
    -   Mode:
        -   **Serial** -- unpack sequentially into one list.
        -   **Parallel** -- unpack into multiple parallel streams, each
            exported as a separate signal name.

### 3. VALID / SOP / EOP Filtering

-   Select signals to act as:
    -   **VALID**
    -   **SOP** (start of packet)
    -   **EOP** (end of packet)
-   Optionally enable each with a checkbox.
-   The app can:
    -   Trim data between SOP and EOP.
    -   Keep only samples where VALID is asserted.
-   Filtering is applied before conversion, so you work only on
    meaningful data ranges.

### 4. Conversion Pipeline

-   Conversion logic centralized in helper functions:
    -   `fixed_to_dec(...)` -- decode fixed-point (optionally complex,
        parallel).\
    -   `float_to_dec(...)` -- decode the custom I/Q float format.\
    -   `convert_db(...)` -- apply conversion to a dictionary of signals
        according to GUI settings.
-   Handles both **serial** and **parallel** unpacking:
    -   In parallel mode, each lane is named `signal_0`, `signal_1`,
        etc.
-   Decoded signals are stored in `db_converted` and listed in the
    "Converted signals" listbox.

### 5. Signal Combination (Real/Imag or Even/Odd)

-   Select **exactly two** raw signals and combine them after
    conversion:
    -   **Real/Imag (Re/Im)**:
        -   First signal is interpreted as real, second as imaginary →
            complex output.
        -   Only supported for scalar fixed-point / float where it makes
            sense.
    -   **Even/Odd**:
        -   Interleave two sequences as even/odd samples:
            `[a0, b0, a1, b1, ...]`.
-   Optional **swap** checkbox to flip roles of the two inputs.
-   Combined result is added as a new converted signal with an
    informative name.

### 6. Data Export (Text / BTE Format)

-   Choose output directory and base file name.
-   Export:
    -   **All converted signals** (if nothing is selected).
    -   **Only selected signals** (if some are highlighted).
-   Standard text format:
    -   One line per sample: `"imag real"` (imag and real as strings).
-   **BTE format** option:
    -   On export, optionally reconvert numeric data into fixed format
        using export precision `[sign, int, frac]`.
    -   Writes:
        -   Header line `START 0`
        -   One line per sample: `imag real` as integer values.
        -   Final line `END 0`
    -   Designed to match a specific external tool or hardware loader.

### 7. Plotting & MultiPlot

-   Plot **converted signals** or **data from arbitrary text/BTE
    files**.
-   Supported plot types:
    -   Time domain:
        -   Time -- Real
        -   Time -- Imag
        -   Time -- Magnitude
        -   Time -- Phase
    -   Frequency domain:
        -   FFT -- Magnitude
        -   FFT -- dB (20·log10)
-   **Sample rate (Fs)** input:
    -   If provided, FFT axis is in Hz.
    -   If left empty, x-axis is bin index.
-   **X-axis limits**:
    -   Optional `Xmin` / `Xmax` fields to zoom in on time or frequency
        windows.
-   **MultiPlot**:
    -   Select multiple converted signals with equal length and plot
        them together.
    -   Each series gets its own curve and legend.
-   **Plot from file**:
    -   Regular text/CSV files with 1 or 2 numeric columns.
        -   1 column → real values.
        -   2 columns → interpret as (imag, real).
    -   BTE files with `START` / `END` are also supported.

### 8. Data Inspection Utilities

-   Double-click a converted signal to open a new window with all its
    samples listed (`index: value`).
-   Scrollable text view lets you quickly inspect sample values for
    debugging.

------------------------------------------------------------------------

## Files & Structure

-   **`main_gui.py`** --- Tkinter GUI, interactions, plotting.
-   **`helper_funcs.py`** --- Numeric conversions, CSV parsing,
    filtering, database handling.

------------------------------------------------------------------------

## Requirements

-   Python 3.x\
-   `numpy`, `matplotlib`\
-   Tkinter (included in most Python distributions)

Install dependencies:

    pip install numpy matplotlib

------------------------------------------------------------------------

## How to Run

    python main_gui.py

------------------------------------------------------------------------

## Typical Workflow

1.  Load CSV & Search\
2.  Select Signals & Configure Format\
3.  Convert\
4.  Combine (optional)\
5.  Export\
6.  Plot
