#!/usr/bin/env python3
"""v3 = v2 assignment + pause-compression before any speed change.
Compress intra-chunk silences first (keep >=0.10s), then atempo only as
needed (<=1.30 preferred), hard cap at slot end. Short chunks stay natural.
"""
import subprocess
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

def compress_pauses(chunk, target_dur):
    """Shrink silent runs (>0.12s) toward 0.35x (min 0.10s) until near target."""
    mono = np.abs(chunk).mean(axis=1)
    hop = int(0.02 * SR); n = len(mono) // hop
    if n == 0: return chunk
    rms = np.array([np.sqrt(np.mean(mono[i*hop:(i+1)*hop].astype(np.float64)**2)) for i in range(n)])
    thr = 0.30 * np.percentile(rms, 80)
    active = rms > thr
    runs = []  # (is_active, frames)
    i = 0
    while i < n:
        j = i
        while j < n and active[j] == active[i]: j += 1
        runs.append([bool(active[i]), j - i]); i = j
    cur = len(chunk) / SR
    for shrink in (0.35, 0.18, 0.08):
        if cur <= target_dur * 1.05: break
        out = []
        for act, fr in runs:
            s = fr * hop
            seg = chunk[len(out)*0 + sum(int(r[2]) for r in out):]  # placeholder, rebuilt below
            out.append([act, fr, s])
        # rebuild with this shrink factor for silent runs > 0.12s
        pieces = []; pos = 0
        for act, fr, s in [(r[0], r[1], r[1]*hop) for r in runs]:
            seg = chunk[pos:pos + s]; pos += s
            if not act and fr * 0.02 > 0.12:
                keep = max(int(0.10 * SR), int(len(seg) * shrink))
                seg = seg[:keep]
            pieces.append(seg)
        chunk = np.concatenate(pieces) if pieces else chunk
        cur = len(chunk) / SR
    return chunk

orig = segments(ORIG_VOC)
user = segments(USER_VOC)
starts = [a for a, _ in orig] + [TOTAL]
groups = {}
for j, (a, b) in enumerate(user):
    mid = (a + b) / 2
    i = int(np.searchsorted(starts, mid, side='right')) - 1
    groups.setdefault(max(0, min(i, len(orig) - 1)), []).append(j)

u, _ = sf.read(USER_VOC)
if u.ndim == 1: u = np.stack([u, u], axis=1)
u[np.abs(u).mean(axis=1) < 0.008] = 0.0

canvas = np.zeros((int(TOTAL * SR) + SR, 2), dtype=np.float64)
tmp, tmp2 = '/tmp/chunk.wav', '/tmp/chunk_st.wav'
for i in sorted(groups):
    js = groups[i]
    s0 = max(0.0, user[js[0]][0] - 0.05); s1 = min(len(u) / SR, user[js[-1]][1] + 0.05)
    chunk = u[int(s0 * SR):int(s1 * SR)].astype(np.float64)
    slot = starts[i + 1] - orig[i][0]
    a_i = orig[i][1] - orig[i][0]
    d0 = len(chunk) / SR
    if d0 > a_i:
        chunk = compress_pauses(chunk, a_i)
    d1 = len(chunk) / SR
    target = min(a_i, slot * 0.98)
    factor = 1.0
    if d1 > target * 1.03:
        factor = float(np.clip(d1 / target, 1.0, 1.32))
        sf.write(tmp, chunk.astype(np.float32), SR)
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp,
                        '-filter:a', f'atempo={factor:.4f}', tmp2], check=True)
        chunk, _ = sf.read(tmp2, dtype='float64')
        if chunk.ndim == 1: chunk = np.stack([chunk, chunk], axis=1)
    maxlen = int(slot * SR)
    if len(chunk) > maxlen: chunk = chunk[:maxlen]
    f = int(0.008 * SR)
    if len(chunk) > 2 * f:
        chunk[:f] *= np.linspace(0, 1, f)[:, None]
        chunk[-f:] *= np.linspace(1, 0, f)[:, None]
    pos = int(orig[i][0] * SR)
    end = min(len(canvas), pos + len(chunk))
    canvas[pos:end] += chunk[:end - pos]
    print(f'sent {i:2d} at {orig[i][0]:6.2f}s  src {d0:.2f}s -> pauses {d1:.2f}s -> atempo {factor:.2f} -> {len(chunk)/SR:.2f}s')

o, _ = sf.read(ORIG_VOC)
def rms(x): return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
g = rms(o) / max(rms(canvas), 1e-9)
print(f'voice gain: {g:.2f}')
canvas *= g
sf.write(f'{BASE}/redub/aligned-voice.wav', canvas.astype(np.float32), SR)
acc, _ = sf.read(ACC)
n = min(len(acc), len(canvas))
mix = acc[:n].astype(np.float64) + canvas[:n]
pk = np.abs(mix).max()
if pk > 0.98:
    mix *= 0.98 / pk; print(f'mix peak {pk:.2f} -> normalized')
sf.write(f'{BASE}/redub/final-mix.wav', mix.astype(np.float32), SR)
print('done')
