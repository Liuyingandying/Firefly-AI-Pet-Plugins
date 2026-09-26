"""firefly_video_extension 环境自检。

检查本地视频分析 canonical 路径的真实依赖（不只是 import——FFmpeg 必须
实际执行 -version）：

  Python 3.10+ / ffmpeg / ffprobe / faster_whisper / scenedetect /
  rapidocr / onnxruntime

用法：
    python scripts/check_environment.py            # 全量检查
    python scripts/check_environment.py --quiet    # 只输出结论行

退出码：0 = 全部就绪；1 = 有缺失（stdout 给出逐项 PASS/FAIL 与安装提示）。
"""

from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys

CHECKS: list[tuple[str, str, str]] = [
    # (名称, kind, 安装提示)
    ("python", "python", "Python 3.10+：https://www.python.org/downloads/"),
    ("ffmpeg", "exe", "winget install ffmpeg  或  https://www.gyan.dev/ffmpeg/builds/"),
    ("ffprobe", "exe", "随 ffmpeg 一起分发（同上）"),
    ("faster_whisper", "import", "pip install faster-whisper"),
    ("scenedetect", "import", "pip install scenedetect"),
    ("rapidocr", "import", "pip install \"rapidocr>=3.9,<4\"（宿主 requirements 已含）"),
    ("onnxruntime", "import", "pip install onnxruntime（随 rapidocr 安装）"),
]


def _check_python() -> tuple[bool, str]:
    version = sys.version_info
    ok = version >= (3, 10)
    return ok, f"Python {version.major}.{version.minor}.{version.micro}"


def _check_exe(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    if path is None:
        return False, f"{name} 不在 PATH"
    try:
        proc = subprocess.run(
            [name, "-version"], capture_output=True, text=True, timeout=30
        )
    except Exception as exc:  # noqa: BLE001 - 报告为 FAIL 而非崩溃
        return False, f"{name} 执行失败: {exc}"
    first = (proc.stdout or "").splitlines()[0] if proc.stdout else ""
    return proc.returncode == 0, first.strip()[:80]


def _check_import(module: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module)
        return True, f"import {module} OK"
    except Exception as exc:  # noqa: BLE001 - 报告为 FAIL 而非崩溃
        return False, f"import {module} 失败: {type(exc).__name__}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="只输出结论行")
    args = parser.parse_args()

    results = []
    for name, kind, hint in CHECKS:
        if kind == "python":
            ok, detail = _check_python()
        elif kind == "exe":
            ok, detail = _check_exe(name)
        else:
            ok, detail = _check_import(name)
        results.append((name, ok, detail, hint))
        if not args.quiet:
            suffix = "" if ok else f"\n             → {hint}"
            print(f"[{'PASS' if ok else 'FAIL'}] {name:<15} {detail}{suffix}")

    failed = [name for name, ok, _, _ in results if not ok]
    if failed:
        print(f"ENV CHECK FAIL: {', '.join(failed)}")
        return 1
    print("ENV CHECK PASS: 本地视频分析 canonical 路径全部就绪")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
