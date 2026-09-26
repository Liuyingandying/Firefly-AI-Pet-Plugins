"""TJU Info Retrieval — thin Quick Tools adapter.

Firefly
   ↓
Plugin Adapter
   ↓  (subprocess via bridge CLI)
TJU_Info_Retrieval (Source of Truth)

The adapter performs NO retrieval itself: it only proxies ``health`` /
``auth_status`` / ``auth`` / ``search`` through the original project's minimal
bridge CLI. No indexes, no ranking, no storage are reimplemented here.

Capability states (distinct):
    READY           plugin usable AND TJU auth valid
    AUTH_REQUIRED   plugin usable, but the TJU login has expired
    OFFLINE         Quick Tools Off (plugin stopped)
    ERROR           project / runtime environment broken
"""

from __future__ import annotations

import inspect
import logging
import os
import sys
from pathlib import Path

from core.extension_api import (
    EXT_STATUS_ERROR,
    EXT_STATUS_OFFLINE,
    EXT_STATUS_READY,
    FireflyExtension,
)
from core.quick_tools import QuickToolManifest

import tju_info_retrieval.adapter as adapter  # noqa: E402 - sibling module

PLUGIN_ID = "tju-info-retrieval"
PLUGIN_VERSION = "0.1.0"

EXT_STATUS_AUTH_REQUIRED = "AUTH_REQUIRED"

log = logging.getLogger("firefly.tju_plugin")


class TjuInfoRetrievalExtension(FireflyExtension):
    capabilities = ("retrieval",)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active = False

    # -- manifest -----------------------------------------------------------

    @property
    def manifest(self) -> QuickToolManifest:
        return QuickToolManifest(
            id=PLUGIN_ID,
            name="TJU Info Retrieval",
            description="天津大学信息检索系统",
            icon="search",
            version=PLUGIN_VERSION,
            capabilities=self.capabilities,
            min_api="2",
            author="Firefly",
        )

    @property
    def capability(self) -> str:
        return "本地信息检索 · 结果召回 · 结构化查询"

    @property
    def capability_note(self) -> str:
        return "桥接独立工程 TJU_Info_Retrieval（原工程为 Source of Truth）"

    # -- lifecycle ----------------------------------------------------------

    def status(self) -> str:
        """Distinct capability state. Never raises; **no launch side effects**.

        Uses the pure-local ``adapter.local_status()`` (project files + the
        persisted login snapshot). It must NEVER call the bridge subprocesses
        here: ``bridge_auth_status`` opens a real controlled Edge window on
        the TJU portal, so a mere Quick Tools panel refresh used to spawn
        python/Playwright/Edge processes. Real credential validation happens
        at actual use (search / open / manual login)."""
        if not self._active:
            return EXT_STATUS_OFFLINE
        try:
            local = adapter.local_status()
        except Exception:  # noqa: BLE001 - status must never crash the card
            return EXT_STATUS_ERROR
        if not local.get("ok"):
            return EXT_STATUS_ERROR
        if local.get("auth_ok"):
            return EXT_STATUS_READY
        return EXT_STATUS_AUTH_REQUIRED

    def start(self) -> None:
        self._active = True
        self.publish_status(self.status(), "ready")

    def stop(self) -> None:
        self._active = False
        # No long-lived process: every request is a fresh one-shot subprocess.
        self.publish_status(EXT_STATUS_OFFLINE, "stopped")

    def shutdown(self) -> None:
        self._active = False
        pass  # nothing resident to release

    # -- capability surface (called by the runner through app.py wiring) ----

    def search(self, query: str, top_k: int = 5):
        """Run one real search through the original project. Returns a list of
        :class:`RetrievalResult`. Raises :class:`TjuAuthRequiredError` when the
        TJU login is expired (the caller renders the re-login hint). The caller
        (runner) checks the capability gate BEFORE invoking this."""
        return adapter.bridge_search(query, top_k=top_k)

    def open_login(self) -> str:
        """Open the controlled Edge for a MANUAL TJU login. Never touches user
        credentials; returns a short user-facing outcome."""
        try:
            result = adapter.bridge_auth(timeout_s=300)
        except adapter.TjuRetrievalUnavailableError as exc:
            return f"（无法打开受控浏览器：{str(exc)[:120]}）"
        if result.get("auth_ok"):
            return "登录状态已恢复，可以重新进行检索。"
        return "已打开受控浏览器，请在天津大学登录页完成登录。登录完成后可以重新发送检索指令。"

    def _log_identity(self, entry: str) -> None:
        """Prove WHICH plugin code/instance handled this click (dev diagnostics).

        ``inspect.getfile(type(self))`` exposes a stale module cache or a
        duplicate plugin copy immediately — the loaded class's real file.
        """
        try:
            plugin_file = inspect.getfile(type(self))
        except (TypeError, OSError):
            plugin_file = "?"
        log.info(
            "tju click entry=%s plugin_file=%s adapter_file=%s "
            "project_root=%s sys.executable=%s pid=%d",
            entry, plugin_file, getattr(adapter, "__file__", "?"),
            adapter.PROJECT_ROOT, sys.executable, os.getpid(),
        )

    def open(self) -> str:
        """Quick Tools「打开」/ 科研助手 / 聊天命令的统一入口：启动原独立 GUI。

        Explicit user action — independent of the On/Off capability gate (the
        original project is a standalone tool the user actively opens; the gate
        only controls Firefly's own background ``search``). Never touches
        credentials."""
        self._log_identity("quick_tools.open")
        return self.open_ui()

    def open_ui(self) -> str:
        """Launch the original TJU desktop GUI. Returns a user-facing message.

        Uses the honest launcher result (startup probe + env scrub): a child
        that dies immediately is NEVER reported as opened."""
        self._log_identity("open_ui")
        result = adapter.open_gui()
        log.info(
            "tju open_gui result status=%s pid=%s detail=%s",
            result.status, result.pid, (result.detail or "")[:200],
        )
        if result.status == "opened":
            return "TJU Info Retrieval 已打开。"
        if result.status == "already_running":
            return "TJU Info Retrieval 已经在运行。"
        if result.status in ("launch_failed", "project_not_found", "python_not_found"):
            # 具体 stderr 只进开发日志（adapter 已写入 gui log），UI 只给简洁文案。
            return "TJU Info Retrieval 启动失败，请检查运行环境。"
        return "TJU Info Retrieval 启动失败，请检查运行环境。"


def create_plugin(parent=None) -> TjuInfoRetrievalExtension:
    return TjuInfoRetrievalExtension(parent)