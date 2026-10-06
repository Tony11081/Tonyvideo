"""Beat-locked original soundtrack + sound effects for v3 videos (all synthesized here, no samples).

Usage: python3 tools/v3/audio.py <style garden|home> <bpm> <beats> <seed> <events.json> <out.wav>

- Music is written on the same 120 BPM grid the picture uses, starting on a downbeat at t=0.
- Arrangement by bar: intro (light) -> groove -> hero lift -> CTA -> return; no fade-out,
  the last bar leads back into bar 1 so the Short loops.
- Sound effects are placed by their peak on the events the picture reports (window.EVENTS).
"""
import json, sys
import numpy as np
from scipy.signal import fftconvolve, lfilter
from scipy.io import wavfile

SR = 44100


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.L = np.zeros(self.n); self.R = np.zeros(self.n)

    def add(self, clip, at, gain=1.0, pan=0.5):
        i = int(round(at * SR))
        if i >= self.n or i + len(clip) <= 0:
            return
        a = max(0, i); b = min(self.n, i + len(clip))
        c = clip[a - i:b - i] * gain
        self.L[a:b] += c * np.sqrt(1 - pan) * 1.41
        self.R[a:b] += c * np.sqrt(pan) * 1.41


def env(n, a, d, curve=4.0):
    t = np.arange(n) / SR
    return np.where(t < a, t / max(a, 1e-4), np.exp(-(t - a) * curve / max(d, 1e-4)))


def pluck(rng, f, dur, bright=0.45):
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = lfilter([bright], [1, -(1 - bright)], rng.uniform(-1, 1, p))
    out = np.zeros(n)
    for i in range(n):
        v = buf[i % p]; out[i] = v; buf[i % p] = 0.996 * 0.5 * (v + buf[(i + 1) % p])
    return out * env(n, 0.002, dur, 3.0)


def keys(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 3)
            + 0.1 * np.sin(6 * np.pi * f * t) * np.exp(-t * 6))
    return tone * (1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)) * env(n, 0.006, dur * 1.3, 2.5)


def pad(rng, freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for f in freqs:
        for det in (-0.1, 0.0, 0.1):
            ph = rng.uniform(0, 6.28)
            out += np.sin(2 * np.pi * f * (1 + det / 100) * t + ph) + 0.2 * np.sin(4 * np.pi * f * t + ph)
    out /= max(1, 3 * len(freqs))
    a = min(0.5, dur / 4)
    return out * np.clip(np.minimum(t / a, (dur - t) / a), 0, 1)


def kick():
    n = int(0.32 * SR); t = np.arange(n) / SR
    f = 48 + 80 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10)


def noise_burst(rng, dur, decay, hp=True):
    n = int(dur * SR); z = rng.uniform(-1, 1, n)
    if hp:
        z = np.diff(z, prepend=0)
    return z * np.exp(-np.arange(n) / SR * decay)


def snap(rng):
    a = noise_burst(rng, 0.12, 35, hp=False)
    b, aa = [0.3], [1, -0.7]
    return lfilter(b, aa, a) * 0.9


# ---------------- sound effects ----------------
def sfx(rng, kind):
    t = lambda d: np.arange(int(d * SR)) / SR
    if kind == 'tick':
        tt = t(0.06); return np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt * 70) * 0.5
    if kind == 'click':
        tt = t(0.08); return (np.sin(2 * np.pi * 1200 * tt) + 0.5 * np.sin(2 * np.pi * 2400 * tt)) * np.exp(-tt * 55) * 0.45
    if kind == 'pop':
        tt = t(0.12); f = 900 * np.exp(-tt * 18) + 250
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30) * 0.55
    if kind in ('whoosh', 'swish'):
        d = 0.45 if kind == 'whoosh' else 0.3; n = int(d * SR)
        z = rng.uniform(-1, 1, n); out = np.zeros(n); y = 0.0
        tt = np.arange(n) / n
        cut = 0.02 + 0.25 * np.sin(np.pi * tt)                  # sweeping low-pass
        for i in range(n):
            y += cut[i] * (z[i] - y); out[i] = y
        return out * np.sin(np.pi * tt) ** 2 * (1.6 if kind == 'whoosh' else 1.1)
    if kind == 'impact':
        tt = t(0.6); f = 70 * np.exp(-tt * 6) + 38
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 6)
        return body * 0.9 + noise_burst(rng, 0.6, 18, hp=False) * 0.12
    if kind == 'drop':
        tt = t(0.25); f = 600 * np.exp(-tt * 10) + 180
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14) * 0.5
    if kind == 'sprinkle':
        out = np.zeros(int(0.5 * SR))
        for k in range(10):
            c = sfx(rng, 'tick') * 0.4; i = int(k * 0.04 * SR + rng.uniform(0, 0.01) * SR)
            out[i:i + len(c)] += c[:len(out) - i]
        return out
    if kind == 'drip':
        tt = t(0.18); f = 500 + 900 * tt / 0.18
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 22) * 0.4
    return np.zeros(1)


SFX_GAIN = {'tick': .35, 'click': .4, 'pop': .45, 'whoosh': .5, 'swish': .4, 'impact': .7, 'drop': .4, 'sprinkle': .35, 'drip': .35}

PROG = {
    'garden': [[0, 4, 7], [9, 12, 16], [5, 9, 12], [7, 11, 14]],        # I vi IV V (bright)
    'home': [[0, 4, 7, 11], [9, 12, 16, 19], [5, 9, 12, 16], [7, 11, 14, 17]],
}


def music(style, bpm, beats, seed):
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm; bar = beat * 4; bars = int(np.ceil(beats / 4))
    seconds = beats * beat
    m = Mix(seconds + 2.0)                                   # tail, cut later and folded to bar 1
    key = (62 if style == 'garden' else 53) + [0, 2, -2, 3][seed % 4]
    prog = PROG[style]
    # energy per bar: 0 intro, 1 groove, 2 lift (hero), 3 cta, 4 return
    shape = {0: 0, 1: 1, 2: 1, 3: 1, 4: 2, 5: 3, 6: 3, 7: 4}
    for b in range(bars):
        e = shape.get(b, 1); t0 = b * bar; ch = prog[b % len(prog)]
        m.add(pad(rng, [midi(key - 12 + c) for c in ch[:3]], bar + 0.4), t0, 0.14 + 0.04 * (e == 2))
        if style == 'garden':
            pat = [0, 1, 2, 1, 0, 2, 1, 2] if e else [0, 2, 1, 2]
            step = beat / 2 if e else beat
            for k, idx in enumerate(pat):
                note = key + ch[idx] + (12 if k in (2, 6) else 0)
                m.add(pluck(rng, midi(note), beat * 1.5), t0 + k * step, 0.24, 0.3 + 0.4 * (k % 2))
            m.add(pluck(rng, midi(key - 24 + ch[0]), bar, 0.3), t0, 0.32)
        else:
            for hit in (0, 1.5, 2.5) if e else (0,):
                for c in ch:
                    m.add(keys(midi(key + c), beat * 1.8), t0 + hit * beat, 0.09, 0.45 + 0.1 * (c % 2))
            m.add(keys(midi(key - 12 + ch[0]), bar), t0, 0.16)
        if e in (1, 2, 3):
            for k in range(4):
                if k % 2 == 0:
                    m.add(kick(), t0 + k * beat, 0.30)
                else:
                    m.add(snap(rng), t0 + k * beat, 0.16, 0.55)
            for k in range(8):
                m.add(noise_burst(rng, 0.04, 70), t0 + k * beat / 2, 0.035 if k % 2 else 0.02, 0.6)
        if e == 4:                                            # return bar: filtered, leads into bar 1
            m.add(kick(), t0, 0.22)
    # fold the tail into the start so the loop point is seamless
    tail = int(seconds * SR)
    L = m.L[:tail].copy(); R = m.R[:tail].copy()
    extra = m.n - tail
    L[:extra] += m.L[tail:] * 0.8; R[:extra] += m.R[tail:] * 0.8
    return L, R, seconds


def reverb(rng, sig, seconds=1.4, mix=0.18):
    n = int(seconds * SR)
    ir = rng.uniform(-1, 1, n) * np.exp(-np.arange(n) / SR * 4.5); ir /= np.sqrt(np.sum(ir ** 2))
    return (1 - mix) * sig + mix * fftconvolve(sig, ir)[:len(sig)]


def main():
    style, bpm, beats, seed, evfile, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6]
    rng = np.random.default_rng(seed + 100)
    L, R, seconds = music(style, bpm, beats, seed)
    L = reverb(rng, L); R = reverb(rng, R)
    a = np.exp(-2 * np.pi * 8000 / SR); L = lfilter([1 - a], [1, -a], L); R = lfilter([1 - a], [1, -a], R)
    mus = max(1e-6, np.max(np.abs(np.stack([L, R]))))
    L /= mus; R /= mus
    fx = Mix(seconds)
    for e in json.load(open(evfile)):
        clip = sfx(rng, e['kind'])
        if len(clip) < 2:
            continue
        peak = int(np.argmax(np.abs(clip)))            # place by peak, not by file start
        fx.add(clip, e['t'] - peak / SR, SFX_GAIN.get(e['kind'], .4), 0.5)
    L = 0.8 * L + fx.L[:len(L)]; R = 0.8 * R + fx.R[:len(R)]
    st = np.stack([L, R], axis=1); st /= np.max(np.abs(st)) / 0.8
    wavfile.write(out, SR, (st * 32767).astype(np.int16))
    print('wrote', out, f'{seconds:.2f}s')


if __name__ == '__main__':
    main()
