import csv
from pathlib import Path
import numpy as np

# ------------------------
#  Core conversion helpers
# ------------------------

def to_signed_dec(raw, data_prec):
    """
    Convert an integer 'raw' in fixed-point s.int.frac format
    into a Python float.
    data_prec = [sign_bits, int_bits, frac_bits]
    """
    sign_bits, int_bits, frac_bits = data_prec
    total_bits = sign_bits + int_bits + frac_bits

    # Signed?
    if sign_bits == 1 and (raw & (1 << (total_bits - 1))):
        raw -= 1 << total_bits  # two's complement

    return raw / (2 ** frac_bits)


def convert_to_fixed(samples, sign_bit, int_bits, frac_bits):
    """
    Convert an array of real-valued samples (floats) into fixed-point integers
    in s.int.frac format, suitable for hardware (two's complement).

    samples   : iterable of floats
    sign_bit  : 1 for signed two's complement, 0 for unsigned
    int_bits  : number of integer bits (excluding sign)
    frac_bits : number of fractional bits

    Returns: list of ints in the range representable by the given format.
    """
    total_bits = sign_bit + int_bits + frac_bits
    scale = 1 << frac_bits
    mag_bits = int_bits + frac_bits  # magnitude bits (excluding sign)

    if sign_bit == 1:
        # two's complement signed range
        min_val = -(1 << mag_bits)
        max_val = (1 << mag_bits) - 1
    else:
        # unsigned range
        min_val = 0
        max_val = (1 << mag_bits) - 1

    mask = (1 << total_bits) - 1

    fixed_vals = []
    for x in samples:
        # scale float to fixed
        val_real = int(round(np.real(x) * scale))
        val_imag = int(round(np.imag(x) * scale))

        # saturate to representable range
        if val_real < min_val:
            val_real = min_val
        elif val_real > max_val:
            val_real = max_val

        if val_imag < min_val:
            val_imag = min_val
        elif val_imag > max_val:
            val_imag = max_val

        # map to raw hardware word (two's complement for signed)
        fixed_vals.append(complex(val_real,val_imag))

    return fixed_vals


def fixed_to_dec(samples, data_prec, data_complex, data_par, data_par_mode):
    """
    Convert samples encoded as fixed-point (optionally complex, concatenated).
    samples: list of hex strings or ints
    data_prec: [sign_bits, int_bits, frac_bits]
    data_complex: "y" for complex, anything else for real
    data_par: how many packed samples in one word
    """
    sign_bits, int_bits, frac_bits = data_prec
    total_bits = sign_bits + int_bits + frac_bits

    sample_size_in_bits = total_bits * (2 if data_complex == "y" else 1)
    mask_all = (1 << sample_size_in_bits) - 1
    mask_iq = (1 << total_bits) - 1

    # Initialize output structure properly
    if data_par_mode == "parallel":
        out = [[] for _ in range(data_par)]
    else:
        out = []

    for sample in samples:
        if isinstance(sample, str):
            sample = int(sample, 16)

        for i in range(data_par):
            raw = sample & mask_all
            raw_i = raw & mask_iq
            raw_q = 0
            if data_complex == "y":
                raw_q = (raw >> total_bits) & mask_iq

            val_i = to_signed_dec(raw_i, data_prec)
            val_q = to_signed_dec(raw_q, data_prec)
            value = complex(val_i, val_q) if data_complex == "y" else val_i
            if data_par_mode == "parallel": # Parallel
                out[i].append(value)
            else: # Serial
                out.append(value)

            sample >>= sample_size_in_bits

    return out


def float_to_dec(samples, data_prec, data_complex, data_par, data_par_mode):
    """
    Convert samples encoded as custom float:
    [exp_bits][mantissa_I_bits][mantissa_Q_bits]
    samples: list of hex strings or ints
    data_prec: [exp_bits, man_bits]  (man_bits for I and Q each)
    data_complex is currently ignored (assumed complex)
    data_par: how many packed samples in one word
    """
    exp_bits, man_bits = data_prec
    man_mask = (1 << man_bits) - 1
    exp_mask = (1 << exp_bits) - 1

    total_bits = exp_bits + 2 * man_bits
    sample_mask = (1 << total_bits) - 1

    # Initialize output structure properly
    if data_par_mode == "parallel":
        out = [[] for _ in range(data_par)]
    else:
        out = []

    for sample in samples:
        if isinstance(sample, str):
            sample = int(sample, 16)

        for i in range(data_par):
            sample_raw = sample & sample_mask

            man_i_raw = sample_raw & man_mask
            man_q_raw = (sample_raw >> man_bits) & man_mask
            exp_raw = (sample_raw >> (2 * man_bits)) & exp_mask

            man_i = to_signed_dec(man_i_raw, [1, 0, man_bits-1])
            man_q = to_signed_dec(man_q_raw, [1, 0, man_bits-1])

            value = complex(man_i, man_q) # * (2 ** exp_raw)
            if data_par_mode == "parallel":
                out[i].append(value)
            else:
                out.append(value)

            sample >>= total_bits

    return out


def sample_is_valid(val) -> bool:
    """Return True if 'val' represents a logical 1."""
    # Handle ints directly
    if isinstance(val, int):
        return val == 1

    if not isinstance(val, str):
        return False

    s = val.strip()
    if not s:
        return False

    # Try to parse as integer with auto base (handles 0x1, 0b1, etc.)
    try:
        v = int(s, 0)
        return v == 1
    except ValueError:
        # Fallback: some weird literal like "1'b1"
        if s in ("1", "1'b1", "1b1"):
            return True
        return False


def convert_db(db_in, data_type, data_prec, data_complex, data_par, data_par_mode):
    """
    Convert the samples in db according to user settings.
    db_in: {sig_name: {"idx": int, "samples": [raw_strings]}}
    returns new dict: {sig_name: {"samples": [converted_values]}}
    """
    db_out = {}
    for sig, info in db_in.items():
        samples = info["samples"]
        if data_type == "1":      # Fixed
            converted = fixed_to_dec(samples, data_prec, data_complex, data_par, data_par_mode)
        elif data_type == "2":    # Float
            converted = float_to_dec(samples, data_prec, data_complex, data_par, data_par_mode)
        else:                     # As-is
            converted = samples[:]

        if data_par_mode == "serial": # Serial
            db_out[sig] = {"samples": converted}
        else: # Parallel
            for idx,arr in enumerate(converted):
                sig_indexed = sig + "_" + str(idx)
                db_out[sig_indexed] = {"samples": arr}

    return db_out


def load_signals_from_csv(csv_path: Path, name_filter: str):
    """
    Parse the CSV file, find all columns whose *short* name contains 'name_filter',
    and load all samples for those columns.

    Returns:
        {
            full_signal_name: {
                "idx": abs_col_idx,
                "samples": [raw_strings],
                "short_name": short_signal_name,
            },
            ...
        }
    """
    db = {}

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)

        header = next(reader, None)
        if not header:
            raise ValueError("CSV appears to be empty.")

        base_idx = 3  # first 3 columns are metadata
        data_header = header[base_idx:]

        # Find relevant columns
        for idx, signal_name in enumerate(data_header):
            # full name from header
            full_name = signal_name
            # short name for filtering / display
            signal_name_short = Path(signal_name).name
            if name_filter in signal_name_short:
                abs_col_idx = base_idx + idx
                db[full_name] = {
                    "idx": abs_col_idx,
                    "samples": [],
                    "short_name": signal_name_short,
                }

        if not db:
            raise ValueError(f"No columns matched '{name_filter}'.")

        # Second row is radix row; skip it
        next(reader, None)

        # Read all data rows
        for row in reader:
            if len(row) <= base_idx:
                continue
            for full_name, info in db.items():
                col = info["idx"]
                if col < len(row):
                    info["samples"].append(row[col])

    return db


def filter_data(samples, valid_samples=None, sop_samples=None, eop_samples=None):
    """
    Filter `samples` using optional VALID, SOP and EOP signals.

    - If SOP is given: keep from first SOP==1 onward.
    - If EOP is given: stop after first EOP==1 (including that sample).
    - If VALID is given: within that range, keep only VALID==1 samples.
    - If VALID is None/Falsey: keep all samples in the SOP/EOP range.
    """
    n = len(samples)
    end = n

    # Find start (SOP)
    start = 0
    if sop_samples:
        for i in range(start, end):
            if sop_samples[i] == '1':
                start = i
                break

    # Find end (EOP), exclusive
    if eop_samples:
        for i in range(start, end):
            if eop_samples[i] == '1':
                end = i + 1  # +1 because of range()
                break

    # Apply VALID filter (if provided)
    filtered_samples = []
    if valid_samples:
        for i in range(start, end):
            if valid_samples[i] == '1':
                filtered_samples.append(samples[i])

    return filtered_samples