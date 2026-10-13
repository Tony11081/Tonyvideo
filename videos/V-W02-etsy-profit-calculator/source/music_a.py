"""Original score and sound design for film A (Etsy 利润计算器, 18 s).

Fully synthesised (no samples). 120 BPM, A minor, drop on beat 22 when the
order turns out to be an offsite-ads order. SFX come from eventsA.json, the
same timeline the picture uses (timelineA.js).

    python3 music_a.py   -> mix_a.wav
"""
import json
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
EV = json.load(open("eventsA.json"))
BEAT = EV["BEAT"]
DUR = EV["duration"]
N = int(SR * DUR)
AT = EV["at"]
rng = np.random.default_rng(7)


def b(x):
    return x * BEAT


def S(t):
    return int(round(t * SR))


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def m(name):  # "A3" -> midi
    return 12 * (int(name[-1]) + 1) + NOTE[name[:-1]]


# ---------------------------------------------------------------- buses
def bus():
    return np.zeros((2, N))


music = {k: bus() for k in ["pad", "bass", "pluck", "lead", "drums", "fx"]}
sfx = bus()
verb_send = bus()


def place(dst, x, t, gain=1.0, pan=0.0, send=0.0):
    """Add mono or stereo x at time t (s) with equal-power pan."""
    i = S(t)
    if i >= N:
        return
    if x.ndim == 1:
        l = np.cos((pan + 1) * np.pi / 4)
        r = np.sin((pan + 1) * np.pi / 4)
        x = np.vstack([x * l, x * r])
    n = min(x.shape[1], N - max(i, 0))
    j = max(-i, 0)
    i = max(i, 0)
    if n - j <= 0:
        return
    dst[:, i:i + n - j] += x[:, j:n] * gain
    if send:
        verb_send[:, i:i + n - j] += x[:, j:n] * gain * send


# ---------------------------------------------------------------- oscillators
_tables = {}


def saw_table(h):
    if h not in _tables:
        ph = np.arange(4096) / 4096
        k = np.arange(1, h + 1)[:, None]
        _tables[h] = (np.sin(2 * np.pi * k * ph[None, :]) / k).sum(0) * (2 / np.pi)
    return _tables[h]


def saw(freq, n, phase0=0.0):
    """Band-limited saw from a wavetable. freq: scalar or array of length n."""
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    h = max(1, int(16000 / max(f.max(), 1)))
    tab = saw_table(min(h, 200))
    ph = (phase0 + np.cumsum(f) / SR) % 1.0
    idx = ph * 4096
    i0 = idx.astype(int) % 4096
    frac = idx - np.floor(idx)
    return tab[i0] * (1 - frac) + tab[(i0 + 1) % 4096] * frac


def sine(freq, n, phase0=0.0):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    return np.sin(2 * np.pi * (phase0 + np.cumsum(f) / SR))


def env_adsr(n, a, d, s, r_start, r):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = np.clip((t - r_start) / max(r, 1e-6), 0, 1)
    return e * np.where(t > r_start, np.exp(-5 * rel), 1)


def lp(x, fc, order=2):
    sos = signal.butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=-1)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=-1)


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=-1)


def noise(n):
    return rng.standard_normal(n)


def fm_bell(freq, dur, ratio=3.5, index=2.4, decay=1.4):
    n = S(dur)
    t = np.arange(n) / SR
    idx = index * np.exp(-t / 0.25)
    mod = np.sin(2 * np.pi * freq * ratio * t) * idx
    car = np.sin(2 * np.pi * freq * t + mod)
    return car * np.exp(-t / decay) * np.minimum(1, t / 0.002)


def pad_note(midi, dur, bright):
    n = S(dur + 1.2)
    out = np.zeros((2, n))
    for k, (cents, pan) in enumerate([(-7, -0.6), (0, 0.0), (7, 0.6)]):
        f = mtof(midi) * 2 ** (cents / 1200)
        vib = 1 + 0.0018 * np.sin(2 * np.pi * (0.3 + 0.07 * k) * np.arange(n) / SR + k)
        x = saw(f * vib, n, phase0=rng.random())
        dark, light = lp(x, 520), lp(x, 2600)
        x = dark * (1 - bright) + light * bright
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        out += np.vstack([x * l, x * r])
    e = env_adsr(n, 0.35, 0.8, 0.85, dur, 0.9)
    return out * e / 3



def pluck(midi, dur=0.32, bright=1.0):
    n = S(dur + 0.05)
    t = np.arange(n) / SR
    x = saw(mtof(midi), n) * 0.7 + saw(mtof(midi) * 1.004, n) * 0.3
    filt_env = np.exp(-t / (0.05 + 0.08 * bright))
    x = lp(x, 900) * (1 - filt_env) + lp(x, 900 + 5200 * bright) * filt_env
    return x * np.exp(-t / 0.16) * np.minimum(1, t / 0.002)



def kick():
    n = S(0.55)
    t = np.arange(n) / SR
    f = 46 + 120 * np.exp(-t / 0.032)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.32)
    click = hp(noise(n), 3000) * np.exp(-t / 0.003) * 0.25
    return np.tanh((body + click) * 1.4) * np.minimum(1, t / 0.001)


def clap():
    n = S(0.4)
    t = np.arange(n) / SR
    e = sum(np.exp(-np.clip(t - o, 0, None) / 0.008) * (t >= o) for o in (0, 0.011, 0.023))
    e = e + 0.5 * np.exp(-np.clip(t - 0.03, 0, None) / 0.12) * (t >= 0.03)
    return bp(noise(n), 900, 2600) * e * 0.8


def hat(open_=False):
    n = S(0.3 if open_ else 0.08)
    t = np.arange(n) / SR
    return hp(noise(n), 7500) * np.exp(-t / (0.11 if open_ else 0.022))



def duck_curve(times, depth=0.7, rel=0.16):
    g = np.ones(N)
    for t in times:
        i = S(t)
        n = min(S(0.5), N - i)
        tt = np.arange(n) / SR
        g[i:i + n] = np.minimum(g[i:i + n], 1 - depth * np.exp(-tt / rel) * np.minimum(1, tt / 0.004 + 0.3))
    return g



def riser(dur):
    n = S(dur)
    t = np.arange(n) / SR
    u = t / dur
    x = noise(n)
    # Crossfade through rising bands for a sweep.
    bands = [(200, 600), (500, 1500), (1200, 3500), (3000, 9000)]
    out = np.zeros(n)
    for i, (lo, hi) in enumerate(bands):
        w = np.clip(1 - abs(u * (len(bands) - 1) - i), 0, 1)
        out += bp(x, lo, hi) * w
    tone = sine(220 * 2 ** (u * 2.5), n) * 0.15
    return (out * 0.6 + tone) * u ** 2


def impact(big=1.0):
    n = S(2.4)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.9)
    crash = lp(noise(n), 6000) * np.exp(-t / 0.5) * 0.35
    return (boom + crash) * big * np.minimum(1, t / 0.002)


def whoosh(dur, lo=300, hi=4000):
    n = S(dur)
    t = np.arange(n) / SR
    u = t / dur
    x = noise(n)
    a = bp(x, lo, lo * 3)
    c = bp(x, hi / 3, hi)
    return (a * (1 - u) + c * u) * np.sin(np.pi * u) ** 1.5



def key_click(pitch):
    n = S(0.03)
    t = np.arange(n) / SR
    return bp(noise(n), 2000 * pitch, 6000 * pitch) * np.exp(-t / 0.006)



def ir(seconds=2.6, predelay=0.02):
    n = S(seconds)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        x = rng.standard_normal(n) * np.exp(-t / (seconds / 6.5))
        x = lp(x, 7000) if ch == 0 else lp(x, 6500)
        x[: S(predelay)] = 0
        out.append(x / np.sqrt((x ** 2).sum()))
    return out



# ==== composition ====
CH = {
    "Am9": (["A3", "C4", "E4", "G4", "B4"], "A1"),
    "Fmaj7": (["F3", "A3", "C4", "G4", "A4"], "F1"),
    "Cmaj7": (["G3", "B3", "C4", "D4", "G4"], "C2"),
    "G6": (["G3", "B3", "D4", "A4", "B4"], "G1"),
    "Cmaj9": (["E3", "G3", "B3", "D4", "E4"], "C2"),
}
# (start beat, end beat, chord). The break (20-22) hangs on G6; the drop lands on F.
PROG = [(0, 4, "Am9"), (4, 8, "Fmaj7"), (8, 12, "Cmaj7"), (12, 16, "G6"), (16, 20, "Am9"),
        (20, 22, "G6"), (22, 26, "Fmaj7"), (26, 28, "G6"), (28, 36, "Cmaj9")]


def chord_at(t):
    beat = t / BEAT
    for s, e, c in PROG:
        if s <= beat < e:
            return CH[c]
    return CH[PROG[-1][2]]


# ---------------------------------------------------------------- pad
for k, (s, e, name) in enumerate(PROG):
    bright = [0.2, 0.35, 0.5, 0.6, 0.75, 0.45, 0.9, 0.9, 0.8][k]
    dur = b(e - s)
    for nn in CH[name][0]:
        place(music["pad"], pad_note(m(nn), dur, bright), b(s), gain=0.10 * (2.4 if s < 4 else 1.0), send=0.35)

# ---------------------------------------------------------------- bass (in from the bar, out in the break)
for s, e, name in PROG:
    if s < 4 or s == 20 or s >= 28:
        continue
    root = m(CH[name][1])
    n = S(b(e - s))
    tt = np.arange(n) / SR
    sub = sine(mtof(root), n) * 0.9
    mid = lp(saw(mtof(root + 12), n), 420) * 0.35
    e_ = np.minimum(1, tt / 0.01) * np.where(tt > b(e - s) - 0.06, np.clip((b(e - s) - tt) / 0.06, 0, 1), 1)
    place(music["bass"], (sub + mid) * e_, b(s), gain=0.42 if s >= 22 else 0.34)
n = S(b(8))
tt = np.arange(n) / SR
place(music["bass"], sine(mtof(m("C2")), n) * np.exp(-tt / 2.2) * np.minimum(1, tt / 0.01), b(28), gain=0.45)

# ---------------------------------------------------------------- pluck arpeggio
ARP = [0, 2, 1, 3, 2, 4, 3, 1]
for step in range(36 * 2):
    beat = step / 2
    if beat < 1 or beat >= 30:
        continue
    t = b(beat)
    notes, _ = chord_at(t)
    up = 12 if beat >= 22 else 0
    nn = m(notes[ARP[step % 8]]) + 12 + up
    bright = min(1.0, 0.3 + beat / 18)
    vel = (0.75 if step % 2 else 1.0) * (0.55 if 20 <= beat < 22 else 1.0) * (0.7 if beat < 4 else 1.0)
    place(music["pluck"], pluck(nn, bright=bright), t, gain=0.11 * vel, pan=(-0.35 if step % 2 else 0.35), send=0.25)
d = S(b(0.75))
dl = music["pluck"].copy()
echo = np.zeros_like(dl)
for k in range(1, 5):
    sh = d * k
    src = dl[::-1] if k % 2 else dl
    echo[:, sh:] += lp(src[:, : N - sh], 3000) * 0.32 ** k
music["pluck"] += echo

# ---------------------------------------------------------------- drums
K, CL, HC, HO = kick(), clap(), hat(), hat(True)
kick_times = [b(x) for x in range(4, 20)] + [b(x) for x in range(22, 28)] + [b(28)]
for t in kick_times:
    place(music["drums"], K, t, gain=0.8 if t < b(22) else 0.88)
for x in list(range(8, 20)) + list(range(22, 28)):
    if x % 2 == 1:
        place(music["drums"], CL, b(x), gain=0.4, send=0.25)
    place(music["drums"], HO, b(x + 0.5), gain=0.11, pan=0.25)
for x in np.arange(4, 28, 0.25):
    if 20 <= x < 22:
        continue
    vel = [0.5, 0.25, 0.35, 0.25][int(round(x * 4)) % 4]
    place(music["drums"], HC, b(x), gain=0.09 * vel * (0.6 if x < 8 else 1), pan=-0.3)
# Intro: quiet eighth ticks and a short lift into the bar.
for x in np.arange(1, 4, 0.5):
    place(music["drums"], HC, b(x), gain=0.05, pan=-0.3)
place(music["fx"], riser(b(1)), b(3), gain=0.18, send=0.2)
# Break: filtered heartbeat under the toggle, snare roll into the drop.
for x in (20, 21, 21.5):
    place(music["drums"], lp(K, 250), b(x), gain=0.5)
for i, x in enumerate(np.arange(21, 22, 0.125)):
    place(music["drums"], CL, b(x), gain=0.1 + 0.22 * i / 8, send=0.2)

duck = duck_curve(kick_times)
for k in ("pad", "bass", "pluck"):
    music[k] *= duck

# ---------------------------------------------------------------- transitions
place(music["fx"], riser(b(2)), b(20), gain=0.32, send=0.2)
place(music["fx"], impact(1.0), AT["offsite"], gain=0.62, send=0.5)
place(music["fx"], impact(0.7), AT["outro"], gain=0.5, send=0.6)
gap = np.ones(N)
i0, i1 = S(b(21.75)), S(b(22))
gap[i0:i1] = np.linspace(1, 0.15, i1 - i0)
for k in ("pad", "pluck", "drums"):
    music[k] *= gap

# ---------------------------------------------------------------- sound effects
def coin(base=1.0):
    """Short metallic 'paid' chime: two inharmonic FM partials."""
    a = fm_bell(mtof(m("E6")) * base, 1.2, ratio=2.76, index=1.6, decay=0.45)
    c = fm_bell(mtof(m("B6")) * base, 1.2, ratio=3.1, index=1.2, decay=0.35)
    return a + 0.6 * c


def snip(pitch=1.0, big=1.0):
    """A slice coming off the bar: a scissor tick plus a falling blip."""
    n = S(0.22)
    tt = np.arange(n) / SR
    tick = bp(noise(n), 3500, 9000) * np.exp(-tt / 0.004)
    blip = sine(900 * pitch * np.exp(-tt / 0.06) + 120, n) * np.exp(-tt / 0.07)
    thunk = sine(110 * np.exp(-tt / 0.08) + 50, n) * np.exp(-tt / 0.09) * big
    return tick * 0.6 + blip * 0.5 + thunk * 0.8


# The order is paid: chime on the pulses in the hook.
place(sfx, coin(), b(0.5), gain=0.09, send=0.5)
place(sfx, coin(1.0) * 0.6, b(2), gain=0.07, send=0.5)
place(sfx, whoosh(0.6, 400, 6000), AT["hookOut"], gain=0.2, send=0.3)
# Bar stretches out of the dot.
n = S(b(1.6))
tt = np.arange(n) / SR
place(sfx, sine(300 + 900 * (tt / tt[-1]) ** 0.5, n) * np.exp(-tt / 0.5) * np.minimum(1, tt / 0.02), AT["barGrow"], gain=0.05, send=0.4)
# Each cut steps down a scale: money leaving.
steps = [1.0, 0.94, 0.89, 0.84, 0.75, 0.71, 0.67]
for i, c in enumerate(EV["cuts"]):
    place(sfx, snip(steps[i], 0.6 + 0.08 * i), c, gain=0.32, pan=0.3 - 0.1 * i)
    place(sfx, key_click(1.1), c + 0.06, gain=0.1)
# USD -> CNY flip.
place(sfx, hp(whoosh(0.5, 1500, 9000), 1200), AT["flip"] - 0.08, gain=0.14, send=0.3)
place(sfx, coin(1.122), AT["flip"] + 0.02, gain=0.06, send=0.5)
# Brackets draw.
for t in (AT["etsyBracket"], AT["costBracket"]):
    place(sfx, hp(whoosh(0.35, 2000, 8000), 1500), t, gain=0.08)
# Result: bright chime.
for k, nn in enumerate(["A5", "C6", "E6"]):
    place(sfx, fm_bell(mtof(m(nn)), 1.8, ratio=2.0, index=1.0, decay=0.7), AT["result"] + 0.05 * k, gain=0.06, send=0.5)
# Toggle appears and ticks on the beat; flips on the drop.
for x in (20, 20.5, 21, 21.5):
    place(sfx, key_click(1.5), b(x), gain=0.12)
place(sfx, snip(0.6, 1.4), AT["offsite"], gain=0.4, pan=0)
place(sfx, key_click(0.9), AT["offsite"], gain=0.5)
place(sfx, whoosh(0.7, 300, 3000), AT["compare"], gain=0.15, send=0.3)
# End card.
place(sfx, hp(whoosh(0.8, 3000, 14000), 4000), AT["endTitle"], gain=0.14, send=0.5)
for i, t in enumerate(AT["features"]):
    place(sfx, pluck(m(["E5", "G5", "A5"][i]), dur=0.5, bright=1.0), t, gain=0.11, send=0.4)
for k, nn in enumerate(["C6", "G6", "E7"]):
    place(sfx, fm_bell(mtof(m(nn)), 2.2, ratio=3.0, index=1.0, decay=0.9), AT["url"] + 0.06 * k, gain=0.06, send=0.6)

# ---------------------------------------------------------------- reverb + mix
IR = ir()
wet = np.vstack([signal.fftconvolve(verb_send[c], IR[c])[:N] for c in range(2)])
wet = hp(wet, 180)
mix = sum(music[k] for k in music) + sfx + wet * 0.55
fade = S(0.6)
mix[:, -fade:] *= np.linspace(1, 0, fade) ** 2
mix[:, : S(0.004)] *= np.linspace(0, 1, S(0.004))
mix /= np.abs(mix).max()
mix = np.tanh(mix * 1.25) / np.tanh(1.25)
mix *= 0.89
wavfile.write("mix_a.wav", SR, (mix.T * 32767).astype(np.int16))
print("wrote mix_a.wav", mix.shape, "peak", float(np.abs(mix).max()))
