#!/usr/bin/env python3
"""
A/B transcription quality test: original MP3 vs re-encoded Opus/OGG.

Answers the question that gates the storage strategy: does re-encoding the
archive to 24kbps Opus measurably degrade Parakeet ASR output?

There is no ground-truth transcript, so the metric is *divergence* between the
two formats: WER/CER of the OGG transcript measured against the MP3 transcript
as reference. Near-zero divergence means the re-encode is ASR-transparent.

Requires episodes that currently have BOTH a .mp3 and a .ogg on disk.

Usage:
    python tools/ab_format_test.py --num-episodes 20 --segment-seconds 300
"""

import argparse
import json
import logging
import random
import re
import string
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

AUDIO_DIR = PROJECT_ROOT / "data" / "audio"
SAMPLE_RATE = 16000

# How much audio to decode accurately after a fast seek. Long enough to absorb
# any imprecision in the fast seek, short enough to stay quick.
PREROLL_SECONDS = 10.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def probe_duration(path):
    """Decoded duration in seconds, or None if ffprobe cannot read the file."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, timeout=120,
    )
    if out.returncode != 0:
        return None
    value = out.stdout.strip()
    try:
        return float(value)
    except ValueError:
        return None


def find_pairs(check_durations=False):
    """Find every episode with both an .ogg and a matching .mp3, grouped by podcast.

    Pass check_durations=True to pre-screen every pair by duration. That probes
    the whole archive and is slow; by default the per-window cross-correlation
    check in main() catches mismatched pairs far more cheaply, and catches
    misalignment a duration check would miss entirely.
    """
    by_podcast = defaultdict(list)
    skipped = 0
    for ogg in sorted(AUDIO_DIR.rglob("*.ogg")):
        mp3 = ogg.with_suffix(".mp3")
        if not (mp3.exists() and ogg.stat().st_size > 0 and mp3.stat().st_size > 0):
            continue
        if check_durations:
            d_ogg, d_mp3 = probe_duration(ogg), probe_duration(mp3)
            if not d_ogg or not d_mp3 or abs(d_ogg - d_mp3) > max(2.0, 0.01 * d_mp3):
                skipped += 1
                continue
        by_podcast[ogg.parent.name].append((mp3, ogg))
    if skipped:
        logger.warning(f"Excluded {skipped} pairs whose mp3 and ogg durations disagree")
    return by_podcast


def sample_pairs(by_podcast, n, seed=1234):
    """Stratified sample: spread picks across as many distinct podcasts as possible."""
    rng = random.Random(seed)
    podcasts = sorted(by_podcast)
    rng.shuffle(podcasts)
    picked = []
    round_idx = 0
    while len(picked) < n:
        added = False
        for p in podcasts:
            items = sorted(by_podcast[p])
            if round_idx < len(items):
                picked.append(items[rng.randrange(len(items))] if round_idx == 0 else items[round_idx])
                added = True
                if len(picked) == n:
                    break
        if not added:
            break
        round_idx += 1
    return picked


def decode_full(audio_path):
    """Decode an entire file to a 16kHz mono float32 array via ffmpeg.

    Both formats are decoded from sample zero, so identical slice ranges cover
    identical audio. Seeking is deliberately avoided: ffmpeg's fast seek is
    frame-approximate on MP3 but sample-accurate on Opus, so seeking to the same
    timestamp in each lands several seconds apart and the comparison silently
    measures different content instead of codec loss.
    """
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(audio_path),
         "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1", "-"],
        capture_output=True, timeout=1800,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {audio_path}: {proc.stderr[-300:]}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def write_window(audio, out_path, start_sample, n_samples):
    """Write one window of a decoded signal to a 16kHz mono WAV."""
    window = audio[start_sample:start_sample + n_samples]
    sf.write(str(out_path), window, SAMPLE_RATE)
    return window


def alignment_lag(a, b, max_lag_s=5.0):
    """Offset in seconds between two signals, by FFT cross-correlation.

    A non-zero lag means the two windows are not the same audio, so any word
    differences between their transcripts say nothing about the codec.
    """
    n = min(len(a), len(b))
    if n == 0:
        return None, 0.0
    a = a[:n].astype(np.float64) - float(a[:n].mean())
    b = b[:n].astype(np.float64) - float(b[:n].mean())

    size = 1 << int(np.ceil(np.log2(2 * n)))
    corr = np.fft.irfft(np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size)), size)
    max_lag = min(int(max_lag_s * SAMPLE_RATE), n - 1)
    # Positive lags sit at the front of the array, negative lags wrap to the end
    candidates = np.concatenate([corr[:max_lag + 1], corr[-max_lag:]])
    offsets = np.concatenate([np.arange(max_lag + 1), np.arange(-max_lag, 0)])
    peak = int(candidates.argmax())
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return offsets[peak] / SAMPLE_RATE, float(candidates[peak] / norm) if norm else 0.0


_PUNCT = str.maketrans("", "", string.punctuation)


def normalize(text):
    """Lowercase, strip punctuation, collapse whitespace -- standard WER normalization."""
    text = text.lower().translate(_PUNCT)
    return re.sub(r"\s+", " ", text).strip()


def edit_distance(ref, hyp):
    """Levenshtein distance over sequences, computed row-wise with numpy."""
    if not ref:
        return len(hyp)
    prev = np.arange(len(ref) + 1, dtype=np.int32)
    for j, h in enumerate(hyp, start=1):
        cur = np.empty_like(prev)
        cur[0] = j
        for i, r in enumerate(ref, start=1):
            cur[i] = min(prev[i] + 1, cur[i - 1] + 1, prev[i - 1] + (r != h))
        prev = cur
    return int(prev[-1])


def error_rate(ref_units, hyp_units):
    if not ref_units:
        return 0.0 if not hyp_units else 1.0
    return edit_distance(ref_units, hyp_units) / len(ref_units)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--num-episodes", type=int, default=20)
    parser.add_argument("--segment-seconds", type=int, default=90,
                        help="Length of each sampled window. Kept short because Conformer "
                             "self-attention is quadratic in time and this GPU is shared.")
    parser.add_argument("--segments-per-episode", type=int, default=4,
                        help="Windows sampled per episode, spread across its runtime")
    parser.add_argument("--check-durations", action="store_true",
                        help="Pre-screen every mp3/ogg pair by duration before sampling (slow)")
    parser.add_argument("--model", default="nvidia/parakeet-tdt-0.6b-v2")
    parser.add_argument("--work-dir", default="/tmp/ab_format_test")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "tools" / "ab_format_results.json"))
    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    by_podcast = find_pairs(check_durations=args.check_durations)
    total_pairs = sum(len(v) for v in by_podcast.values())
    logger.info(f"Found {total_pairs} mp3/ogg pairs across {len(by_podcast)} podcasts")
    if total_pairs == 0:
        logger.error("No mp3/ogg pairs on disk -- nothing to compare")
        sys.exit(1)

    pairs = sample_pairs(by_podcast, min(args.num_episodes, total_pairs))
    logger.info(f"Sampled {len(pairs)} episodes from "
                f"{len({p[0].parent.name for p in pairs})} distinct podcasts")

    # Sample several windows spread across each episode rather than one long one:
    # more content diversity for the same amount of audio, and a much smaller
    # attention matrix per forward pass.
    n_seg = args.segments_per_episode
    start_fracs = [(i + 1) / (n_seg + 1) for i in range(n_seg)]

    # Decode each file once and cut identical sample ranges from both. Decoding
    # up front also means a model failure doesn't waste the GPU warm-up.
    n_samples = args.segment_seconds * SAMPLE_RATE
    jobs = []
    misaligned = []
    for idx, (mp3, ogg) in enumerate(pairs):
        try:
            mp3_audio = decode_full(mp3)
            ogg_audio = decode_full(ogg)

            usable = min(len(mp3_audio), len(ogg_audio))
            if usable < n_samples * 2:
                logger.warning(f"Skipping {mp3.parent.name}: too short to sample")
                continue

            mp3_wavs, ogg_wavs, lags = [], [], []
            for s_idx, frac in enumerate(start_fracs):
                start = min(int(usable * frac), usable - n_samples)
                mp3_wav = work_dir / f"{idx:03d}_{s_idx}_mp3.wav"
                ogg_wav = work_dir / f"{idx:03d}_{s_idx}_ogg.wav"
                a = write_window(mp3_audio, mp3_wav, start, n_samples)
                b = write_window(ogg_audio, ogg_wav, start, n_samples)
                lags.append(alignment_lag(a, b))
                mp3_wavs.append(str(mp3_wav))
                ogg_wavs.append(str(ogg_wav))

            worst_lag = max(abs(l) for l, _ in lags)
            worst_corr = min(c for _, c in lags)
            if worst_lag > 0.02 or worst_corr < 0.5:
                # Comparing transcripts of different audio measures nothing.
                misaligned.append((mp3.parent.name, worst_lag, worst_corr))
                logger.warning(f"Skipping {mp3.parent.name}: windows misaligned "
                               f"(lag {worst_lag:.3f}s, corr {worst_corr:.2f})")
                continue

            jobs.append({
                "idx": idx, "podcast": mp3.parent.name, "episode": mp3.stem,
                "mp3_path": str(mp3), "ogg_path": str(ogg),
                "mp3_size_mb": mp3.stat().st_size / 1024**2,
                "ogg_size_mb": ogg.stat().st_size / 1024**2,
                "episode_duration_s": len(mp3_audio) / SAMPLE_RATE,
                "segments": n_seg, "segment_len_s": args.segment_seconds,
                "max_alignment_lag_s": worst_lag,
                "min_alignment_corr": worst_corr,
                "mp3_wav": mp3_wavs, "ogg_wav": ogg_wavs,
            })
            logger.info(f"[{idx:03d}] {mp3.parent.name[:34]:34s} prepared "
                        f"(lag {worst_lag:.3f}s, corr {worst_corr:.2f})")
        except Exception as e:
            logger.warning(f"Skipping {mp3.name}: {e}")

    if misaligned:
        logger.warning(f"{len(misaligned)} episodes excluded for misaligned windows")

    logger.info(f"Prepared {len(jobs)} segment pairs; loading ASR model...")

    from nemo.collections.asr.models import ASRModel
    import torch

    model = ASRModel.from_pretrained(model_name=args.model)
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda()

    use_cuda = torch.cuda.is_available()

    def transcribe(paths):
        """Transcribe one window at a time; this GPU is shared, so keep the footprint small."""
        texts = []
        for i in range(0, len(paths), 1):
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16,
                                                        enabled=use_cuda):
                out = model.transcribe(paths[i:i + 1], batch_size=1, return_hypotheses=False)
            for item in out:
                texts.append(item.text if hasattr(item, "text") else str(item))
            if use_cuda:
                torch.cuda.empty_cache()
            if (i + 1) % 20 == 0:
                logger.info(f"  transcribed {i + 1}/{len(paths)} windows")
        return texts

    # Flatten every window of both formats into one pass, then regroup per episode
    all_wavs = [w for j in jobs for w in j["mp3_wav"]] + [w for j in jobs for w in j["ogg_wav"]]
    logger.info(f"Transcribing {len(all_wavs)} windows "
                f"({len(all_wavs) * args.segment_seconds / 3600:.1f}h of audio)...")
    texts = transcribe(all_wavs)

    half = len(texts) // 2
    def regroup(flat):
        return [" ".join(flat[i * n_seg:(i + 1) * n_seg]) for i in range(len(jobs))]
    mp3_texts, ogg_texts = regroup(texts[:half]), regroup(texts[half:])

    results = []
    for job, mp3_text, ogg_text in zip(jobs, mp3_texts, ogg_texts):
        ref, hyp = normalize(mp3_text), normalize(ogg_text)
        ref_words, hyp_words = ref.split(), hyp.split()
        wer = error_rate(ref_words, hyp_words)
        cer = error_rate(list(ref), list(hyp))
        results.append({
            **{k: v for k, v in job.items() if not k.endswith("_wav")},
            "mp3_words": len(ref_words), "ogg_words": len(hyp_words),
            "wer": wer, "cer": cer,
            "mp3_text": mp3_text, "ogg_text": ogg_text,
        })
        logger.info(f"[{job['idx']:03d}] {job['podcast'][:32]:32s} "
                    f"WER={wer*100:5.2f}%  CER={cer*100:5.2f}%  words={len(ref_words)}")

    total_ref_words = sum(r["mp3_words"] for r in results)
    agg_wer = (sum(r["wer"] * r["mp3_words"] for r in results) / total_ref_words) if total_ref_words else 0.0
    agg_cer = (sum(r["cer"] * len(normalize(r["mp3_text"])) for r in results)
               / max(1, sum(len(normalize(r["mp3_text"])) for r in results)))
    wers = sorted(r["wer"] for r in results)
    mp3_mb = sum(r["mp3_size_mb"] for r in results)
    ogg_mb = sum(r["ogg_size_mb"] for r in results)

    summary = {
        "episodes": len(results),
        "podcasts": len({r["podcast"] for r in results}),
        "segment_seconds": args.segment_seconds,
        "segments_per_episode": args.segments_per_episode,
        "total_reference_words": total_ref_words,
        "aggregate_wer": agg_wer,
        "aggregate_cer": agg_cer,
        "median_wer": wers[len(wers) // 2] if wers else 0.0,
        "max_wer": wers[-1] if wers else 0.0,
        "episodes_with_zero_wer": sum(1 for w in wers if w == 0.0),
        "sample_mp3_mb": mp3_mb,
        "sample_ogg_mb": ogg_mb,
        "excluded_misaligned": len(misaligned),
        "max_alignment_lag_s": max((r.get("max_alignment_lag_s", 0) for r in results),
                                   default=0.0),
        "size_reduction_pct": (1 - ogg_mb / mp3_mb) * 100 if mp3_mb else 0.0,
    }

    Path(args.output).write_text(json.dumps({"summary": summary, "results": results}, indent=2))

    print("\n" + "=" * 64)
    print("MP3 vs OPUS/OGG TRANSCRIPTION DIVERGENCE")
    print("=" * 64)
    print(f"Episodes compared      : {summary['episodes']} across {summary['podcasts']} podcasts")
    print(f"Audio compared         : {summary['episodes'] * args.segments_per_episode * args.segment_seconds / 60:.0f} min per format")
    print(f"Reference words (mp3)  : {total_ref_words:,}")
    print(f"Aggregate WER          : {agg_wer * 100:.3f}%")
    print(f"Aggregate CER          : {agg_cer * 100:.3f}%")
    print(f"Median / max WER       : {summary['median_wer'] * 100:.3f}% / {summary['max_wer'] * 100:.3f}%")
    print(f"Identical transcripts  : {summary['episodes_with_zero_wer']}/{summary['episodes']}")
    print(f"Size {mp3_mb:.0f}MB -> {ogg_mb:.0f}MB  ({summary['size_reduction_pct']:.1f}% smaller)")
    print("=" * 64)
    print(f"\nFull results: {args.output}")


if __name__ == "__main__":
    main()
