"""
VoiceGuard Telephony Pipeline
Pure-lookup G.711 mu-law decoding/encoding, Twilio payload decoding,
resampling via scipy.signal.resample_poly, and phone-line channel simulation.
Does NOT use audioop.
"""

import base64
from typing import Union
import numpy as np
from scipy.signal import resample_poly


# G.711 mu-law ITU-T 256-entry reconstruction table (decoded int16 PCM values)
# Every index corresponds to a byte code 0..255. Tested against ITU-T formula & stdlib oracle.
ULAW_DECODE_TABLE = np.array([
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364,  -9852,  -9340,  -8828,  -8316,
     -7932,  -7676,  -7420,  -7164,  -6908,  -6652,  -6396,  -6140,
     -5884,  -5628,  -5372,  -5116,  -4860,  -4604,  -4348,  -4092,
     -3900,  -3772,  -3644,  -3516,  -3388,  -3260,  -3132,  -3004,
     -2876,  -2748,  -2620,  -2492,  -2364,  -2236,  -2108,  -1980,
     -1884,  -1820,  -1756,  -1692,  -1628,  -1564,  -1500,  -1436,
     -1372,  -1308,  -1244,  -1180,  -1116,  -1052,   -988,   -924,
      -876,   -844,   -812,   -780,   -748,   -716,   -684,   -652,
      -620,   -588,   -556,   -524,   -492,   -460,   -428,   -396,
      -372,   -356,   -340,   -324,   -308,   -292,   -276,   -260,
      -244,   -228,   -212,   -196,   -180,   -164,   -148,   -132,
      -120,   -112,   -104,    -96,    -88,    -80,    -72,    -64,
       -56,    -48,    -40,    -32,    -24,    -16,     -8,      0,
     32124,  31100,  30076,  29052,  28028,  27004,  25980,  24956,
     23932,  22908,  21884,  20860,  19836,  18812,  17788,  16764,
     15996,  15484,  14972,  14460,  13948,  13436,  12924,  12412,
     11900,  11388,  10876,  10364,   9852,   9340,   8828,   8316,
      7932,   7676,   7420,   7164,   6908,   6652,   6396,   6140,
      5884,   5628,   5372,   5116,   4860,   4604,   4348,   4092,
      3900,   3772,   3644,   3516,   3388,   3260,   3132,   3004,
      2876,   2748,   2620,   2492,   2364,   2236,   2108,   1980,
      1884,   1820,   1756,   1692,   1628,   1564,   1500,   1436,
      1372,   1308,   1244,   1180,   1116,   1052,    988,    924,
       876,    844,    812,    780,    748,    716,    684,    652,
       620,    588,    556,    524,    492,    460,    428,    396,
       372,    356,    340,    324,    308,    292,    276,    260,
       244,    228,    212,    196,    180,    164,    148,    132,
       120,    112,    104,     96,     88,     80,     72,     64,
        56,     48,     40,     32,     24,     16,      8,      0,
], dtype=np.int16)


# ITU-T G.711 mu-law encoder table generation using piecewise segments (without audioop)
_SEG_UEND = [0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF, 0x1FFF]
_BIAS = 0x84
_CLIP = 32635


def _build_pcm_to_ulaw_table() -> np.ndarray:
    """Precomputes 65,536-entry G.711 mu-law lookup table for int16 PCM -> uint8 byte."""
    tbl = np.empty(65536, dtype=np.uint8)
    for idx in range(65536):
        pcm_val = idx if idx < 32768 else idx - 65536
        val32 = np.int32(pcm_val) << 16
        val14 = int(val32 >> 18)
        if val14 < 0:
            val14 = -val14
            mask = 0x7F
        else:
            mask = 0xFF
        if val14 > _CLIP:
            val14 = _CLIP
        val14 += (_BIAS >> 2)

        for seg in range(8):
            if val14 <= _SEG_UEND[seg]:
                break
        else:
            seg = 8

        if seg >= 8:
            code = 0x7F ^ mask
        else:
            code = ((seg << 4) | ((val14 >> (seg + 1)) & 0x0F)) ^ mask
        tbl[idx] = code
    return tbl


PCM_TO_ULAW_TABLE = _build_pcm_to_ulaw_table()


def decode_ulaw_bytes(ulaw_bytes: bytes) -> np.ndarray:
    """
    Decodes G.711 mu-law byte string to 8 kHz int16 PCM numpy array using 256-entry table.
    """
    byte_indices = np.frombuffer(ulaw_bytes, dtype=np.uint8)
    return ULAW_DECODE_TABLE[byte_indices]


def encode_pcm_to_ulaw(pcm_int16: np.ndarray) -> bytes:
    """
    Encodes 8 kHz int16 PCM numpy array to G.711 mu-law bytes using lookup table.
    """
    uint16_indices = pcm_int16.astype(np.uint16)
    ulaw_bytes = PCM_TO_ULAW_TABLE[uint16_indices]
    return ulaw_bytes.tobytes()


def decode_twilio_payload(base64_payload: str) -> np.ndarray:
    """
    Extracts base64 audio payload from Twilio media stream event,
    decodes G.711 mu-law to 8 kHz PCM, resamples to 16 kHz,
    and returns float32 mono audio clamped to [-1.0, 1.0].
    """
    ulaw_bytes = base64.b64decode(base64_payload)
    pcm_8k = decode_ulaw_bytes(ulaw_bytes)
    audio_float_8k = pcm_8k.astype(np.float32) / 32768.0

    # Resample 8 kHz -> 16 kHz (up=2, down=1)
    audio_float_16k = resample_poly(audio_float_8k, up=2, down=1)

    # Strictly guard bounds [-1.0, 1.0] without ad-hoc normalization
    audio_float_16k = np.clip(audio_float_16k, -1.0, 1.0)
    return audio_float_16k.astype(np.float32)


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Anti-aliased polyphase resampling between 8k and 16k.
    """
    if orig_sr == target_sr:
        return audio
    if orig_sr == 8000 and target_sr == 16000:
        return resample_poly(audio, up=2, down=1)
    elif orig_sr == 16000 and target_sr == 8000:
        return resample_poly(audio, up=1, down=2)
    else:
        from math import gcd
        g = gcd(orig_sr, target_sr)
        return resample_poly(audio, up=target_sr // g, down=orig_sr // g)


def simulate_telephony_channel(audio_16k_float: np.ndarray) -> np.ndarray:
    """
    Offline phone-line codec simulation:
    WAV (16 kHz float32) -> 8 kHz -> G.711 mu-law encode -> G.711 mu-law decode -> 16 kHz -> float32.
    Guards amplitude to [-1.0, 1.0] with zero arbitrary normalization.
    """
    if audio_16k_float.ndim > 1:
        audio_16k_float = audio_16k_float.mean(axis=1)

    # 1. Downsample 16 kHz -> 8 kHz (polyphase filter, anti-aliased)
    audio_8k = resample_poly(audio_16k_float, up=1, down=2)

    # 2. Convert float32 in [-1.0, 1.0] to int16 PCM
    pcm_8k = np.clip(audio_8k * 32767.0, -32768, 32767).astype(np.int16)

    # 3. G.711 mu-law codec quantization (encode -> decode via 256-entry tables)
    ulaw_bytes = encode_pcm_to_ulaw(pcm_8k)
    pcm_decoded_8k = decode_ulaw_bytes(ulaw_bytes)

    # 4. Upsample 8 kHz -> 16 kHz
    float_decoded_8k = pcm_decoded_8k.astype(np.float32) / 32767.0
    audio_simulated_16k = resample_poly(float_decoded_8k, up=2, down=1)

    # 5. Amplitude guard [-1.0, 1.0]
    audio_simulated_16k = np.clip(audio_simulated_16k, -1.0, 1.0)
    return audio_simulated_16k.astype(np.float32)
