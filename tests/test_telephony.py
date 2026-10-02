"""
VoiceGuard Telephony Pipeline Unit Tests
Validates:
1. 256-entry mu-law lookup table matches the reference ITU-T formula for all 256 byte codes.
2. 256-entry mu-law lookup table matches stdlib audioop.ulaw2lin oracle for all 256 byte codes.
3. Encoding table matches stdlib audioop.lin2ulaw oracle across a full sweep of 16-bit PCM values.
4. Twilio base64 media stream payload decoding and conversion.
5. Scipy polyphase anti-aliased resampling (8k <-> 16k) round-trip fidelity.
6. Telephony channel simulation (8 kHz G.711 codec quantization and bandwidth limit).
"""

import audioop
import base64
import numpy as np
import pytest
from server.telephony import (
    ULAW_DECODE_TABLE,
    decode_ulaw_bytes,
    encode_pcm_to_ulaw,
    decode_twilio_payload,
    resample_audio,
    simulate_telephony_channel,
)


def reference_ulaw_decode(byte_val: int) -> int:
    """ITU-T G.711 reference formula for decoding a single mu-law byte to int16 PCM."""
    u = (~byte_val) & 0xFF
    t = (((u & 0x0F) << 3) + 0x84) << ((u & 0x70) >> 4)
    return (0x84 - t) if (u & 0x80) != 0 else (t - 0x84)


def test_ulaw_lookup_table_matches_reference_all_256_codes():
    """Validates that every single entry in the 256-entry table exactly matches reference formula."""
    for byte_code in range(256):
        expected = reference_ulaw_decode(byte_code)
        actual = int(ULAW_DECODE_TABLE[byte_code])
        assert actual == expected, (
            f"Mismatch at mu-law byte {byte_code}: reference expected {expected}, got {actual}"
        )


def test_ulaw_lookup_table_matches_audioop_all_256_codes():
    """Validates that the 256-entry lookup table matches stdlib audioop.ulaw2lin oracle for all 256 codes."""
    for byte_code in range(256):
        oracle_bytes = audioop.ulaw2lin(bytes([byte_code]), 2)
        oracle_pcm = int.from_bytes(oracle_bytes, "little", signed=True)
        table_pcm = int(ULAW_DECODE_TABLE[byte_code])
        assert table_pcm == oracle_pcm, (
            f"Mismatch at byte {byte_code}: audioop oracle={oracle_pcm}, table={table_pcm}"
        )


def test_ulaw_encode_matches_audioop_pcm_sweep():
    """Validates that encoding lookup table matches stdlib audioop.lin2ulaw across a full sweep of PCM values."""
    pcm_sweep = np.arange(-32768, 32768, dtype=np.int16)
    table_encoded = encode_pcm_to_ulaw(pcm_sweep)
    oracle_encoded = audioop.lin2ulaw(pcm_sweep.tobytes(), 2)
    assert table_encoded == oracle_encoded, "Encode lookup table produced mismatch against audioop.lin2ulaw"


def test_ulaw_roundtrip_pcm():
    """Validates that PCM encoded to mu-law and decoded back preserves speech amplitudes."""
    test_samples = np.linspace(-32000, 32000, 500, dtype=np.int16)
    ulaw_bytes = encode_pcm_to_ulaw(test_samples)
    decoded_pcm = decode_ulaw_bytes(ulaw_bytes)

    # Quantization error in G.711 mu-law is bounded by logarithmic step size (typically < 3.5%)
    max_abs_err = np.max(np.abs(test_samples.astype(float) - decoded_pcm.astype(float)))
    relative_err = np.mean(
        np.abs(test_samples.astype(float) - decoded_pcm.astype(float)) / (np.abs(test_samples.astype(float)) + 1e-5)
    )
    assert max_abs_err < 2000, f"Excessive quantization error: max abs error {max_abs_err}"
    assert relative_err < 0.05, f"Excessive mean relative error: {relative_err:.4f}"


def test_resample_poly_8k_to_16k_roundtrip():
    """Validates anti-aliased polyphase resampling between 8k and 16k."""
    t_8k = np.linspace(0, 1.0, 8000, endpoint=False, dtype=np.float32)
    orig_8k = np.sin(2 * np.pi * 500 * t_8k)

    # 8k -> 16k -> 8k
    up_16k = resample_audio(orig_8k, 8000, 16000)
    assert len(up_16k) == 16000
    down_8k = resample_audio(up_16k, 16000, 8000)
    assert len(down_8k) == 8000

    interior_slice = slice(500, 7500)
    max_diff = np.max(np.abs(orig_8k[interior_slice] - down_8k[interior_slice]))
    assert max_diff < 0.01, f"Resampling distortion too high: max diff {max_diff}"


def test_decode_twilio_payload():
    """Validates base64 Twilio media payload decoding to 16 kHz float32 mono."""
    synthetic_8k_pcm = (np.sin(np.linspace(0, 2 * np.pi * 10, 160)) * 16000).astype(np.int16)
    ulaw_bytes = encode_pcm_to_ulaw(synthetic_8k_pcm)
    b64_payload = base64.b64encode(ulaw_bytes).decode("ascii")

    decoded_16k = decode_twilio_payload(b64_payload)
    assert len(decoded_16k) == 320
    assert decoded_16k.dtype == np.float32
    assert -1.0 <= np.min(decoded_16k) <= 1.0
    assert -1.0 <= np.max(decoded_16k) <= 1.0


def test_simulate_telephony_channel_spectral_alteration():
    """Validates that offline phone codec simulation introduces realistic channel alterations."""
    t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
    in_band_tone = 0.5 * np.sin(2 * np.pi * 500 * t)
    out_band_tone = 0.5 * np.sin(2 * np.pi * 5500 * t) # Above 8 kHz telephony Nyquist (4000 Hz)
    signal = in_band_tone + out_band_tone

    simulated = simulate_telephony_channel(signal)

    assert len(simulated) == 16000
    assert simulated.dtype == np.float32
    assert -1.0 <= np.min(simulated) <= 1.0
    assert -1.0 <= np.max(simulated) <= 1.0

    fft_orig = np.abs(np.fft.rfft(signal))
    fft_sim = np.abs(np.fft.rfft(simulated))
    freqs = np.fft.rfftfreq(len(signal), d=1/16000)

    idx_500 = np.argmin(np.abs(freqs - 500))
    idx_5500 = np.argmin(np.abs(freqs - 5500))

    assert fft_sim[idx_500] > 0.3 * fft_orig[idx_500]
    assert fft_sim[idx_5500] < 0.05 * fft_orig[idx_5500]
