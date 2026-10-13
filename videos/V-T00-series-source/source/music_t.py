"""Music + SFX for the 15 s single-tool series (filmT.html).

One original score for the whole series (series identity), written as MIDI and
played with the FluidR3 GM soundfont (MIT) through FluidSynth; each episode
gets its own UI sound effects on the picture's beats.

    python3 music_t.py            -> series_score.wav, mix_t_<ep>.wav for every episode
120 BPM, 30 beats = 15 s.
"""
import subprocess

import mido
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
BEAT = 0.5
DUR = 15.0
N = int(SR * DUR)
TPB = 480
rng = np.random.default_rng(11)
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
def m(s):
    return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]

# ------------------------------------------------------------------ score (MIDI)
ev = []
def note(ch, beat, dur, p, vel):
    p = m(p) if isinstance(p, str) else p
    ev.append((beat, 1, mido.Message("note_on", channel=ch, note=p, velocity=int(max(1, min(127, vel))))))
    ev.append((beat + dur, 0, mido.Message("note_off", channel=ch, note=p, velocity=0)))
def cc(ch, beat, num, val):
    ev.append((beat, 0, mido.Message("control_change", channel=ch, control=num, value=int(max(0, min(127, val))))))
EPN, PAD, BASS, VIB, DR = 0, 1, 2, 3, 9
for ch, p in ((EPN, 4), (PAD, 89), (BASS, 38), (VIB, 11)):
    ev.append((0, -1, mido.Message("program_change", channel=ch, program=p)))
    cc(ch, 0, 7, 100); cc(ch, 0, 91, 60); cc(ch, 0, 93, 25)
cc(PAD, 0, 7, 82); cc(BASS, 0, 7, 92); cc(VIB, 0, 10, 80); cc(EPN, 0, 10, 52)

PROG = [(0, 4, "Am"), (4, 8, "F"), (8, 12, "C"), (12, 16, "G"), (16, 20, "Am"), (20, 22, "F"), (22, 24, "G"), (24, 30, "C")]
VOICE = {"Am": ["A3", "C4", "E4", "G4"], "F": ["F3", "A3", "C4", "E4"], "C": ["C4", "E4", "G4", "B4"], "G": ["G3", "B3", "D4", "A4"]}
ARP = {"Am": ["A3", "E4", "A4", "C5", "E5", "C5", "A4", "E4"], "F": ["F3", "C4", "F4", "A4", "C5", "A4", "F4", "C4"],
       "C": ["C4", "G4", "C5", "E5", "G5", "E5", "C5", "G4"], "G": ["G3", "D4", "G4", "B4", "D5", "B4", "G4", "D4"]}
ROOT = {"Am": "A1", "F": "F1", "C": "C2", "G": "G1"}
for s, e, c in PROG:
    end = min(e, 29.5)
    for p in VOICE[c]:
        note(PAD, s, end - s, p, 70 if s < 24 else 82)
    if s < 24:
        for k in range(int((e - s) * 2)):
            bb = s + k * 0.5
            note(EPN, bb, 0.45, ARP[c][k % 8], 66 if k % 2 == 0 else 54)
    if 4 <= s < 24:
        for k in range(int((e - s) * 2)):
            note(BASS, s + k * 0.5, 0.4, ROOT[c], 84 if k % 2 == 0 else 66)
# the dot's "paid" pulses in the hook
note(VIB, 0.5, 2, "E6", 72); note(VIB, 2, 2, "A6", 60)
# a light melody on vibraphone under the second half of the explanation
for b_, p, l in [(16, "E5", 1), (17, "G5", 1), (18, "A5", 1.5), (20, "C6", 1), (21, "A5", 1), (22, "G5", 1), (23, "D5", 1)]:
    note(VIB, b_, l, p, 66)
# drums
for x in np.arange(4, 24, 1.0):
    note(DR, x, 0.4, 36, 92)
for x in np.arange(4, 24, 0.5):
    note(DR, x, 0.2, 42, 52 if x % 1 else 40)
for x in np.arange(9, 24, 2.0):
    note(DR, x, 0.4, 39, 78)
for i, x in enumerate(np.arange(23, 24, 0.125)):
    note(DR, x, 0.1, 38, 50 + 8 * i)
# CTA: the C chord lands with a crash, then rings out
note(DR, 24.2, 3, 49, 96); note(DR, 24.2, 0.5, 36, 112)
for p in ["C2", "C3", "G3", "C4", "E4", "G4"]:
    note(EPN, 24.2, 4.5, p, 92)
note(BASS, 24.2, 4, "C1", 96)
for i, p in enumerate(["C6", "E6", "G6", "C7"]):
    note(VIB, 26.6 + i * 0.25, 2.5, p, 70 - 6 * i)
cc(EPN, 24.2, 64, 127); cc(EPN, 29.8, 64, 0)

mid = mido.MidiFile(ticks_per_beat=TPB)
tr = mido.MidiTrack(); mid.tracks.append(tr)
tr.append(mido.MetaMessage("set_tempo", tempo=int(BEAT * 1e6), time=0))
ev.sort(key=lambda e: (e[0], e[1]))
now = 0
for bb, _, msg in ev:
    tk = int(round(bb * TPB)); tr.append(msg.copy(time=max(0, tk - now))); now = max(now, tk)
mid.save("series_score.mid")
subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.5", "-r", str(SR), "-o", "synth.reverb.room-size=0.7", "-o", "synth.reverb.level=0.5",
                "-F", "series_score_raw.wav", "/usr/share/sounds/sf2/FluidR3_GM.sf2", "series_score.mid"], check=True)
sr, x = wavfile.read("series_score_raw.wav")
x = (x.astype(np.float64) / 32768.0).T
x = np.pad(x, ((0, 0), (0, max(0, N - x.shape[1]))))[:, :N]
x /= np.abs(x).max()
fade = int(SR * 1.2)
x[:, -fade:] *= np.linspace(1, 0, fade) ** 2

# ------------------------------------------------------------------ UI sound effects
def S(t):
    return int(round(t * SR))
def bp(z, lo, hi):
    return signal.sosfilt(signal.butter(2, [lo, hi], "band", fs=SR, output="sos"), z)
def sine(f, n):
    f = np.broadcast_to(np.asarray(f, float), (n,)); return np.sin(2 * np.pi * np.cumsum(f) / SR)
def click(p=1.0, n=0.03):
    k = S(n); t = np.arange(k) / SR; return bp(rng.standard_normal(k), 2000 * p, 6500 * p) * np.exp(-t / 0.006)
def pop(f):
    k = S(0.14); t = np.arange(k) / SR; return sine(f * (1 + 0.5 * np.exp(-t / 0.012)), k) * np.exp(-t / 0.05)
def chime(f):
    k = S(1.2); t = np.arange(k) / SR; return (np.sin(2 * np.pi * f * t + 1.2 * np.exp(-t / .2) * np.sin(2 * np.pi * f * 2 * t)) * np.exp(-t / 0.4))
def buzz():
    k = S(0.22); t = np.arange(k) / SR; z = signal.sawtooth(2 * np.pi * 150 * t) * np.exp(-t / 0.08); return signal.sosfilt(signal.butter(2, 1800, "low", fs=SR, output="sos"), z)
def whoosh(d, lo=400, hi=5000):
    k = S(d); t = np.arange(k) / SR; u = t / d; z = rng.standard_normal(k)
    return (bp(z, lo, lo * 3) * (1 - u) + bp(z, hi / 3, hi) * u) * np.sin(np.pi * u) ** 1.5
def thunk():
    k = S(0.2); t = np.arange(k) / SR; return sine(110 * np.exp(-t / .07) + 50, k) * np.exp(-t / .09)
def place(bus, z, t, g=1.0):
    i = S(t); n = min(len(z), N - i)
    if n > 0:
        bus[i:i + n] += z[:n] * g
b = lambda v: v * BEAT
pent = [m(q) for q in ["A5", "C6", "D6", "E6", "G6", "A6"]]
def f(mn):
    return 440 * 2 ** ((mn - 69) / 12)

def sfx_for(ep):
    z = np.zeros(N)
    place(z, whoosh(0.5), b(3) - .05, .25)          # hook lifts away
    place(z, whoosh(0.45, 600, 7000), b(23.6), .22)  # into the CTA
    place(z, bp(rng.standard_normal(S(.6)), 3000, 9000) * np.hanning(S(.6)) * .5, b(26.6) + .6, .12)  # url sheen
    if ep == "tags":
        times = [b(4.5 + i * .5) if i < 7 else b(8 + (i - 7) * .5) for i in range(13)]
        for i, t in enumerate(times):
            place(z, pop(f(pent[i % 6]) / (1 if i < 7 else 1.12)), t, .22)
        for t in (b(11), b(12)):
            place(z, buzz(), t, .2)
        for t in (b(14), b(15)):
            place(z, chime(f(m("E6"))), t, .08)
        for i in range(3):
            place(z, click(1.3), b(16.5) + i * .18, .25)
    if ep == "title":
        for i in range(0, 74, 2):
            place(z, click(0.9 + 0.3 * ((i * 7) % 5) / 5), b(4.5) + (b(9.5) - b(4.5)) * i / 74, .18)
        place(z, whoosh(.4, 2000, 9000), b(11), .15)
        place(z, chime(f(m("A6"))), b(13), .08)
        for i in range(2):
            place(z, click(1.3), b(14) + i * .2, .25)
        for i in range(6):
            place(z, buzz() * .5, b(17.2) + i * .12, .12)
    if ep == "ship":
        place(z, thunk(), b(3.5), .4)
        for i in range(3):
            place(z, click(1.2), b(4.5) + i * .2, .2)
        for i in range(3):
            place(z, click(1.0), b(5.5) + i * b(1.1), .25)
        place(z, pop(f(m("E6"))), b(7.7), .2)
        for i in range(2):
            place(z, whoosh(.35, 800, 5000), b(11.7) + i * .25, .12)
        place(z, chime(f(m("G6"))), b(13.5), .09)
        place(z, chime(f(m("C7"))), b(17.5), .09)
    if ep == "partner":
        for i, t in enumerate([4.5, 6.5, 8.5, 10.5, 12.5]):
            place(z, pop(f(pent[i])), b(t), .22); place(z, click(1.1), b(t) + .03, .15)
        place(z, chime(f(m("E6"))), b(12.5) + .3, .09)
        place(z, buzz(), b(17.5), .18)
        place(z, click(1.3), b(20), .25)
    if ep == "ai":
        place(z, click(.8, .05), b(5.5), .45); place(z, click(.8, .05), b(11.5), .45)
        for i in range(0, 62, 2):
            place(z, click(0.9 + 0.3 * ((i * 7) % 5) / 5), b(12.2) + (b(15.5) - b(12.2)) * i / 62, .16)
        place(z, chime(f(m("E6"))), b(15.6), .07)
        place(z, chime(f(m("A6"))), b(18.3), .08)
    return z

for ep in ["tags", "title", "ship", "partner", "ai"]:
    z = sfx_for(ep)
    mix = x * 0.8 + np.vstack([z, np.roll(z, 160)])
    mix /= np.abs(mix).max()
    mix = np.tanh(mix * 1.05) / np.tanh(1.05) * 0.89
    wavfile.write(f"mix_t_{ep}.wav", SR, (mix.T * 32767).astype(np.int16))
print("ok")
