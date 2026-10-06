"""Original background music, synthesized from scratch (no samples, no third-party audio).

Usage: python3 tools/music.py <style: garden|home> <seconds> <seed> <out.wav>

garden: bright plucked arpeggios + soft pad + light shaker (seed videos)
home:   warm electric-piano chords + bass + soft kick/hat (furniture videos)
Because every note is generated here, there is no licence to track.
"""
import sys
import numpy as np
from scipy.signal import fftconvolve, lfilter
from scipy.io import wavfile

SR = 44100
rng = None


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n, a, d, s=0.0, curve=4.0):
    """attack seconds a, then exponential decay over d seconds towards s."""
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) * curve / max(d, 1e-4)))
    return e


def pluck(f, dur, bright=0.5):
    """Karplus-Strong string."""
    n = int(dur * SR)
    p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    buf = lfilter([bright], [1, -(1 - bright)], buf)   # soften the attack
    out = np.zeros(n)
    for i in range(n):
        v = buf[i % p]
        out[i] = v
        buf[i % p] = 0.996 * 0.5 * (v + buf[(i + 1) % p])
    return out * env(n, 0.002, dur, curve=3.0)


def epiano(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3)
            + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 6))
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    return tone * trem * env(n, 0.006, dur * 1.2, curve=2.5)


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):
            ph = rng.uniform(0, 2 * np.pi)
            out += np.sin(2 * np.pi * f * (1 + det / 100) * t + ph) + 0.25 * np.sin(4 * np.pi * f * t + ph)
    out /= max(1, len(freqs) * 3)
    a = min(0.8, dur / 3)
    e = np.clip(np.minimum(t / a, (dur - t) / a), 0, 1)
    return out * e


def kick(dur=0.35):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat(dur=0.06, gain=1.0):
    n = int(dur * SR)
    noise = rng.uniform(-1, 1, n)
    noise = np.diff(noise, prepend=0)                  # crude high-pass
    return noise * np.exp(-np.arange(n) / SR * 60) * gain


def reverb(sig, seconds=1.6, mix=0.22):
    n = int(seconds * SR)
    ir = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / SR * 4.0)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet = fftconvolve(sig, ir)[: len(sig)]
    return (1 - mix) * sig + mix * wet


def place(track, clip, at, gain=1.0):
    i = int(at * SR)
    if i >= len(track):
        return
    j = min(len(track), i + len(clip))
    track[i:j] += clip[: j - i] * gain


PROGS = {
    'garden': [[0, 4, 7], [7, 11, 14], [9, 12, 16], [5, 9, 12]],      # I V vi IV
    'garden2': [[0, 4, 7], [5, 9, 12], [9, 12, 16], [7, 11, 14]],     # I IV vi V
    'home': [[0, 4, 7, 11], [9, 12, 16, 19], [2, 5, 9, 12], [7, 11, 14, 17]],   # Imaj7 vi7 ii7 V7
    'home2': [[5, 9, 12, 16], [4, 7, 11, 14], [2, 5, 9, 12], [0, 4, 7, 11]],    # IVmaj7 iii7 ii7 Imaj7
}


def make(style, seconds, seed):
    global rng
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    L = np.zeros(n)
    R = np.zeros(n)
    if style == 'garden':
        bpm = 92 + (seed % 3) * 4
        key = 62 + [0, 2, -3, 5, -2][seed % 5]          # around D
        prog = PROGS['garden' if seed % 2 == 0 else 'garden2']
    else:
        bpm = 78 + (seed % 3) * 3
        key = 53 + [0, 2, -2, 3, 5][seed % 5]           # around F
        prog = PROGS['home' if seed % 2 == 0 else 'home2']
    beat = 60.0 / bpm
    bar = beat * 4
    bars = int(np.ceil(seconds / bar)) + 1
    for b in range(bars):
        chord = prog[b % len(prog)]
        t0 = b * bar
        if style == 'garden':
            p = pad([midi(key - 12 + c) for c in chord], bar + 0.6)
            place(L, p, t0, 0.18); place(R, p, t0, 0.18)
            pattern = [0, 1, 2, 1, 0, 2, 1, 2]                 # eighth-note arpeggio
            for k, idx in enumerate(pattern):
                note = key + chord[idx] + (12 if k in (2, 6) else 0)
                c = pluck(midi(note), beat * 1.6, bright=0.45)
                pan = 0.35 + 0.3 * (k % 2)
                place(L, c, t0 + k * beat / 2, 0.30 * (1 - pan) * 2)
                place(R, c, t0 + k * beat / 2, 0.30 * pan * 2)
            bass = pluck(midi(key - 24 + chord[0]), bar, bright=0.3)
            place(L, bass, t0, 0.35); place(R, bass, t0, 0.35)
            for k in range(8):                                 # shaker on off-beats
                if b > 0 or k >= 4:
                    h = hat(0.05, 0.05 if k % 2 else 0.025)
                    place(L, h, t0 + k * beat / 2, 0.8); place(R, h, t0 + k * beat / 2 + 0.004, 0.8)
        else:
            for hit in (0, 2.5):                               # syncopated chord stabs
                for c in chord:
                    e = epiano(midi(key + c), beat * 2.2)
                    place(L, e, t0 + hit * beat, 0.17); place(R, e, t0 + hit * beat + 0.003, 0.17)
            bass = epiano(midi(key - 12 + chord[0]), bar)
            place(L, bass, t0, 0.15); place(R, bass, t0, 0.15)
            if b > 0:
                for k in (0, 2.5):
                    place(L, kick(), t0 + k * beat, 0.2); place(R, kick(), t0 + k * beat, 0.2)
                for k in range(8):
                    g = 0.035 if k % 2 else 0.02
                    place(L, hat(0.05, g), t0 + k * beat / 2, 1.0); place(R, hat(0.05, g), t0 + k * beat / 2, 1.0)
            # simple melody: chord tones, one per beat, sparse
            for k in (1, 3):
                note = key + 12 + chord[(b + k) % len(chord)]
                m = pluck(midi(note), beat * 1.5, bright=0.35)
                place(L, m, t0 + k * beat, 0.16); place(R, m, t0 + k * beat, 0.16)
    L = reverb(L); R = reverb(R)
    a = np.exp(-2 * np.pi * 7000 / SR)            # gentle master low-pass
    L = lfilter([1 - a], [1, -a], L); R = lfilter([1 - a], [1, -a], R)
    t = np.arange(n) / SR
    fade = np.clip(np.minimum(t / 0.4, (seconds - t) / 1.8), 0, 1)
    st = np.stack([L * fade, R * fade], axis=1)
    st /= max(1e-6, np.max(np.abs(st))) / 0.7                  # peak -3 dBFS
    return st


if __name__ == '__main__':
    style, sec, seed, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    wavfile.write(out, SR, (make(style, sec, seed) * 32767).astype(np.int16))
    print('wrote', out)
