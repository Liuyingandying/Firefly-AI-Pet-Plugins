# -*- coding: utf-8 -*-
"""API 契约测试（无需模型 / 引擎 / GPU / 网络，CI 可跑）。

覆盖宿主 voice_client 实际依赖的服务接口面:
    GET  /health
    POST /voice/speak    play=false → audio/wav + X-* 头
                         play=true  → JSON (emotion/segments/total_ms/session_id/queue)
    POST /voice/queue/stop
    GET  /voice/queue
    POST /voice/queue/clear

Mock 策略（只替重依赖, 管道逻辑走真代码）:
    api.server.get_module          → 桩对象（不加载 RVC 引擎）
    core.speech.tts_synthesize     → 假 mp3 bytes（不联网）
    core.speech.convert_voice      → 假音频数组（不加载模型）
    audio.audio_queue.{sd,_SD_OK}  → 模拟播放（不出声、不依赖声卡）

真实 E2E（模型 + 网络 + 扬声器）见 tests/test_pipeline.py 与 tests/test_cancellation.py,
属于可选验证, 不作为契约回归的一部分。
"""

from __future__ import annotations

import io
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

SERVICE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.server import app  # noqa: E402
import audio.audio_queue as audio_queue_mod  # noqa: E402
import core.speech as speech_mod  # noqa: E402

SR = 40000
FAKE_AUDIO = np.sin(np.linspace(0.0, 440.0 * 2 * np.pi, SR // 5)).astype(np.float32)  # 0.1s


class _StubModule:
    """RVCConverter 的最小桩: 满足 /health 与 lifespan 的读取面。"""

    device = "cpu"
    speakers = {"firefly": SimpleNamespace(display_name="流萤 (Firefly)")}
    _loaded: set[str] = set()

    def load_speaker(self, name: str):
        self._loaded.add(name)
        return self.speakers[name]


@pytest.fixture()
def client(monkeypatch):
    stub = _StubModule()
    monkeypatch.setattr("api.server.get_module", lambda: stub)

    def fake_tts(text, params, voice="zh-CN-XiaoxiaoNeural"):
        return b"fake-mp3"

    def fake_convert(input_audio, speaker_model="firefly", **kwargs):
        return SimpleNamespace(audio=FAKE_AUDIO.copy(), sample_rate=SR, seconds=0.01, speaker=speaker_model)

    monkeypatch.setattr(speech_mod, "tts_synthesize", fake_tts)
    monkeypatch.setattr(speech_mod, "convert_voice", fake_convert)

    # 模拟播放: 不触碰声卡
    monkeypatch.setattr(audio_queue_mod, "sd", None, raising=False)
    monkeypatch.setattr(audio_queue_mod, "_SD_OK", False, raising=False)

    queue = audio_queue_mod.get_audio_queue()
    queue.clear()
    queue.cancelled_sessions.clear()

    with TestClient(app) as c:
        yield c

    queue.clear()


def _wav_bytes(payload: bytes) -> bytes:
    assert payload[:4] == b"RIFF", f"not a wav: {payload[:8]!r}"
    return payload


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["device"] == "cpu"
    assert data["speakers"] == {"firefly": "流萤 (Firefly)"}
    assert data["loaded"] == ["firefly"]      # lifespan 已加载全部注册说话人


def test_speak_play_false_returns_wav_with_headers(client):
    resp = client.post("/voice/speak", json={"text": "你好，我是流萤。", "play": False})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert resp.headers["x-emotion"] == "neutral"
    assert resp.headers["x-emotion-source"] in {"default", "keyword", "explicit", "expression"}
    assert int(resp.headers["x-segments"]) >= 1
    assert resp.headers["x-session-id"]
    _wav_bytes(resp.content)
    with wave.open(io.BytesIO(resp.content)) as w:
        assert w.getframerate() == SR
        assert w.getnframes() > 0


def test_speak_play_true_returns_json_contract(client):
    # 宿主 voice_client.speak 读: emotion / segments(len) / total_ms
    resp = client.post("/voice/speak", json={"text": "你好，我是流萤。", "play": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["emotion"] == "neutral"
    assert isinstance(data["segments"], list) and len(data["segments"]) >= 1
    seg = data["segments"][0]
    assert {"text", "emotion", "duration_s", "tts_ms", "vc_ms"} <= set(seg)
    assert isinstance(data["total_ms"], int)
    assert data["session_id"]
    assert data["cancelled"] is False
    assert {"playing", "queued", "dropped_total", "device"} <= set(data["queue"])


def test_speak_explicit_emotion(client):
    resp = client.post(
        "/voice/speak", json={"text": "今天真开心！", "emotion": "happy", "play": True}
    )
    assert resp.status_code == 200
    assert resp.json()["emotion"] == "happy"


def test_speak_empty_text_400(client):
    resp = client.post("/voice/speak", json={"text": "   ", "play": False})
    assert resp.status_code == 400


def test_speak_play_false_waits_for_playback_path_without_audio_device(client):
    """play=true 且无声卡时应走模拟播放并正常收尾（CI/无设备环境）。

    注: 分句器会把 <6 字的短句并回前句, 测试文本需足够长才能切成两句。
    """
    resp = client.post(
        "/voice/speak",
        json={"text": "今天天气真不错呀。我们一起去公园散步吧。", "play": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["segments"]) == 2
    queue = client.get("/voice/queue").json()
    assert queue["device"].startswith("simulated")


def test_queue_status_shape(client):
    resp = client.get("/voice/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert {"playing", "queued", "dropped_total", "device"} <= set(data)


def test_queue_stop_contract(client):
    # 宿主 voice_client.stop 只要求 200 + JSON 布尔语义
    resp = client.post("/voice/queue/stop", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["stopped"], bool)
    assert data["cancelled_session"] is None or isinstance(data["cancelled_session"], str)
    assert isinstance(data["cleared"], int)


def test_queue_stop_interrupts_pending_playback(client):
    resp = client.post("/voice/speak", json={"text": "长句一。长句二。长句三。", "play": True})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    queue = audio_queue_mod.get_audio_queue()
    queue.clear()
    stop = client.post("/voice/queue/stop", json={}).json()
    assert stop["cancelled_session"] == session_id or stop["stopped"] is True
    queue.cancelled_sessions.clear()


def test_queue_clear(client):
    resp = client.post("/voice/queue/clear")
    assert resp.status_code == 200
    assert isinstance(resp.json()["cleared"], int)


def test_speakers_endpoint(client):
    resp = client.get("/voice/speakers")
    assert resp.status_code == 200
    assert resp.json()["speakers"] == {"firefly": "流萤 (Firefly)"}
