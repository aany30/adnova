"""
Shared media utilities: image processing + multi-frame video storyboard via OpenCV.
"""
import io
import os
import base64
import tempfile
from typing import Optional

import cv2
from PIL import Image
import subprocess


def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _frame_to_jpeg(frame) -> Optional[bytes]:
    """Convert an OpenCV BGR frame to JPEG bytes."""
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        # Resize to max 512px on longest side for storyboard (Smaller = Much Faster on Render)
        max_size = 512
        if max(pil.size) > max_size:
            ratio = max_size / max(pil.size)
            pil = pil.resize((int(pil.width * ratio), int(pil.height * ratio)), Image.LANCZOS)
        out = io.BytesIO()
        pil.save(out, format="JPEG", quality=82)
        return out.getvalue()
    except Exception as e:
        print(f"Frame to JPEG error: {e}")
        return None


def _hist_distance(a, b) -> float:
    """Return a rough 0..1 visual distance between two grayscale histograms."""
    if a is None or b is None:
        return 1.0
    similarity = cv2.compareHist(a, b, cv2.HISTCMP_CORREL)
    if similarity != similarity:  # NaN guard
        return 1.0
    return max(0.0, min(1.0, 1.0 - similarity))


def _nearest_frame(frames: list[dict], target_time: float) -> Optional[dict]:
    if not frames:
        return None
    return min(frames, key=lambda f: abs(f["timestamp"] - target_time))


def _is_unique_frame(candidate: dict, selected: list[dict], min_gap_seconds: float = 0.45) -> bool:
    for item in selected:
        close_in_time = abs(candidate["timestamp"] - item["timestamp"]) < min_gap_seconds
        visually_similar = _hist_distance(candidate.get("hist"), item.get("hist")) < 0.16
        if close_in_time or visually_similar:
            return False
    return True


def _read_jpeg_at_frame(cap, frame_index: int) -> Optional[bytes]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_index))
    ret, frame = cap.read()
    if not ret or frame is None:
        return None
    return _frame_to_jpeg(frame)


def extract_adaptive_video_frames(
    video_bytes: bytes,
    min_frames: int = 12,
    max_frames: int = 16
) -> list[dict]:
    """
    Scan the full video locally, then return 12-16 meaningful frames for AI.
    Each item includes JPEG bytes plus the timestamp used to label the frame.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if total_frames <= 0 or fps <= 0:
            cap.release()
            return []

        duration = total_frames / fps
        scanned = []
        prev_gray = None
        frame_index = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (96, 96), interpolation=cv2.INTER_AREA)
            blur = float(cv2.Laplacian(small, cv2.CV_64F).var())
            change = 0.0
            if prev_gray is not None:
                change = float(cv2.absdiff(small, prev_gray).mean())

            hist = cv2.calcHist([small], [0], None, [16], [0, 256])
            cv2.normalize(hist, hist)

            timestamp = frame_index / fps
            # Favor visible, non-blurry frames with meaningful movement/change.
            quality = min(1.0, blur / 120.0)
            score = (change * 2.4) + (quality * 18.0)
            scanned.append({
                "frame_index": frame_index,
                "timestamp": timestamp,
                "blur": blur,
                "change": change,
                "score": score,
                "hist": hist,
            })

            prev_gray = small
            frame_index += 1

        cap.release()
        if not scanned:
            return []

        avg_change = sum(f["change"] for f in scanned) / max(1, len(scanned))
        target_count = min_frames
        if duration >= 20:
            target_count += 1
        if duration >= 35:
            target_count += 1
        if avg_change >= 6:
            target_count += 1
        if avg_change >= 12:
            target_count += 1
        target_count = max(min_frames, min(max_frames, target_count))

        # Anchors guarantee opening hook, mid-story, and end/CTA coverage.
        anchor_times = [
            0.15,
            min(1.0, duration * 0.08),
            min(2.0, duration * 0.15),
            min(3.0, duration * 0.22),
            duration * 0.25,
            duration * 0.40,
            duration * 0.55,
            duration * 0.70,
            duration * 0.85,
            max(0.0, duration - 1.0),
        ]

        selected = []
        for t in anchor_times:
            candidate = _nearest_frame(scanned, max(0.0, min(duration, t)))
            if candidate and _is_unique_frame(candidate, selected, min_gap_seconds=0.35):
                selected.append(candidate)

        ranked = sorted(scanned, key=lambda f: f["score"], reverse=True)
        for candidate in ranked:
            if len(selected) >= target_count:
                break
            if _is_unique_frame(candidate, selected):
                selected.append(candidate)

        # If a very static video could not satisfy uniqueness, relax enough to
        # still give the model a 12-frame timeline.
        if len(selected) < min_frames:
            for candidate in sorted(scanned, key=lambda f: f["timestamp"]):
                if len(selected) >= min_frames:
                    break
                if all(candidate["frame_index"] != item["frame_index"] for item in selected):
                    selected.append(candidate)

        selected = sorted(selected[:max_frames], key=lambda f: f["timestamp"])

        cap = cv2.VideoCapture(tmp_path)
        output = []
        for item in selected:
            jpeg = _read_jpeg_at_frame(cap, item["frame_index"])
            if jpeg:
                output.append({
                    "bytes": jpeg,
                    "timestamp": round(item["timestamp"], 2),
                    "frame_index": item["frame_index"],
                })
        cap.release()

        return output
    except Exception as e:
        print(f"Adaptive frame extraction error: {e}")
        return []
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def extract_video_storyboard(video_bytes: bytes, num_frames: int = 4) -> list[bytes]:
    """
    Extract multiple frames evenly distributed across the video.
    Returns a list of JPEG bytes (up to num_frames frames).
    Used to give GPT-4o a 'storyboard' view of the full video.
    """
    tmp_path = None
    frames = []
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return frames

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return frames

        # Pick frame positions: 5%, 25%, 50%, 75% of total
        positions = [max(0, int(total_frames * p)) for p in [0.05, 0.25, 0.50, 0.75]]
        positions = positions[:num_frames]

        for pos in positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, min(pos, total_frames - 1))
            ret, frame = cap.read()
            if ret and frame is not None:
                jpeg = _frame_to_jpeg(frame)
                if jpeg:
                    frames.append(jpeg)

        cap.release()
    except Exception as e:
        print(f"Storyboard extraction error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # Fallback: if we got nothing, try first frame
    if not frames:
        single = extract_single_frame(video_bytes)
        if single:
            frames = [single]

    return frames


def extract_single_frame(video_bytes: bytes) -> Optional[bytes]:
    """Extract a single frame (~1 second in) from a video."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
        target = min(int(fps), total - 1)

        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target))
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return None

        return _frame_to_jpeg(frame)
    except Exception as e:
        print(f"Single frame error: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def extract_audio(video_bytes: bytes) -> Optional[bytes]:
    """
    Extract audio from video bytes as a small MP3 using ffmpeg.
    This is much more bandwidth/memory efficient than sending a full video to Whisper.
    """
    tmp_v = None
    tmp_a = None
    try:
        # Create temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as v:
            v.write(video_bytes)
            tmp_v = v.name
        
        tmp_a = tmp_v.replace(".mp4", ".mp3")

        # Run ffmpeg to extract audio (mono, 64k bitrate for efficiency)
        # -y: overwrite, -vn: no video, -ac 1: mono, -ar 16000: 16kHz
        cmd = [
            "ffmpeg", "-y", "-i", tmp_v, 
            "-vn", "-acodec", "libmp3lame", "-ac", "1", "-ar", "16000", "-b:a", "64k", 
            tmp_a
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"FFmpeg audio extraction failed: {result.stderr}")
            return None

        if os.path.exists(tmp_a):
            with open(tmp_a, "rb") as a:
                return a.read()
                
    except Exception as e:
        print(f"Audio extraction error: {e}")
    finally:
        for p in [tmp_v, tmp_a]:
            if p and os.path.exists(p):
                try: os.unlink(p)
                except: pass

    return None


def process_uploaded_file(file_bytes: bytes, content_type: str) -> Optional[bytes]:
    """
    For images: resize and return JPEG bytes.
    For videos: return first frame as JPEG (for the metrics router).
    """
    is_video = "video" in (content_type or "")
    if is_video:
        return extract_single_frame(file_bytes)
    else:
        try:
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            max_size = 1024
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=85)
            return out.getvalue()
        except Exception as e:
            print(f"Image processing error: {e}")
            return None
