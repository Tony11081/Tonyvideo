"""Original score for V-W03, the launch-film cut (30 s, 80 BPM, 24 fps picture).

Cinematic hybrid, fully synthesised: low drone, braams and booms on the
chapter cuts, a 16th-note pulse under the chapters, one beat of silence,
then the final hit. SFX come from eventsK.json (timelineK.js).

    python3 music_k.py   -> mix_k.wav
"""
import json
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
EV = json.load(open("eventsK.json"))
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
    "Am9": ["A3", "C4", "E4", "G4", "B4"], "Fmaj7": ["F3", "A3", "C4", "G4", "A4"],
    "Cmaj7": ["G3", "B3", "C4", "D4", "G4"], "G6": ["G3", "B3", "D4", "A4", "B4"], "Cmaj9": ["E3", "G3", "B3", "D4", "E4"],
}
ROOT = {"Am9": "A1", "Fmaj7": "F1", "Cmaj7": "C2", "G6": "G1", "Cmaj9": "C2"}
PROG = [(0, 11, "Am9"), (11, 16, "Am9"), (16, 20, "Fmaj7"), (20, 26, "Cmaj7"), (26, 31, "G6"), (31, 33, "G6"), (33, 40, "Cmaj9")]
HIT = AT["hit"]
SIL = AT["silence"]


def chord_at(t):
    beat = t / BEAT
    for s, e, c in PROG:
        if s <= beat < e:
            return c
    return PROG[-1][2]


def braam(notes, dur, bright=1.0):
    """Detuned low saws with a slow filter swell — the trailer 'braam'."""
    n = S(dur)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for nn in notes:
        for d in (-0.12, 0.0, 0.11):
            out += saw(mtof(m(nn)) * 2 ** (d / 12), n, phase0=rng.random())
    fc = 180 + 1800 * bright * np.exp(-tt / 0.9) * np.minimum(1, tt / 0.08)
    # time-varying LP in blocks
    y = np.zeros(n)
    blk = 1024
    for k in range(0, n, blk):
        y[k:k + blk] = lp(out[max(0, k - 2048):k + blk], float(fc[k]))[-min(blk, n - k):]
    env = np.minimum(1, tt / 0.03) * np.exp(-tt / (dur * 0.45))
    return np.tanh(y * env * 0.5)


# ---------------------------------------------------------------- drone + air (cold open to the silence)
n = S(SIL)
tt = np.arange(n) / SR
drone = sine(mtof(m("A1")), n) * 0.7 + lp(saw(mtof(m("A1")), n), 300) * 0.3 + lp(saw(mtof(m("E2")) * 1.002, n), 260) * 0.2
swell = np.minimum(1, tt / 2.5) * (0.6 + 0.4 * np.clip(tt / SIL, 0, 1))
place(music["bass"], drone * swell, 0, gain=0.22)
air = bp(noise(n), 1500, 7000) * np.minimum(1, tt / 3) * 0.06
place(music["fx"], np.vstack([air, np.roll(air, 977)]), 0, gain=0.6)

# ---------------------------------------------------------------- pads by section
for s_, e_, name in PROG:
    if s_ < 5:
        continue
    dur = b(e_ - s_)
    if s_ == 31:
        dur = SIL - b(31)
    bright = {5: 0.25, 11: 0.4, 16: 0.55, 20: 0.7, 26: 0.85, 31: 0.9, 33: 0.75}[s_]
    for nn in CH[name]:
        place(music["pad"], pad_note(m(nn), dur, bright), b(s_), gain=0.085 * (1.4 if s_ == 33 else 1.0), send=0.4)

# ---------------------------------------------------------------- 16th pulse under the chapters
PAT = [0, 2, 4, 2, 1, 3, 4, 3]
for k in range(int((31 - 11) * 4)):
    beat = 11 + k / 4
    t = b(beat)
    if t >= SIL:
        break
    notes = CH[chord_at(t)]
    nn = m(notes[PAT[k % 8]]) + 12
    vel = (1.0 if k % 4 == 0 else 0.6) * (0.5 + 0.5 * min(1, (beat - 11) / 12))
    place(music["pluck"], pluck(nn, dur=0.18, bright=0.35 + 0.4 * min(1, (beat - 11) / 18)), t, gain=0.075 * vel, pan=(-0.3 if k % 2 else 0.3), send=0.3)
d = S(b(0.75))
dl = music["pluck"].copy()
echo = np.zeros_like(dl)
for k in range(1, 4):
    sh = d * k
    src = dl[::-1] if k % 2 else dl
    echo[:, sh:] += lp(src[:, : N - sh], 2500) * 0.28 ** k
music["pluck"] += echo

# bass on the root under the pulse
for s_, e_, name in PROG:
    if s_ < 11 or s_ >= 33:
        continue
    t0 = b(s_)
    t1 = min(b(e_), SIL)
    nn = S(t1 - t0)
    tq = np.arange(nn) / SR
    x = sine(mtof(m(ROOT[name])), nn) * 0.8 + lp(saw(mtof(m(ROOT[name]) + 12), nn), 380) * 0.3
    x *= np.minimum(1, tq / 0.02) * np.clip((t1 - t0 - tq) / 0.05, 0, 1)
    place(music["bass"], x, t0, gain=0.3)

# ---------------------------------------------------------------- drums: heartbeat, then the montage toms
K, CL, HC, HO = kick(), clap(), hat(), hat(True)
kick_times = [b(x) for x in np.arange(11, 31, 1.0)]
for i, t in enumerate(kick_times):
    place(music["drums"], K, t, gain=0.55 + 0.25 * i / len(kick_times))
for x in np.arange(16, 31, 0.5):
    place(music["drums"], HC, b(x), gain=0.05 if x % 1 else 0.035, pan=-0.25)
for x in np.arange(20, 31, 2):
    place(music["drums"], CL, b(x + 1), gain=0.22, send=0.35)


def tom(f0=90):
    n = S(0.7)
    tq = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(f0 + f0 * 1.2 * np.exp(-tq / 0.04)) / SR) * np.exp(-tq / 0.25)
    skin = bp(noise(n), 200, 1200) * np.exp(-tq / 0.03) * 0.4
    return np.tanh((body + skin) * 1.6)


for i, x in enumerate(np.arange(31, 32.5, 0.25)):
    place(music["drums"], tom(70 + 6 * (i % 3)), b(x), gain=0.45 + 0.05 * i, send=0.3)
duck = duck_curve(kick_times, depth=0.45, rel=0.2)
for k in ("pad", "pluck"):
    music[k] *= duck

# ---------------------------------------------------------------- hits
place(music["fx"], riser(b(1.8)), b(3.2), gain=0.25, send=0.3)
place(music["fx"], impact(0.8), b(5), gain=0.5, send=0.6)
place(music["fx"], braam(["A1", "E2", "A2"], 3.2, 0.7), b(5), gain=0.5, send=0.4)
for c in ("title", "tags", "profit", "pipe"):
    t = AT["chapter"][c]
    place(music["fx"], impact(0.45), t, gain=0.42, send=0.5)
    place(music["fx"], braam([{"title": "A1", "tags": "F1", "profit": "C2", "pipe": "G1"}[c]] * 1 + ["E2"], 1.6, 0.5), t, gain=0.3, send=0.4)
place(music["fx"], riser(SIL - b(31)), b(31), gain=0.35, send=0.2)
place(music["fx"], impact(1.2), HIT, gain=0.75, send=0.7)
place(music["fx"], braam(["C1", "G1", "C2", "E2"], 5.0, 1.0), HIT, gain=0.62, send=0.5)
n = S(5.0)
tq = np.arange(n) / SR
place(music["bass"], sine(mtof(m("C1")) * 2, n) * np.exp(-tq / 2.6) * np.minimum(1, tq / 0.01), HIT, gain=0.4)

# ---------------------------------------------------------------- sound effects from the picture
place(sfx, fm_bell(mtof(m("A6")), 2.0, ratio=2.0, index=0.8, decay=0.8), AT["dotOn"], gain=0.05, send=0.7)
place(sfx, hp(whoosh(AT["nameSweepEnd"] - AT["nameSweep"], 2000, 12000), 2500), AT["nameSweep"], gain=0.12, send=0.5)
for i in range(0, 74, 2):
    t = EV["typeT0"] + (EV["typeT1"] - EV["typeT0"]) * i / 74
    nq = S(0.03)
    tq = np.arange(nq) / SR
    place(sfx, bp(noise(nq), 2500, 7000) * np.exp(-tq / 0.005), t, gain=0.08, pan=0.2 * np.sin(i))
place(sfx, fm_bell(mtof(m("E6")), 1.2), EV["typeT1"] + 0.2, gain=0.05, send=0.5)
pent = [m(x) for x in ["A4", "C5", "D5", "E5", "G5"]]
for i, t in enumerate(EV["tags"]):
    f = mtof(pent[i % 5] + 12 * (i // 5))
    nq = S(0.14)
    tq = np.arange(nq) / SR
    place(sfx, sine(f * (1 + 0.5 * np.exp(-tq / 0.012)), nq) * np.exp(-tq / 0.05), t, gain=0.1, pan=-0.4 + 0.8 * i / 12, send=0.25)


def snip(pitch=1.0, big=1.0):
    nq = S(0.22)
    tq = np.arange(nq) / SR
    tick = bp(noise(nq), 3500, 9000) * np.exp(-tq / 0.004)
    blip = sine(900 * pitch * np.exp(-tq / 0.06) + 120, nq) * np.exp(-tq / 0.07)
    thunk = sine(110 * np.exp(-tq / 0.08) + 50, nq) * np.exp(-tq / 0.09) * big
    return tick * 0.6 + blip * 0.5 + thunk * 0.8


for i, t in enumerate(EV["cuts"]):
    place(sfx, snip([1.0, 0.94, 0.89, 0.84, 0.75, 0.71, 0.67][i], 0.7), t, gain=0.26, pan=0.3 - 0.1 * i, send=0.2)
for k, nn in enumerate(["A5", "C6", "E6"]):
    place(sfx, fm_bell(mtof(m(nn)), 1.8, ratio=2.0, index=1.0, decay=0.7), AT["result"] + 0.05 * k, gain=0.05, send=0.5)
for i, t in enumerate(EV["pipe"]):
    place(sfx, pluck(m(["A4", "C5", "D5", "E5", "G5", "A5", "C6"][i]), dur=0.5, bright=1.0), t, gain=0.1, pan=-0.2 + 0.4 * i / 6, send=0.45)
for t in AT["flashes"]:
    place(sfx, whoosh(0.3, 600, 8000), t - 0.05, gain=0.18, send=0.2)
place(sfx, fm_bell(mtof(m("G6")), 2.0, ratio=3.0, index=1.0, decay=0.9), AT["endLand"], gain=0.05, send=0.6)
for k, nn in enumerate(["C6", "G6", "E7"]):
    place(sfx, fm_bell(mtof(m(nn)), 2.4, ratio=3.0, index=1.0, decay=1.0), AT["url"] + 0.06 * k, gain=0.05, send=0.6)

# ---------------------------------------------------------------- the silence before the hit
gap = np.ones(N)
i0, i1 = S(SIL), S(HIT)
gap[i0:i1] = 0.0
gap[i0 - S(0.03):i0] = np.linspace(1, 0, S(0.03))
for k in music:
    music[k] *= gap
sfx *= gap
verb_send *= gap

# ---------------------------------------------------------------- reverb + mix
IR = ir(3.4)
wet = np.vstack([signal.fftconvolve(verb_send[c], IR[c])[:N] for c in range(2)])
wet = hp(wet, 160)
wet[:, S(SIL):S(SIL) + S(0.12)] *= np.linspace(1, 0, S(0.12)) ** 2  # the tail dies quickly
wet[:, S(SIL) + S(0.12):S(HIT)] *= 0.0  # true silence before the hit
mix = sum(music[k] for k in music) + sfx + wet * 0.6
fade = S(1.2)
mix[:, -fade:] *= np.linspace(1, 0, fade) ** 2
mix[:, : S(0.004)] *= np.linspace(0, 1, S(0.004))
mix /= np.abs(mix).max()
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix *= 0.89
wavfile.write("mix_k.wav", SR, (mix.T * 32767).astype(np.int16))
print("wrote mix_k.wav", mix.shape)
