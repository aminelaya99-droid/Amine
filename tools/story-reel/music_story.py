#!/usr/bin/env python3
"""Calm North-African storytelling track for an animated fable, synthesised.

Same grid as product-reel (one bar = 2.2 s, 109 BPM) so scenes land on bars.
A plucked oud-like string (Karplus-Strong) arpeggiates in A Hijaz over a soft
pad; a light darbuka maqsum (doum / tek) enters after the intro and drops out
for the moral. Effects tied to the story: a thud on the strike bar, an impact
with a shimmer when the water comes up, and the last chord lifts to A major.

  python3 music_story.py out.wav --bars 16 --strike-bar 10 --water-bar 11 --moral-bar 14
"""
import argparse
import wave

import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 44100
BAR = 2.2
BEAT = BAR / 4
rng = np.random.default_rng(11)


def t_(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f):
    return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)


def hp(x, f):
    return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)


def add(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def oud(freq, dur=1.6):
    """Karplus-Strong plucked string, a little nasal like an oud."""
    n = int(dur * SR)
    p = max(2, int(SR / freq))
    x = np.zeros(n)
    x[:p] = rng.uniform(-1, 1, p) * np.hanning(p)
    a = np.zeros(p + 2)
    a[0] = 1.0
    a[p] = a[p + 1] = -0.4985
    y = lfilter([1.0], a, x)
    y = hp(y, 90) + 0.3 * np.sign(y) * np.abs(y) ** 1.5           # a touch of grit
    return y * np.minimum(1, t_(dur) / 0.002)


def pad(freqs, dur):
    t = t_(dur)
    s = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t)
            for f in freqs)
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.5)
    return lp(s, 1200) * env / len(freqs)


def doum():
    t = t_(0.5)
    return np.sin(2 * np.pi * (70 + 60 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.18)


def tek():
    t = t_(0.12)
    return (np.sin(2 * np.pi * 1250 * t) * 0.6 + hp(rng.standard_normal(len(t)), 3000) * 0.5) * np.exp(-t / 0.025)


def impact():
    t = t_(1.6)
    boom = np.sin(2 * np.pi * (40 + 45 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.5)
    return np.tanh(1.4 * boom) + lp(rng.standard_normal(len(t)), 700) * np.exp(-t / 0.3) * 0.3


def shimmer(dur=2.0):
    t = t_(dur)
    s = sum(np.sin(2 * np.pi * f * t) for f in (1760, 2217.5, 2637, 3520))
    return s * np.exp(-t / 0.7) * np.minimum(1, t / 0.05) * 0.15


def build(bars, strike_bar, water_bar, moral_bar):
    n = int(bars * BAR * SR)
    music, drums, fx = np.zeros(n), np.zeros(n), np.zeros(n)
    # A Hijaz: A Bb C# D E F G. Bars alternate A (i) and Gm-ish (vii) colours.
    A, Bb, Cs, D, E, F, G = 220.0, 233.08, 277.18, 293.66, 329.63, 349.23, 392.0
    arps = [[A, Cs, E, A * 2, E, Cs, Bb, Cs],          # A hijaz
            [G, Bb, D, G * 2, D, Bb, A, Bb]]               # G minor colour
    for b in range(bars):
        t0 = b * BAR
        after_water = b >= water_bar
        if b >= moral_bar:                                             # moral: A major, slow
            add(music, pad([A / 2, Cs, E, A], BAR), t0, 0.5)
            for k, f in enumerate([A, Cs, E, A * 2]):
                add(music, oud(f, 2.0), t0 + k * BEAT, 0.35)
            continue
        chord = [A / 2, Cs if after_water else Bb, E] if b % 2 == 0 else [G / 2, Bb, D]
        add(music, pad(chord, BAR), t0, 0.45)
        arp = arps[b % 2]
        if after_water:
            arp = [f if f not in (Bb,) else Cs for f in arp]           # brighten after the water
        for k, f in enumerate(arp):                                    # 8 notes per bar
            add(music, oud(f, 1.4), t0 + k * BEAT / 2, 0.30 if k % 2 == 0 else 0.2)
        if 2 <= b < moral_bar and b != water_bar:                      # maqsum: D T . T D . T .
            for pos, hit in ((0, "d"), (1, "t"), (3, "t"), (4, "d"), (6, "t")):
                add(drums, doum() if hit == "d" else tek(), t0 + pos * BEAT / 2, 0.5 if hit == "d" else 0.25)
    add(fx, doum() * 1.6, strike_bar * BAR + 1.2, 1.0)                 # the shovel strike
    add(fx, impact(), water_bar * BAR, 0.8)
    add(fx, shimmer(), water_bar * BAR, 1.0)
    mix = music + drums + fx
    mix = hp(mix, 30)
    mix = np.tanh(1.1 * mix / (np.max(np.abs(mix)) + 1e-9)) * 0.89
    right = np.concatenate([np.zeros(int(0.015 * SR)), music])[:n] * 0.2 + mix * 0.85
    st = np.stack([mix, right], axis=1)
    return st / (np.max(np.abs(st)) / 0.89)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--bars", type=int, default=16)
    ap.add_argument("--strike-bar", type=int, default=10)
    ap.add_argument("--water-bar", type=int, default=11)
    ap.add_argument("--moral-bar", type=int, default=14)
    a = ap.parse_args()
    st = build(a.bars, a.strike_bar, a.water_bar, a.moral_bar)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    print(f"wrote {a.out}: {len(st) / SR:.2f}s")


if __name__ == "__main__":
    main()
