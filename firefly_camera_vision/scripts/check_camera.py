"""firefly_camera_vision 设备自检（只查询设备，绝不拍照/保存画面）。

检查 Qt Multimedia 能否看到真实视频输入设备，逐台列出描述。

用法：
    python scripts/check_camera.py            # 需要 QApplication（offscreen 即可）

退出码：0 = 至少一台设备；1 = 无设备或 Qt Multimedia 不可用。
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        print(f"FAIL PySide6 不可用: {exc}")
        return 1

    app = QApplication.instance() or QApplication([])

    try:
        from PySide6.QtMultimedia import QMediaDevices
    except ImportError as exc:
        print(f"FAIL QtMultimedia 不可用: {exc}")
        return 1

    devices = QMediaDevices.videoInputs()
    if not devices:
        print("FAIL 未检测到视频输入设备（ CAMERA_DEVICE_FOUND = NO ）")
        return 1

    print(f"CAMERA_DEVICE_FOUND = YES（{len(devices)} 台）")
    for index, device in enumerate(devices):
        print(f"  [{index}] {device.description()}")
    print("（本次自检只枚举设备，未打开相机、未捕获任何画面）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
