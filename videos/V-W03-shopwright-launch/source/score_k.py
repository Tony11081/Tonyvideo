"""Score for V-W03 (launch film), written as MIDI and played with the FluidR3 GM
soundfont (MIT licence) through FluidSynth. Composition is original.

    python3 score_k.py A   -> score_A.wav  (piano + strings + timpani)
    python3 score_k.py B   -> score_B.wav  (electric piano + pads + clean drums)

Timing comes from eventsK.json (timelineK.js): 80 BPM, 40 beats = 30 s.
"""
import json
import subprocess
import sys

import mido
import numpy as np
from scipy.io import wavfile

V = sys.argv[1] if len(sys.argv) > 1 else "A"
EV = json.load(open("eventsK.json"))
BEAT = EV["BEAT"]
SR = 48000
TPB = 480
SIL_B, HIT_B = 32.5, 33.0

NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
def m(s):
    return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]

ev = []  # (beat, priority, message)
def note(ch, beat, dur, pitch, vel):
    p = m(pitch) if isinstance(pitch, str) else pitch
    ev.append((beat, 1, mido.Message("note_on", channel=ch, note=p, velocity=int(max(1, min(127, vel))))))
    ev.append((beat + dur, 0, mido.Message("note_off", channel=ch, note=p, velocity=0)))
def cc(ch, beat, num, val):
    ev.append((beat, 0, mido.Message("control_change", channel=ch, control=num, value=int(max(0, min(127, val))))))
def ramp(ch, b0, b1, v0, v1, num=11, steps=24):
    for k in range(steps + 1):
        cc(ch, b0 + (b1 - b0) * k / steps, num, v0 + (v1 - v0) * k / steps)
def prog(ch, p):
    ev.append((0, -1, mido.Message("program_change", channel=ch, program=p)))

PIANO, STR, LOW, TIMP, BELL, CHOIR, DR = 0, 1, 2, 3, 4, 5, 9
if V == "A":
    prog(PIANO, 0); prog(STR, 48); prog(LOW, 42); prog(TIMP, 47); prog(BELL, 8); prog(CHOIR, 52)
else:
    prog(PIANO, 4); prog(STR, 89); prog(LOW, 38); prog(TIMP, 116); prog(BELL, 11); prog(CHOIR, 91)
for ch in range(6):
    cc(ch, 0, 7, 100); cc(ch, 0, 91, 70 if V == "A" else 55); cc(ch, 0, 93, 20)
cc(PIANO, 0, 10, 60); cc(STR, 0, 10, 64); cc(LOW, 0, 10, 58); cc(BELL, 0, 10, 80)

VOICE = {
    "Am": ["A2", "E3", "A3", "C4", "E4"], "F": ["F2", "C3", "A3", "C4", "F4"],
    "C": ["C3", "G3", "C4", "E4", "G4"], "G": ["G2", "D3", "B3", "D4", "G4"],
    "Cmaj9": ["C2", "G2", "E3", "B3", "D4", "G4", "E5"],
}
ARP = {
    "Am": ["A2", "E3", "A3", "C4", "E4", "C4", "A3", "E3"], "F": ["F2", "C3", "F3", "A3", "C4", "A3", "F3", "C3"],
    "C": ["C3", "G3", "C4", "E4", "G4", "E4", "C4", "G3"], "G": ["G2", "D3", "G3", "B3", "D4", "B3", "G3", "D3"],
}
ROOT = {"Am": "A1", "F": "F1", "C": "C2", "G": "G1"}

# ---------------- open (0-5): one light in the dark
for p in VOICE["Am"][:4]:
    note(STR, 0, 4.9, p, 60)
ramp(STR, 0, 4.9, 55, 105)
note(BELL, EV["at"]["dotOn"] / BEAT, 3, "E6", 90)
for b_, p, v in [(2.0, "A4", 66), (3.0, "E5", 70), (4.0, "C5", 74)]:
    note(PIANO, b_, 1.6, p, v)
note(TIMP, 4.0, 1.0, "A1", 30); note(TIMP, 4.25, 1.0, "A1", 40); note(TIMP, 4.5, 1.0, "A1", 55); note(TIMP, 4.75, 1.0, "A1", 70)

# ---------------- name (5-11): the hit, then the sweep
note(TIMP, 5, 2, "A1", 125); note(DR, 5, 1, 36, 115); note(DR, 5, 2, 49, 80)
note(PIANO, 5, 3, "A1", 115); note(PIANO, 5, 3, "A2", 105); note(PIANO, 5, 3, "E3", 80)
for p in VOICE["Am"]:
    note(STR, 5, 3, p, 95)
for p in VOICE["F"]:
    note(STR, 8, 3, p, 88)
ramp(STR, 5, 10.8, 110, 70)
for i, p in enumerate(["A3", "E4", "A4", "C5", "E5", "C5"]):
    note(PIANO, 5.5 + i * 0.5, 1.2, p, 58 + 4 * i)
for i, p in enumerate(["F3", "C4", "F4", "A4", "C5", "A4"]):
    note(PIANO, 8 + i * 0.5, 1.2, p, 62)
note(BELL, EV["at"]["nameSweepEnd"] / BEAT, 2, "E6", 64); note(BELL, EV["at"]["nameSweepEnd"] / BEAT + 0.25, 2, "A6", 58)

# ---------------- chapters (11-31): arpeggio + melody + pulse
SECS = [(11, 16, "Am"), (16, 20, "F"), (20, 26, "C"), (26, 31, "G")]
MEL = [  # beat, note, length
    (11.5, "E5", 1.5), (13, "C5", 1), (14, "D5", 1), (15, "E5", 1),
    (16, "F5", 2), (18, "E5", 1), (19, "C5", 1),
    (20, "G5", 2), (22, "E5", 1), (23, "D5", 1), (24, "C5", 1), (25, "E5", 1),
    (26, "D5", 2), (28, "B4", 1), (29, "D5", 1), (30, "G5", 1),
]
for s, e, c in SECS:
    for k in range(int((e - s) * 2)):
        bb = s + k * 0.5
        note(PIANO, bb, 0.6, ARP[c][k % 8], 52 + (8 if k % 4 == 0 else 0) + (bb - 11) * 0.6)
    for p in VOICE[c]:
        note(STR, s, e - s, p, 72)
    for k in range(int((e - s) * 2)):
        bb = s + k * 0.5
        note(LOW, bb, 0.3, ROOT[c] if V == "B" else m(ROOT[c]) + 12, 50 + (bb - 11) * 2.2)
    note(TIMP, s, 1.5, ROOT[c] if c != "C" else "C2", 92)
for b_, p, l in MEL:
    note(PIANO, b_, l * 0.95, p, 86 + (b_ - 11) * 0.5)
ramp(STR, 11, 31, 55, 105)
for x in np.arange(16, 31, 1.0):
    note(DR, x, 0.5, 36, 58 + (x - 16) * 2)
if V == "B":
    for x in np.arange(11, 16, 1.0):
        note(DR, x, 0.5, 36, 60)
    for x in np.arange(16, 31, 0.5):
        note(DR, x, 0.25, 42, 50 if x % 1 else 38)
    for x in np.arange(21, 31, 2.0):
        note(DR, x, 0.5, 39, 70)
    for x in np.arange(26.5, 31, 1.0):
        note(DR, x, 0.5, 46, 45)
else:
    for x in (20, 26):
        note(DR, x, 2, 49, 55)

# ---------------- montage (31-32.5): three stabs and a roll
for x in (31, 31.5, 32):
    for p in ["G1", "G2", "D3", "G3"]:
        note(PIANO, x, 0.45, p, 118)
    for p in VOICE["G"]:
        note(STR, x, 0.45, p, 115)
    note(TIMP, x, 0.45, "G1", 120)
for i, x in enumerate(np.arange(31, 32.5, 0.125)):
    note(DR, x, 0.12, [41, 43, 45, 47][i % 4], 70 + 4 * i)
ramp(STR, 31, 32.45, 100, 127, steps=12)

# ---------------- end (33-40): the big C
note(TIMP, 33, 3, "C2", 127); note(DR, 33, 2, 36, 127); note(DR, 33, 4, 49, 115); note(DR, 33, 4, 57, 100)
for p in ["C1", "C2", "G2", "C3"]:
    note(PIANO, 33, 5, p, 120)
for p in VOICE["Cmaj9"]:
    note(STR, 33, 6.8, p, 105)
ramp(STR, 33, 39.8, 120, 35)
for p in ["C4", "E4", "G4"]:
    note(CHOIR, 33.5, 6, p, 70)
ramp(CHOIR, 33.5, 39.8, 90, 30)
note(BELL, EV["at"]["endLand"] / BEAT, 3, "G6", 80)
for i, p in enumerate(["C4", "E4", "G4", "B4", "D5"]):
    note(PIANO, EV["at"]["endLine"] / BEAT + i * 0.12, 4, p, 62)
for i, p in enumerate(["C6", "E6", "G6", "C7"]):
    note(BELL, EV["at"]["url"] / BEAT + i * 0.25, 3, p, 70 - 5 * i)
# piano sustain pedal through the end
cc(PIANO, 33, 64, 127); cc(PIANO, 39.9, 64, 0)

# ---------------- write MIDI
mid = mido.MidiFile(ticks_per_beat=TPB)
tr = mido.MidiTrack(); mid.tracks.append(tr)
tr.append(mido.MetaMessage("set_tempo", tempo=int(BEAT * 1e6), time=0))
ev.sort(key=lambda e: (e[0], e[1]))
now = 0
for bb, _, msg in ev:
    tk = int(round(bb * TPB))
    tr.append(msg.copy(time=max(0, tk - now))); now = max(now, tk)
mid.save(f"score_{V}.mid")
subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.5", "-r", str(SR), "-o", "synth.reverb.room-size=0.82", "-o", "synth.reverb.width=0.9",
                "-o", "synth.reverb.level=0.6", "-F", f"score_{V}_raw.wav", "/usr/share/sounds/sf2/FluidR3_GM.sf2", f"score_{V}.mid"], check=True)

# ---------------- mix with the UI sound effects, silence before the hit, master
sr, x = wavfile.read(f"score_{V}_raw.wav")
x = x.astype(np.float64) / 32768.0
x = x.T if x.ndim == 2 else np.vstack([x, x])
N = int(SR * EV["duration"])
if x.shape[1] < N:
    x = np.pad(x, ((0, 0), (0, N - x.shape[1])))
x = x[:, :N]
sfx = np.load("sfx_k.npy").astype(np.float64)[:, :N]
S = lambda t: int(round(t * SR))
sil, hit = SIL_B * BEAT, HIT_B * BEAT
g = np.ones(N)
g[S(sil) - S(0.04):S(sil)] = np.linspace(1, 0, S(0.04)) ** 2
g[S(sil):S(hit)] = 0
x *= g
mix = x / (np.abs(x).max() + 1e-9) + sfx * (0.55 if V == "A" else 0.7)
fade = S(1.4)
mix[:, -fade:] *= np.linspace(1, 0, fade) ** 2
mix /= np.abs(mix).max()
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= 0.89
wavfile.write(f"score_{V}_pre.wav", SR, (mix.T * 32767).astype(np.int16))
print("ok", V)
