import csv
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from scipy.io.matlab.mio5_params import mat_struct

# ------------------------
#  Core conversion helpers
# ------------------------

# ---------- MAT Helpers ---------- #
def _matobj_to_dict(obj):
    """
    Recursively convert scipy.io.matlab.mat_struct and object arrays
    into nested Python dict / list / numpy arrays.
    """
    if isinstance(obj, mat_struct):
        out = {}
        for name in obj._fieldnames:
            value = getattr(obj, name)
            out[name] = _matobj_to_dict(value)
        return out

    # cell arrays or struct arrays become lists
    if isinstance(obj, np.ndarray) and obj.dtype == object:
        return [_matobj_to_dict(v) for v in obj.flat]

    # numeric arrays, strings, scalars – leave as is
    return obj


def _flatten_struct(obj, parent_key="", sep="."):
    """
    Walk nested dict/list and yield (path, leaf_array).
    Only emits leaves that can be interpreted as numeric numpy arrays.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            yield from _flatten_struct(v, new_key, sep)

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            yield from _flatten_struct(v, new_key, sep)

    else:
        # leaf – try to interpret as numeric array
        arr = np.array(obj)
        if np.issubdtype(arr.dtype, np.number):
            # Only emit if we have a meaningful name
            if parent_key:
                yield parent_key, arr


def collect_signals_v5(path):
    """
    Load a (non-v7.3) MAT file and return:
        { "var.subfield[.subsub]": np.ndarray, ... }
    """
    raw = loadmat(path, struct_as_record=False, squeeze_me=True)

    # Strip MATLAB internal keys
    top = {}
    for k, v in raw.items():
        if k.startswith("__"): # Meta data
            continue
        top[k] = _matobj_to_dict(v)

    signals = {}
    for top_name, top_val in top.items():
        for name, arr in _flatten_struct(top_val, parent_key=top_name):
            signals[name] = arr

    return signals


# ---------- DSP Helpers ---------- #
# ---------- ILA Helpers ---------- #

def detect_csv_kind(csv_path: Path) -> str:

    """Return 'quartus_stp', 'vivado_ila', or 'unknown'."""

    try:

        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:

            head = [f.readline() for _ in range(120)]

    except Exception:

        return "unknown"



    head_txt = "".join(head).lower()



    # Quartus SignalTap export commonly includes these section headers

    if "groups:" in head_txt and "data:" in head_txt:

        return "quartus_stp"



    # Vivado ILA CSV often includes a Radix row / Sample in Buffer / Trigger

    if "radix" in head_txt or "sample in buffer" in head_txt or "trigger" in head_txt:

        return "vivado_ila"

    return "unknown"


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

        name_filter_lower = name_filter.lower()

        # Find relevant columns
        for idx, signal_name in enumerate(data_header):
            # full name from header
            full_name = signal_name
            # short name for filtering / display
            signal_name_short = Path(signal_name).name
            if name_filter_lower in signal_name_short.lower():
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


def _find_packet_ranges(n: int, sop_samples=None, eop_samples=None):
    """Return list of (start, end_exclusive) ranges for all packets found."""
    sop_samples = sop_samples or []
    eop_samples = eop_samples or []

    ranges = []
    i = 0

    while i < n:
        start = i

        # If SOP is provided, packet starts at next sop==1
        if sop_samples:
            found = False
            for k in range(i, n):
                if sample_is_valid(sop_samples[k]):
                    start = k
                    found = True
                    break
            if not found:
                break

        # End is next eop==1 after start (inclusive), else end of trace
        end = n
        if eop_samples:
            for k in range(start, n):
                if sample_is_valid(eop_samples[k]):
                    end = k + 1
                    break

        if end <= start:
            end = start + 1

        ranges.append((start, end))
        i = end

        # No SOP/EOP => single range
        if not sop_samples and not eop_samples:
            break

    return ranges


def filter_data_all_packets(samples, valid_samples=None, sop_samples=None, eop_samples=None):
    """Concatenate all packets into one list, optionally filtering by VALID within each packet."""
    n = len(samples)
    if n == 0:
        return []

    ranges = _find_packet_ranges(n, sop_samples=sop_samples, eop_samples=eop_samples)
    out = []

    for start, end in ranges:
        if valid_samples:
            for i in range(start, min(end, n)):
                if sample_is_valid(valid_samples[i]):
                    out.append(samples[i])
        else:
            out.extend(samples[start:min(end, n)])

    return out


def filter_data_packets_list(samples, valid_samples=None, sop_samples=None, eop_samples=None):
    """Return a list of packet arrays. Each packet may be filtered by VALID."""
    n = len(samples)
    if n == 0:
        return []

    ranges = _find_packet_ranges(n, sop_samples=sop_samples, eop_samples=eop_samples)
    packets = []

    for start, end in ranges:
        if valid_samples:
            pkt = []
            for i in range(start, min(end, n)):
                if sample_is_valid(valid_samples[i]):
                    pkt.append(samples[i])
            if pkt:
                packets.append(pkt)
        else:
            pkt = samples[start:min(end, n)]
            if pkt:
                packets.append(list(pkt))

    return packets
