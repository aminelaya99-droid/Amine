#!/usr/bin/env python3
"""Original background track for a product reel, synthesised from scratch.

8 bars at 109.09 BPM (one bar = 2.2 s, one scene of the reel), so every cut
lands on a downbeat and the track loops with the video. Am - F - C - G twice.
Kick, clap, hats, sub bass, pluck chords and a soft pad, plus three effects
tied to the edit: a metal "tick" on the ring, risers into each cut, and an
impact when the price card lands.

  python3 music.py out.wav [--bars 8] [--impact-bar 6]
"""
import argparse
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
BAR = 2.2
BEAT = BAR / 4
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f):
    return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)


def hp(x, f):
    return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def add(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def kick():
    t = t_(0.45)
    f = 45 + 85 * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    click = hp(rng.standard_normal(len(t)), 2000) * np.exp(-t / 0.004) * 0.25
    return np.tanh(1.6 * (body + click))


def clap():
    t = t_(0.35)
    n = bp(rng.standard_normal(len(t)), 900, 5000)
    env = np.exp(-t / 0.09)
    for d in (0.0, 0.011, 0.023):             # three quick hits = a clap
        env = env + (t >= d) * np.exp(-np.clip(t - d, 0, None) / 0.008) * 0.8
    return n * env * 0.6


def hat(open_=False):
    t = t_(0.25 if open_ else 0.06)
    n = hp(rng.standard_normal(len(t)), 7000)
    return n * np.exp(-t / (0.07 if open_ else 0.015)) * 0.35


def note(freq, dur, kind="pluck"):
    t = t_(dur)
    if kind == "sub":
        s = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(4 * np.pi * freq * t)
        env = np.minimum(1, t / 0.01) * np.exp(-t / 0.5)
        return np.tanh(1.3 * s) * env
    if kind == "pad":
        s = sum(np.sin(2 * np.pi * freq * k * t + rng.uniform(0, 6)) / k for k in (1, 2, 3))
        s += 0.6 * np.sin(2 * np.pi * freq * 1.004 * t)          # slight detune
        env = np.minimum(1, t / 0.35) * np.minimum(1, (dur - t) / 0.3)
        return lp(s, 1800) * env * 0.5
    # pluck: bright saw-ish tone with a fast decay
    s = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 9))
    return lp(s, 3200) * np.exp(-t / 0.18) * np.minimum(1, t / 0.003)


def tick():
    t = t_(0.12)
    s = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((2450, 1), (3720, .7), (5130, .5), (6900, .3)))
    return s * np.exp(-t / 0.018) * 0.5 + hp(rng.standard_normal(len(t)), 4000) * np.exp(-t / 0.003) * 0.3


def riser(d=0.5):
    t = t_(d)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    steps = 10                                  # sweep the band upwards in slices
    for k in range(steps):
        a, b = k * len(n) // steps, (k + 1) * len(n) // steps
        lo = 400 * (1 + 2.2 * k)
        out[a:b] = bp(n, lo, min(lo * 3, 16000))[a:b]
    return out * (t / d) ** 2 * 0.35


def impact():
    t = t_(1.4)
    boom = np.sin(2 * np.pi * (38 + 40 * np.exp(-t / 0.06)) * t) * np.exp(-t / 0.45)
    return np.tanh(1.5 * boom) * 0.9 + lp(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.25) * 0.3


def build(bars=8, impact_bar=6):
    n = int(bars * BAR * SR)
    drums, bass, music, fx = (np.zeros(n) for _ in range(4))
    side = np.ones(n)                            # sidechain gain, ducked by the kick
    # Am, F, C, G  (roots for the bass, triads one octave up for the chords)
    prog = [(55.0, (220.0, 261.63, 329.63)), (43.65, (174.61, 220.0, 261.63)),
            (65.41, (196.0, 261.63, 329.63)), (49.0, (196.0, 246.94, 293.66))]
    for b in range(bars):
        t0 = b * BAR
        root, chord = prog[b % 4]
        for beat in range(4):
            bt = t0 + beat * BEAT
            add(drums, kick(), bt, 0.9)
            i = int(bt * SR)
            d = t_(0.22)
            side[i:i + len(d)] = np.minimum(side[i:i + len(d)], 0.35 + 0.65 * (d / 0.22) ** 0.7)
            if beat in (1, 3):
                add(drums, clap(), bt, 0.55)
            add(drums, hat(), bt + BEAT / 2, 0.5)
            add(drums, hat(), bt + BEAT * 0.75, 0.25)
        add(drums, hat(True), t0 + 3.5 * BEAT, 0.35)
        for off in (0, 0.5, 1.5, 2.0, 3.0):      # sub bass groove
            add(bass, note(root, BEAT * 0.9, "sub"), t0 + off * BEAT, 0.55)
        for off in (0, 0.75, 1.5, 2.5, 3.25):    # syncopated pluck stabs
            for f in chord:
                add(music, note(f * 2, 0.35), t0 + off * BEAT, 0.11)
        for f in chord:                          # pad under it all
            add(music, note(f, BAR), t0, 0.12)
        if b != impact_bar - 1:                  # riser into each cut (not before the impact)
            add(fx, riser(), t0 + BAR - 0.5, 1.0)
    add(fx, tick(), 0.0, 0.9)                    # the ring opening on frame 1
    add(fx, impact(), impact_bar * BAR, 0.8)     # the price card lands
    mix = drums + (bass + music) * side + fx
    mix = hp(mix, 30)
    mix = np.tanh(1.2 * mix / (np.max(np.abs(mix)) + 1e-9)) * 0.89
    # gentle stereo: hats and plucks widened by a short delay on the right
    left = mix
    right = np.concatenate([np.zeros(int(0.012 * SR)), (drums * 0 + music * side)])[:n] * 0.25 + mix * 0.85
    st = np.stack([left, right], axis=1)
    st /= np.max(np.abs(st)) / 0.89
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--bars", type=int, default=8)
    ap.add_argument("--impact-bar", type=int, default=6)
    a = ap.parse_args()
    st = build(a.bars, a.impact_bar)
    pcm = (st * 32767).astype("<i2")
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {a.out}: {len(st) / SR:.2f}s")


if __name__ == "__main__":
    main()
