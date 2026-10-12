#!/usr/bin/env python3
"""Align user's re-dubbed voice to the original subtitle sentence grid.

Strategy: segment both vocal stems; assign user phrases to original
sentences by cumulative-speech-duration matching (same script => shared
coordinate); re-anchor each sentence's user audio at the original start,
pitch-preserving time-stretch toward the original spoken length.
"""
import subprocess, sys
import numpy as np
import soundfile as sf

BASE = '/home/hatch/workspace/your_files/zeigarnik-episode-01'
ORIG_VOC = f'{BASE}/separation/demucs-out/htdemucs/original-mix/vocals.wav'
USER_VOC = f'{BASE}/redub/user-voice-residual.wav'
ACC = f'{BASE}/separation/no_vocals_minus.wav'
SR = 44100
TOTAL = 156.42

def segments(path, min_sil=0.42, thr_ratio=0.16, min_dur=0.45):
    d, sr = sf.read(path)
    x = d.mean(axis=1)
    hop = int(0.02 * sr); n = len(x) // hop
    rms = np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop].astype(np.float64)**2)) for i in range(n)])
    rms = np.convolve(rms, np.ones(5)/5, mode='same')
    hi, lo = np.percentile(rms, 95), np.percentile(rms, 20)
    thr = lo + (hi - lo) * thr_ratio
    active = rms > thr
    segs = []; i = 0
    while i < n:
        if active[i]:
            j = i
            while j < n:
                if not active[j]:
                    run = 0; k2 = j
                    while k2 < n and not active[k2]:
                        run += 1; k2 += 1
                    if run * 0.02 >= min_sil or k2 >= n:
                        break
                    j = k2
                else:
                    j += 1
            segs.append((i * 0.02, j * 0.02)); i = j
        else:
            i += 1
    return [(a, b) for a, b in segs if b - a >= min_dur]

orig = segments(ORIG_VOC)
user = segments(USER_VOC)
print(f'orig sentences: {len(orig)}  user phrases: {len(user)}')
o_cum = np.cumsum([b - a for a, b in orig])
u_cum = np.cumsum([b - a for a, b in user])
print(f'orig speech total {o_cum[-1]:.1f}s | user speech total {u_cum[-1]:.1f}s')

# assign each user phrase to an orig sentence via cumulative midpoint
assign = []
u_prev = 0.0
for j, (a, b) in enumerate(user):
    mid = u_prev + (b - a) / 2; u_prev = u_cum[j]
    i = int(np.searchsorted(o_cum, mid, side='right'))
    assign.append(min(i, len(orig) - 1))
groups = {}
for j, i in enumerate(assign):
    groups.setdefault(i, []).append(j)
missing = [i for i in range(len(orig)) if i not in groups]
print('sentences with no user phrase:', missing)
for i in sorted(groups):
    js = groups[i]
    print(f'  sent {i:2d} orig {orig[i][0]:6.2f}-{orig[i][1]:6.2f} <- user phrases {js[0]}..{js[-1]} '
          f'({user[js[0]][0]:.2f}-{user[js[-1]][1]:.2f})')

# load user stem, gate low-level bleed
u, _ = sf.read(USER_VOC)
if u.ndim == 1: u = np.stack([u, u], axis=1)
peak = np.abs(u).max()
gate = 0.012 * peak / 0.99 if peak > 0 else 0
mono = np.abs(u).mean(axis=1)
u[mono < gate] = 0.0

canvas = np.zeros((int(TOTAL * SR) + SR, 2), dtype=np.float64)
tmp = '/tmp/chunk.wav'; tmp2 = '/tmp/chunk_st.wav'
for i in sorted(groups):
    js = groups[i]
    s0 = max(0.0, user[js[0]][0] - 0.05); s1 = min(len(u) / SR, user[js[-1]][1] + 0.05)
    chunk = u[int(s0 * SR):int(s1 * SR)].astype(np.float32)
    d_src = len(chunk) / SR
    a_i = orig[i][1] - orig[i][0]
    factor = d_src / a_i                      # atempo>1 shortens
    factor_c = float(np.clip(factor, 0.88, 1.35))
    if abs(factor_c - 1.0) > 0.02:
        sf.write(tmp, chunk, SR)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp,
                        '-filter:a', f'atempo={factor_c:.4f}', tmp2], check=True)
        chunk, _ = sf.read(tmp2, dtype='float64')
        if chunk.ndim == 1: chunk = np.stack([chunk, chunk], axis=1)
    else:
        chunk = chunk.astype(np.float64)
    # 8ms fades
    f = int(0.008 * SR)
    if len(chunk) > 2 * f:
        chunk[:f] *= np.linspace(0, 1, f)[:, None]
        chunk[-f:] *= np.linspace(1, 0, f)[:, None]
    pos = int(orig[i][0] * SR)
    end = min(len(canvas), pos + len(chunk))
    canvas[pos:end] += chunk[:end - pos]

# gain: match original vocals RMS over the whole track
o, _ = sf.read(ORIG_VOC)
def rms(x): return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
g = rms(o) / max(rms(canvas), 1e-9)
print(f'voice gain applied: {g:.2f}')
canvas *= g
sf.write(f'{BASE}/redub/aligned-voice.wav', canvas.astype(np.float32), SR)

acc, _ = sf.read(ACC)
n = min(len(acc), len(canvas))
mix = acc[:n].astype(np.float64) + canvas[:n]
pk = np.abs(mix).max()
if pk > 0.98:
    mix *= 0.98 / pk
    print(f'mix peak {pk:.2f} -> normalized')
sf.write(f'{BASE}/redub/final-mix.wav', mix.astype(np.float32), SR)
print('wrote aligned-voice.wav and final-mix.wav, dur', round(n / SR, 2))
