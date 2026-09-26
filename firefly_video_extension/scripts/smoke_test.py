"""firefly_video_extension 真实冒烟测试（不 mock，测试视频不入库）。

对指定的本地 MP4 依次真实执行管线六要素，每项独立 PASS/FAIL：

    DURATION   ffprobe 实测时长
    AUDIO      ffmpeg 提取 16kHz WAV
    ASR        faster-whisper 实际转写（输出段数/字数/样例）
    SCENE      PySceneDetect 实际场景检测
    KEYFRAME   ffmpeg 关键帧抽取
    OCR        RapidOCR 对关键帧实际识别（EMPTY 记 FAIL）

用法：
    python scripts/smoke_test.py --video <path/to/video.mp4>
    python scripts/smoke_test.py --video clip.mp4 --skip-asr   # 跳过较慢的 ASR

测试视频请自备（任何含人声与画面文字的短片即可），**不要提交到仓库**。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(cmd: list[str], timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def check_duration(video: Path) -> tuple[bool, str]:
    proc = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(video)])
    if proc.returncode != 0:
        return False, (proc.stderr or "").strip()[-120:]
    return True, f"duration={float(proc.stdout.strip()):.2f}s"


def check_audio(video: Path, work: Path) -> tuple[bool, str]:
    wav = work / "audio.wav"
    proc = _run([
        "ffmpeg", "-y", "-i", str(video), "-vn",
        "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(wav),
    ], timeout=180)
    ok = proc.returncode == 0 and wav.exists() and wav.stat().st_size > 1000
    return ok, f"wav={wav.stat().st_size} bytes" if ok else (proc.stderr or "")[-120:]


def check_asr(video: Path, work: Path) -> tuple[bool, str]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        return False, f"faster-whisper 未安装: {exc}"
    wav = work / "audio.wav"
    if not wav.exists():
        return False, "先通过 AUDIO 项生成 wav"
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(wav), language=None)
    texts = [seg.text.strip() for seg in segments if seg.text.strip()]
    chars = sum(len(t) for t in texts)
    sample = (texts[0][:40] + "…") if texts else ""
    return chars > 0, f"segments={len(texts)} chars={chars} sample={sample!r}"


def check_scene(video: Path) -> tuple[bool, str]:
    try:
        from scenedetect import ContentDetector, SceneManager, detect
    except ImportError as exc:
        return False, f"scenedetect 未安装: {exc}"
    try:
        scene_list = detect(str(video), ContentDetector())
    except Exception as exc:  # noqa: BLE001 - 解码失败如实报 FAIL
        return False, f"检测失败: {type(exc).__name__}: {str(exc)[:100]}"
    return True, f"scenes={len(scene_list)}"


def check_keyframe(video: Path, work: Path) -> tuple[bool, str]:
    frame = work / "keyframe.jpg"
    proc = _run([
        "ffmpeg", "-y", "-ss", "1", "-i", str(video),
        "-vframes", "1", "-vf", "scale=960:-1", str(frame),
    ], timeout=120)
    ok = proc.returncode == 0 and frame.exists() and frame.stat().st_size > 1000
    return ok, f"jpg={frame.stat().st_size} bytes" if ok else (proc.stderr or "")[-120:]


def check_ocr(video: Path, work: Path) -> tuple[bool, str]:
    frame = work / "keyframe.jpg"
    if not frame.exists():
        return False, "先通过 KEYFRAME 项生成关键帧"
    try:
        from rapidocr import RapidOCR
    except ImportError:
        try:
            from rapidocr_onnxruntime import RapidOCR  # type: ignore[no-redef]
        except ImportError as exc:
            return False, f"rapidocr 未安装: {exc}"
    engine = RapidOCR()
    result = engine(str(frame))
    # rapidocr 3.x 返回对象带 txts；1.x 返回 (boxes, texts, scores) 元组
    if hasattr(result, "txts"):
        texts = list(result.txts or [])
    elif isinstance(result, tuple) and len(result) >= 2:
        texts = list(result[1] or [])
    else:
        texts = []
    joined = "".join(str(t) for t in texts if t)
    return len(joined) > 0, f"ocr_chars={len(joined)} sample={joined[:40]!r}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="待测视频路径（不入库）")
    parser.add_argument("--skip-asr", action="store_true", help="跳过较慢的 ASR")
    args = parser.parse_args()

    video = Path(args.video)
    if not video.is_file():
        print(f"FAIL 找不到视频: {video}")
        return 1

    checks = [
        ("DURATION", lambda: check_duration(video)),
        ("AUDIO", lambda: check_audio(video, work)),
        ("SCENE", lambda: check_scene(video)),
        ("KEYFRAME", lambda: check_keyframe(video, work)),
        ("OCR", lambda: check_ocr(video, work)),
    ]
    if not args.skip_asr:
        checks.insert(2, ("ASR", lambda: check_asr(video, work)))

    work = Path(tempfile.mkdtemp(prefix="firefly_video_smoke_"))
    failures = 0
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001 - 任何异常=该项 FAIL
            ok, detail = False, f"{type(exc).__name__}: {str(exc)[:120]}"
        if not ok:
            failures += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name:<10} {detail}")

    print(f"\n{len(checks) - failures}/{len(checks)} PASS"
          + ("" if failures else "  (真实视频管线全部就绪)"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
