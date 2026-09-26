"""TJU Info Retrieval — thin bridge client + result model.

This adapter is the ONLY place that talks to the external retrieval project
``tju-research-assistant`` (https://github.com/Liuyingandying/tju-research-assistant,
via its minimal bridge CLI). That project is the source of truth: no retrieval
logic, index, ranking or storage is reimplemented here. Every request spawns a
fresh, isolated subprocess (shell=False / timeout / UTF-8 / cwd=project root).

Project root resolution: **environment variable only** —
``TJU_INFO_RETRIEVAL_ROOT`` must point at a clone of the external project
(containing ``main.py`` and ``src/tju_info_retrieval/bridge.py``). No default
path is built in; without the variable the plugin reports ``ERROR`` with the
exact setup hint.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

log = logging.getLogger("firefly.tju_plugin")

# Single source of the external project location: environment variable only,
# no built-in default path (the plugin fails fast with setup instructions).
PROJECT_ROOT_ENV = "TJU_INFO_RETRIEVAL_ROOT"
SETUP_HINT = (
    "TJU 信息检索外部工程未配置：请 git clone "
    "https://github.com/Liuyingandying/tju-research-assistant 并设置环境变量 "
    "TJU_INFO_RETRIEVAL_ROOT 指向其克隆目录（含 main.py 与 src/）。"
)
_ROOT = os.environ.get(PROJECT_ROOT_ENV, "").strip()
PROJECT_ROOT: Path | None = Path(_ROOT).resolve() if _ROOT else None

# Explicit interpreter override (highest priority when set).
PROJECT_PYTHON_ENV = "TJU_INFO_RETRIEVAL_PYTHON"

BRIDGE = "tju_info_retrieval.bridge"
_HEALTH_TIMEOUT_S = 20
_SEARCH_TIMEOUT_S = 150

# Local, side-effect-free status (see local_status): a persisted login snapshot
# older than this is reported as AUTH_REQUIRED (real validation happens on use).
_AUTH_SNAPSHOT_STALE_DAYS = 30


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Normalized result (thin). Missing fields stay None."""

    title: str
    snippet: str | None = None
    source: str | None = None
    score: float | None = None
    metadata: dict = field(default_factory=dict)


class TjuRetrievalUnavailableError(RuntimeError):
    """Raised when the bridge cannot run or the original project fails."""


class TjuAuthRequiredError(TjuRetrievalUnavailableError):
    """Raised when the bridge reports the TJU login has expired (AUTH_REQUIRED)."""


def project_root() -> Path | None:
    return PROJECT_ROOT


def local_status() -> dict:
    """Side-effect-free plugin status: pure local file checks.

    MUST stay free of subprocess / Playwright / browser launches — the Quick
    Tools popover calls this on every open just to render the card state
    (READY / AUTH_REQUIRED / ERROR). The previous implementation spawned the
    bridge ``auth_status`` subprocess, which opened a real controlled Edge
    window on the TJU portal every time the panel was shown.

    Checks (all local, stdlib only):
    - ``TJU_INFO_RETRIEVAL_ROOT`` set, project root + main.py exist
      → else ``ok=False`` (ERROR)
    - persisted login snapshot exists and is fresh (≤ _AUTH_SNAPSHOT_STALE_DAYS)
      → ``auth_ok=True`` (READY)
    - snapshot missing/expired → AUTH_REQUIRED

    Real credential validation still happens at actual use (search / auth).
    """
    result = {
        "ok": False,
        "auth_ok": False,
        "snapshot_age_days": None,
        "error": None,
    }
    if PROJECT_ROOT is None:
        result["error"] = SETUP_HINT
        return result
    if not PROJECT_ROOT.is_dir() or not (PROJECT_ROOT / "main.py").is_file():
        result["error"] = f"project missing under {PROJECT_ROOT}"
        return result
    result["ok"] = True
    try:
        snapshot = _storage_state_snapshot()
        if snapshot.is_file():
            age_days = (time.time() - snapshot.stat().st_mtime) / 86400.0
            result["snapshot_age_days"] = round(age_days, 2)
            result["auth_ok"] = age_days <= _AUTH_SNAPSHOT_STALE_DAYS
    except Exception as exc:  # noqa: BLE001 - status must never raise
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _storage_state_snapshot() -> Path:
    """Persisted TJU login snapshot path, resolved LOCALLY.

    Mirrors the external project's ``app_paths.storage_state_path()`` with
    pure pathlib — deliberately NOT imported, because inside the Firefly
    process the name ``tju_info_retrieval`` resolves to THIS plugin package
    (which has no app_paths submodule).
    """
    assert PROJECT_ROOT is not None  # callers check first
    override = os.environ.get("TEST_USER_DATA_ROOT", "").strip()
    if getattr(sys, "frozen", False) or override:
        if override:
            base = Path(override)
        else:
            local = os.environ.get("LOCALAPPDATA", "").strip()
            base = Path(local) if local else Path.home() / "AppData" / "Local"
            base = base / "TJU_Info_Retrieval"
        return base / "cache" / "tju_storage_state.json"
    return PROJECT_ROOT / "data" / "tju_storage_state.json"


def bridge_health() -> dict:
    """Run the bridge `health` command; never raises (JSON or degraded dict)."""
    try:
        payload = _run(["health"], timeout=_HEALTH_TIMEOUT_S)
    except TjuRetrievalUnavailableError as exc:
        return {"ok": False, "error": str(exc)}
    return payload


def bridge_auth_status() -> dict:
    """Probe the CURRENT TJU auth state; never raises (degraded dict)."""
    try:
        payload = _run(["auth_status"], timeout=40)
    except TjuRetrievalUnavailableError as exc:
        return {"ok": False, "auth_ok": False, "state": "unknown", "error": str(exc)}
    return payload


def bridge_auth(timeout_s: int = 300) -> dict:
    """Open the controlled Edge for a MANUAL TJU login; returns when logged in,
    the browser closes, or the timeout elapses."""
    return _run(["auth", "--timeout_s", str(timeout_s)], timeout=timeout_s + 30)


def bridge_search(query: str, top_k: int = 5) -> list[RetrievalResult]:
    """Run one real search through the original project's bridge CLI."""
    payload = _run(
        ["search", "--query", query, "--top_k", str(top_k), "--sources", "CNKI"],
        timeout=_SEARCH_TIMEOUT_S,
    )
    if not payload.get("ok"):
        _raise_classified(payload)
    return [_normalize(item) for item in payload.get("results", [])]


def _raise_classified(payload: dict) -> None:
    """Raise the adapter error matching one failed bridge payload.

    ``AuthError`` / 登录-related messages → :class:`TjuAuthRequiredError`
    (the caller renders the re-login hint); anything else →
    :class:`TjuRetrievalUnavailableError`.
    """
    error = str(payload.get("error") or "检索失败")
    error_type = str(payload.get("error_type") or "")
    if error_type == "AuthError" or "登录状态失效" in error or "登录" in error[:60]:
        raise TjuAuthRequiredError(error)
    raise TjuRetrievalUnavailableError(error)


# The GUI process WE spawned (only our own; never a global python scan).
_GUI_PROCESS = None

# Startup probe: how long to wait before deciding a freshly-spawned GUI either
# started (poll() is None) or died immediately (poll() is not None).
_GUI_STARTUP_PROBE_S = 0.7


@dataclass(frozen=True, slots=True)
class GuiLaunchResult:
    """Unambiguous outcome of one GUI launch attempt."""

    status: str  # opened | already_running | launch_failed | project_not_found | python_not_found
    pid: int | None = None
    detail: str = ""  # dev-facing stderr snippet — never shown raw to the user


# Cached best-effort "can this interpreter import X" results (path → bool|None).
_PYTHON_IMPORT_CACHE: dict[str, bool | None] = {}


def _python_can_import(python: Path, module: str = "playwright") -> bool | None:
    """Best-effort, cached probe: ``python -c "import module"`` succeeds?

    Returns True / False, or None when the probe itself could not run.
    Never raises; the probe result is cached per (interpreter, module).
    """
    cache_key = f"{python}|{module}"
    if cache_key in _PYTHON_IMPORT_CACHE:
        return _PYTHON_IMPORT_CACHE[cache_key]
    try:
        proc = subprocess.run(
            [str(python), "-c", f"import {module}"],
            capture_output=True,
            timeout=20,
        )
        result: bool | None = proc.returncode == 0
    except Exception:  # noqa: BLE001 - probe must never break the launcher
        result = None
    _PYTHON_IMPORT_CACHE[cache_key] = result
    return result


def _candidate_project_pythons() -> list[Path]:
    """Ordered candidate interpreters for the ORIGINAL project (deduped).

    1. ``TJU_INFO_RETRIEVAL_PYTHON`` (explicit override — honored unvalidated)
    2. ``PROJECT_ROOT/.venv`` / ``venv`` (the project's own interpreter)
    3. ``sys.base_prefix`` interpreter — when Firefly itself runs inside a
       venv, this is that venv's BASE interpreter (e.g. the conda python the
       user actually uses). This is the interpreter a manual
       ``python main.py`` would resolve to, without hardcoding any path.
    4. ``sys.executable`` (Firefly's own interpreter — last resort)
    """
    candidates: list[Path] = []
    override = os.environ.get(PROJECT_PYTHON_ENV, "").strip()
    if override:
        candidates.append(Path(override))
    if PROJECT_ROOT is not None:
        candidates.extend([
            PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
            PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
        ])
    # Running inside a venv → base interpreter first (it is what a manual
    # terminal launch uses; the venv itself may lack project deps).
    base_python = Path(sys.base_prefix) / "python.exe"
    if base_python != Path(sys.executable):
        candidates.append(base_python)
    candidates.append(Path(sys.executable))
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = os.path.normcase(str(candidate))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_project_python() -> Path | None:
    """The Python the ORIGINAL project should run with (single source).

    Priority: explicit env override → project venvs → the running venv's
    BASE interpreter → ``sys.executable``. All candidates except the explicit
    override are validated to actually import ``playwright`` (the GUI's hard
    dependency); the first interpreter that passes (or cannot be probed) wins.
    If every existing candidate fails validation, the first existing one is
    returned anyway so the child's own stderr stays the source of truth.
    """
    candidates = _candidate_project_pythons()
    existing = [c for c in candidates if c.is_file()]
    if not existing:
        return None
    fallback = existing[0]
    for candidate in existing:
        if candidate == existing[0] and \
                os.environ.get(PROJECT_PYTHON_ENV, "").strip():
            return candidate  # explicit override: honored unvalidated
        verdict = _python_can_import(candidate)
        if verdict is not False:
            log.debug(
                "resolve_project_python chose %s (import probe=%s)",
                candidate, verdict,
            )
            return candidate
        log.warning(
            "resolve_project_python skipped %s: cannot import playwright",
            candidate,
        )
    return fallback


def _gui_log_path() -> Path:
    """Startup log for the GUI child's stdout/stderr (dev diagnostics)."""
    assert PROJECT_ROOT is not None  # callers check first
    log_dir = PROJECT_ROOT / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "tju_info_retrieval_gui.log"


_LOG_MAX_BYTES = 512 * 1024      # keep the attempt log bounded
_LOG_KEEP_BYTES = 64 * 1024      # tail preserved when rotating


def _open_attempt_log(log_path: Path, *, python: Path, command: list[str]) -> object | None:
    """Open the attempt log in append mode and write one attempt separator.

    The header records everything needed to reconstruct this exact launch:
    timestamp, attempt id, interpreter, command, cwd, parent pid and the
    child-env keys removed by the scrub. Rotates the file when it grows past
    ``_LOG_MAX_BYTES`` (keeps the last ``_LOG_KEEP_BYTES``).
    """
    try:
        if log_path.is_file() and log_path.stat().st_size > _LOG_MAX_BYTES:
            data = log_path.read_bytes()[-_LOG_KEEP_BYTES:]
            log_path.write_bytes(data)
    except OSError:
        pass
    try:
        handle = open(log_path, "a", encoding="utf-8", errors="replace")
    except OSError:
        return None
    env_keys_removed = sorted(
        k for k in os.environ
        if k.startswith("QT_QPA_")
    )
    in_venv = Path(sys.prefix) != Path(sys.base_prefix)
    handle.write(
        "\n"
        "================================================\n"
        f"timestamp={datetime.now().isoformat(timespec='seconds')}\n"
        f"attempt_id={uuid.uuid4().hex[:12]}\n"
        f"python={python}\n"
        f"sys.executable={sys.executable}\n"
        f"sys.prefix={sys.prefix} (venv={in_venv})\n"
        f"sys.base_prefix={sys.base_prefix}\n"
        f"command={command!r}\n"
        f"cwd={PROJECT_ROOT}\n"
        f"parent_pid={os.getpid()}\n"
        f"env_keys_removed={env_keys_removed}\n"
        "================================================\n",
    )
    handle.flush()
    return handle


def diagnose_gui_launch() -> dict:
    """Structured dev diagnostic: one REAL launch attempt through the exact
    production path (resolve → validate → Popen → probe), returning what
    actually happened. Not a permanent UI surface.
    """
    python = resolve_project_python()
    diag: dict = {
        "adapter_file": str(Path(__file__)),
        "plugin_package_dir": str(Path(__file__).parent),
        "python": str(python or ""),
        "python_candidates": [str(c) for c in _candidate_project_pythons()],
        "python_import_probe": {
            str(c): _python_can_import(c)
            for c in _candidate_project_pythons() if c.is_file()
        },
        "sys.executable": sys.executable,
        "sys.prefix": sys.prefix,
        "sys.base_prefix": sys.base_prefix,
        "project_root": str(PROJECT_ROOT),
        "main_exists": bool(PROJECT_ROOT and (PROJECT_ROOT / "main.py").is_file()),
        "python_exists": bool(python and python.is_file()),
        "log_path": str(_gui_log_path()) if PROJECT_ROOT is not None else "",
    }
    result = open_gui()
    diag["launch_status"] = result.status
    diag["child_pid"] = result.pid
    if result.pid is not None and result.status == "opened":
        proc = _GUI_PROCESS
        diag["poll_after_probe"] = proc.poll() if proc is not None else None
    diag["stderr_tail"] = result.detail
    return diag


def open_gui() -> GuiLaunchResult:
    """Launch the ORIGINAL TJU desktop GUI (``python main.py``) with an honest
    startup probe.

    - Validates the project root + ``main.py`` before spawning.
    - Uses :func:`resolve_project_python` (the running venv's BASE interpreter
      is preferred over Firefly's own venv python — the base interpreter is
      what a manual terminal launch resolves to, and the one that has the
      project's dependencies such as playwright).
    - Scrubs ``QT_QPA_*`` from the child environment so a Firefly session that
      runs with ``QT_QPA_PLATFORM=offscreen`` cannot make the GUI open
      invisibly.
    - Waits ~``_GUI_STARTUP_PROBE_S`` and only reports ``opened`` when the
      child is still alive; a child that exits immediately is ``launch_failed``
      with its stderr captured to the attempt log.
    - ``already_running`` only when the process WE spawned is still alive; a
      stale (exited) process object is cleared so it can be relaunched.
    """
    global _GUI_PROCESS
    if _GUI_PROCESS is not None:
        if _GUI_PROCESS.poll() is None:
            return GuiLaunchResult(status="already_running", pid=_GUI_PROCESS.pid)
        _GUI_PROCESS = None  # 旧进程已退出——允许重新启动

    if PROJECT_ROOT is None:
        return GuiLaunchResult(status="project_not_found", detail=SETUP_HINT)
    if not PROJECT_ROOT.is_dir():
        return GuiLaunchResult(
            status="project_not_found", detail=f"PROJECT_ROOT={PROJECT_ROOT}"
        )
    if not (PROJECT_ROOT / "main.py").is_file():
        return GuiLaunchResult(
            status="launch_failed", detail=f"main.py missing under {PROJECT_ROOT}"
        )
    python = resolve_project_python()
    if python is None:
        return GuiLaunchResult(status="python_not_found")

    env = dict(os.environ)
    src = PROJECT_ROOT / "src"
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    # 关键：不继承 offscreen 等 Qt 平台强制（否则 GUI 存活但无窗口）。
    for key in [k for k in env if k.startswith("QT_QPA_")]:
        env.pop(key, None)

    command = [str(python), "main.py"]
    log_path = _gui_log_path()
    log.debug(
        "open_gui adapter=%s project=%s python=%s pid=%d",
        Path(__file__), PROJECT_ROOT, python, os.getpid(),
    )
    handle = _open_attempt_log(log_path, python=python, command=command)
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            shell=False,
            stdout=handle,
            stderr=handle,
        )
    except Exception as exc:  # noqa: BLE001 - launch failure must not crash Firefly
        if handle is not None:
            try:
                handle.write(f"POPN_FAILED={type(exc).__name__}: {exc}\n")
                handle.close()
            except OSError:
                pass
        return GuiLaunchResult(
            status="launch_failed", detail=f"{type(exc).__name__}: {exc}"
        )
    finally:
        if handle is not None:
            try:
                handle.flush()
            except (OSError, ValueError):
                pass

    _GUI_PROCESS = proc
    # 轻量启动探测：等待短暂时间，只有仍 alive 才算 opened。
    _time_sleep = time.sleep
    _time_sleep(_GUI_STARTUP_PROBE_S)
    poll = proc.poll()
    log.debug("open_gui child_pid=%s poll_after_probe=%s", proc.pid, poll)
    if poll is None:
        if handle is not None:
            try:
                handle.write(f"child_pid={proc.pid} probe=alive\n")
                handle.flush()
                handle.close()
            except OSError:
                pass
        return GuiLaunchResult(status="opened", pid=proc.pid)
    # 子进程立即退出：把真实原因写入开发日志（不塞进聊天）。
    try:
        stderr_tail = log_path.read_text(encoding="utf-8", errors="replace")[-2000:]
    except OSError:
        stderr_tail = ""
    if handle is not None:
        try:
            handle.write(
                f"child_pid={proc.pid} exit_code={proc.returncode} "
                "probe=exited\n",
            )
            handle.flush()
            handle.close()
        except OSError:
            pass
    _GUI_PROCESS = None
    return GuiLaunchResult(
        status="launch_failed",
        pid=proc.pid,
        detail=f"exit={proc.returncode} stderr={stderr_tail.strip()[:1000]}",
    )


def _run(args: list[str], *, timeout: int) -> dict:
    if PROJECT_ROOT is None or not PROJECT_ROOT.is_dir():
        raise TjuRetrievalUnavailableError(SETUP_HINT)
    src = PROJECT_ROOT / "src"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    # Bridge 子进程与 GUI 用同一个解析器（Firefly venv 缺 playwright，
    # 基础解释器才是手动终端启动时的那个）。
    python = resolve_project_python() or Path(sys.executable)
    try:
        proc = subprocess.run(
            [str(python), "-m", BRIDGE, *args],
            cwd=str(PROJECT_ROOT),
            env=env,
            shell=False,
            capture_output=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TjuRetrievalUnavailableError("检索超时，请稍后再试。") from None
    except FileNotFoundError:
        raise TjuRetrievalUnavailableError("Python 环境不可用。") from None
    try:
        payload = json.loads(proc.stdout or "{}")
    except ValueError:
        raise TjuRetrievalUnavailableError("TJU 信息检索返回了无效结果。") from None
    if not isinstance(payload, dict):
        raise TjuRetrievalUnavailableError("TJU 信息检索返回了无效结果。")
    return payload


def _normalize(item: dict) -> RetrievalResult:
    """Map one bridge result into the thin RetrievalResult (never mutates)."""
    title = str(item.get("title") or "").strip()
    snippet = item.get("abstract") or None
    source = item.get("database") or item.get("source") or None
    metadata = {
        key: value
        for key, value in item.items()
        if key not in ("title", "abstract") and value is not None
    }
    return RetrievalResult(
        title=title,
        snippet=str(snippet).strip() if isinstance(snippet, str) else str(snippet or ""),
        source=str(source) if source else None,
        score=None,
        metadata=metadata,
    )


__all__ = [
    "PROJECT_ROOT",
    "SETUP_HINT",
    "RetrievalResult",
    "TjuRetrievalUnavailableError",
    "bridge_health",
    "bridge_search",
    "local_status",
    "project_root",
]
