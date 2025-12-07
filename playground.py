from ba_quan import *

FLOAT_ENUM = {'MAN': 13, 'EXP': 6}


def exp_calc(num, sgn):

    l2 = np.log2(num)
    l2_r_up = np.ceil(l2)

    if l2 == l2_r_up and sgn > 0:
        return l2_r_up + 1
    else:
        return l2_r_up

def hdl_round(num):

    rounded_num = round(num)

    if rounded_num - num == -0.5:
        return rounded_num + 1
    else:
        return rounded_num

def Fix2Float(sig, in_prc, input_bias=0, exp_bias=0):
    sig = sig * (2 ** input_bias)

    data = ba_quan(x=sig, prec_out=in_prc)
    data = data.quantize_input()

    data = data * (2 ** in_prc['n'])

    new_i = np.array(list(map(np.real, data)))
    new_q = np.array(list(map(np.imag, data)))

    exp_i = np.zeros(len(sig))
    exp_i[np.where(new_i != 0)] = np.array(
        list(map(lambda x, y: exp_calc(x, y), abs(new_i[np.where(new_i != 0)]),
                 np.sign(new_i[np.where(new_i != 0)]))))

    exp_q = np.zeros(len(sig))
    exp_q[np.where(new_q != 0)] = np.array(
        list(map(lambda x, y: exp_calc(x, y), abs(new_q[np.where(new_q != 0)]),
                 np.sign(new_q[np.where(new_q != 0)]))))

    exp_res = np.add(np.array(list(map(max, exp_i, exp_q))), -FLOAT_ENUM['MAN'] + 1)

    exp_res[np.where(exp_res < 0)] = 0

    new_i[np.where(exp_res > 0)] = np.array(
        list(map(lambda x, y: hdl_round(x / (2 ** y)), new_i[np.where(exp_res > 0)],
                 exp_res[np.where(exp_res > 0)])))
    new_q[np.where(exp_res > 0)] = np.array(
        list(map(lambda x, y: hdl_round(x / (2 ** y)), new_q[np.where(exp_res > 0)],
                 exp_res[np.where(exp_res > 0)])))

    new_i[np.where(new_i > 0)] = np.array(
        list(map(lambda x: min(x, (2 ** (FLOAT_ENUM['MAN'] - 1)) - 1), new_i[np.where(new_i > 0)])))
    new_i[np.where(new_i < 0)] = np.add(new_i[np.where(new_i < 0)], 2 ** FLOAT_ENUM['MAN'])

    new_q[np.where(new_q > 0)] = np.array(
        list(map(lambda x: min(x, (2 ** (FLOAT_ENUM['MAN'] - 1)) - 1), new_q[np.where(new_q > 0)])))
    new_q[np.where(new_q < 0)] = np.add(new_q[np.where(new_q < 0)], 2 ** FLOAT_ENUM['MAN'])

    same_iq = np.where(new_i == new_q)
    zero = np.where(new_i[same_iq] == 0)

    exp_res += exp_bias
    exp_res[np.where(exp_res < 0)] = 0
    exp_res[same_iq[0][zero]] = 0  # If both i and q are 0

    out = np.array(list(
        map(lambda x, y, z:
            (int(x) << (2 * FLOAT_ENUM['MAN'])) + (int(y) << FLOAT_ENUM['MAN']) + int(z),
            exp_res, new_q, new_i)))

    return out

def norm_complex(arr):
    x = np.asarray(arr, dtype=complex)
    max_abs = np.max(np.abs(x))
    if max_abs == 0:
        return x  # all zeros, nothing to scale
    return x / max_abs

def round_fixed(input_val: int,input_width: int,output_width: int,round_negative_up: bool = True,support_saturation: bool = True,) -> int:
    """Python version of the VHDL 'round' for signed fixed-point two's complement."""

    assert input_width >= 1 and output_width >= 1

    in_mask  = (1 << input_width)  - 1
    out_mask = (1 << output_width) - 1
    x        = input_val & in_mask          # raw bits
    sign_bit = (x >> (input_width - 1)) & 1

    # Helpers for sign extension path
    def to_signed(bits: int, width: int) -> int:
        sign = 1 << (width - 1)
        return bits - (1 << width) if bits & sign else bits

    def from_signed(val: int, width: int) -> int:
        return val & ((1 << width) - 1)

    # If input fits in output width: only sign-extend
    if input_width <= output_width:
        return from_signed(to_signed(x, input_width), output_width)

    # input_width > output_width → need rounding
    drop = input_width - output_width

    # Take top output_width bits (same as input_vec(N-1 downto N-output_width))
    v = (x >> drop) & out_mask

    # Round bit: the bit right below the kept MSBs
    round_bit = (x >> (drop - 1)) & 1
    if round_bit == 0:
        # Nothing to round
        return v

    # ------------------------
    # Positive numbers:
    # ------------------------
    if sign_bit == 0:
        if not support_saturation:
            return (v + 1) & out_mask

        if output_width == 1:
            # With saturation & only 1 bit, don't increment (would flip sign)
            return v

        # Check if increment would overflow positive range
        max_mag_bits = (1 << (output_width - 1)) - 1           # all 1s in magnitude field
        mag_bits     = v & max_mag_bits                        # bits [output_width-2:0]
        if mag_bits != max_mag_bits:
            v = (v + 1) & out_mask
        return v

    # ------------------------
    # Negative numbers:
    # ------------------------
    if not round_negative_up:
        # Only add if we're not exactly at half (i.e., some lower bit is 1)
        lower_bits = x & ((1 << (drop - 1)) - 1) if drop > 1 else 0
        if lower_bits == 0:
            # Exactly half → no rounding in this mode
            return v

    # round_negative_up == True or not-half in "down" mode
    return (v + 1) & out_mask

def saturate_fixed(input_val: int, input_width: int, output_width: int) -> int:
    """
    Saturate a signed fixed-point value (two's complement) from input_width bits
    to output_width bits, mimicking the VHDL 'saturate' function.
    Returns an integer representing output_width bits.
    """
    assert input_width >= 1 and output_width >= 1

    in_mask  = (1 << input_width)  - 1
    out_mask = (1 << output_width) - 1
    x        = input_val & in_mask
    sign_bit = (x >> (input_width - 1)) & 1

    def to_signed(bits: int, width: int) -> int:
        sign = 1 << (width - 1)
        return bits - (1 << width) if bits & sign else bits

    def from_signed(val: int, width: int) -> int:
        return val & ((1 << width) - 1)

    # Case 1: input fits → just sign-extend
    if input_width <= output_width:
        return from_signed(to_signed(x, input_width), output_width)

    # Case 2: input wider than output → check if we need saturation
    # Bits to check: indices [input_width-2 .. output_width-1]
    span = input_width - output_width       # number of bits in that span
    region = (x >> (output_width - 1)) & ((1 << span) - 1)

    # For no saturation:
    #   sign=0 → all those bits must be 0
    #   sign=1 → all those bits must be 1
    if sign_bit == 0:
        overflow = (region != 0)
    else:
        overflow = (region != (1 << span) - 1)

    if overflow:
        # Saturate:
        # sign=0 → 0 111..1  (max positive)
        # sign=1 → 1 000..0  (max negative)
        if sign_bit == 0:
            return (1 << (output_width - 1)) - 1
        else:
            return 1 << (output_width - 1)

    # No saturation → just truncate to output_width bits
    return x & out_mask

def ans_base_calc_hw(float_sig_ddr, float_sig_acc, weight):
    mask_i_q = (2 ** FLOAT_ENUM['MAN']) - 1
    mask_exp = (2 ** FLOAT_ENUM['EXP']) - 1

    float_sig_ddr_i   =  float_sig_ddr                             & mask_i_q
    float_sig_ddr_q   = (float_sig_ddr << FLOAT_ENUM['MAN'])       & mask_i_q
    float_sig_ddr_exp = (float_sig_ddr << (2 * FLOAT_ENUM['MAN'])) & mask_exp

    float_sig_ddr_no_exp = float_sig_ddr_i + 1j * float_sig_ddr_q
    weighted_ddr = float_sig_ddr_no_exp * weight

    # quan
    in_width = 36
    round_width = 19
    out_width = 18
    for idx, w in enumerate(weighted_ddr):
        w_r = round_fixed(w, in_width, round_width)
        w_r_s = saturate_fixed(w_r, round_width, out_width)
        weighted_ddr[idx] = w_r_s

    weighted_ddr = np.array(list(
            map(lambda x, y, z:
                (int(x) << (2 * FLOAT_ENUM['MAN'])) + (int(y) << FLOAT_ENUM['MAN']) + int(z),
                float_sig_ddr_exp, np.imag(weighted_ddr), np.real(weighted_ddr))))

def ans_base_calc_sw(sig_1, sig_2, weight):
    return weight*sig_1 + sig_2

# --- Main ---
def main():
    in_prec = {'s':1,'m':0,'n':17}
    N = 20
    imag = np.random.randn(N,2)
    real = np.random.randn(N,2)
    sig_1 = norm_complex(real[0] + 1j * imag[0])
    sig_2 = norm_complex(real[1] + 1j * imag[1])

    float_sig_1 = Fix2Float(sig_1, in_prec)
    float_sig_2 = Fix2Float(sig_2, in_prec)

    weight = norm_complex(np.random.randn(1) + 1j * np.random.randn(1))
    weight = ba_quan(x=weight, prec_out=in_prec)
    weight = weight.quantize_input()
    weight = weight * (2 ** in_prec['n'])

    float_sig_3 = ans_base_calc(float_sig_1, float_sig_2, weight)

if __name__ == "__main__":
    main()