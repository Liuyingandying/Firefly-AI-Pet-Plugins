"""tju_info_retrieval 插件自测（可独立运行: python -m pytest tju_info_retrieval/tests）。

纯单元测试：契约归一化、状态机、错误分类、插件形态——不启动浏览器、
不需要外部工程、不需要 Firefly 宿主。
"""

from __future__ import annotations

import ast
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # 仓库根

from tju_info_retrieval import adapter  # noqa: E402


# ---------------------------------------------------------------- 契约归一化

def test_normalize_maps_bridge_fields():
    item = {
        "rank": 1,
        "title": "THz ISAC Survey",
        "abstract": "A survey on THz ISAC.",
        "database": "CNKI",
        "year": 2025,
        "detail_url": "https://example.org/paper",
    }
    result = adapter._normalize(item)
    assert result.title == "THz ISAC Survey"
    assert result.snippet == "A survey on THz ISAC."
    assert result.source == "CNKI"            # database 优先
    assert result.score is None               # 适配器从不编造评分
    assert result.metadata["rank"] == 1
    assert result.metadata["year"] == 2025
    assert "title" not in result.metadata and "abstract" not in result.metadata


def test_normalize_missing_fields_stay_none():
    result = adapter._normalize({"title": "  "})
    assert result.title == ""
    assert result.snippet is None or result.snippet == ""
    assert result.source is None


def test_normalize_source_fallback():
    result = adapter._normalize({"title": "t", "source": "Wanfang"})
    assert result.source == "Wanfang"


# ---------------------------------------------------------------- 错误分类

def test_auth_error_type_raises_auth_required():
    with pytest.raises(adapter.TjuAuthRequiredError):
        adapter._raise_classified({"ok": False, "error": "boom", "error_type": "AuthError"})


def test_login_text_raises_auth_required():
    with pytest.raises(adapter.TjuAuthRequiredError):
        adapter._raise_classified({"ok": False, "error": "登录状态已失效，请重新登录"})


def test_other_error_raises_unavailable():
    with pytest.raises(adapter.TjuRetrievalUnavailableError) as excinfo:
        adapter._raise_classified({"ok": False, "error": "Edge 未检测到"})
    assert not isinstance(excinfo.value, adapter.TjuAuthRequiredError)


# ---------------------------------------------------------------- 状态机（零副作用）

@pytest.fixture()
def isolated_project(tmp_path, monkeypatch):
    """fake 外部工程根 + 隔离登录快照根。"""
    root = tmp_path / "tju-research-assistant"
    root.mkdir()
    (root / "main.py").write_text("# external project entry\n", encoding="utf-8")
    monkeypatch.setattr(adapter, "PROJECT_ROOT", root)
    user_root = tmp_path / "user_data"
    monkeypatch.setenv("TEST_USER_DATA_ROOT", str(user_root))
    return root, user_root


def _snapshot_path(user_root: Path) -> Path:
    return user_root / "cache" / "tju_storage_state.json"


def test_status_error_when_root_unset(monkeypatch):
    monkeypatch.setattr(adapter, "PROJECT_ROOT", None)
    result = adapter.local_status()
    assert result["ok"] is False
    assert "TJU_INFO_RETRIEVAL_ROOT" in (result["error"] or "")


def test_status_error_when_project_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "PROJECT_ROOT", tmp_path / "nope")
    result = adapter.local_status()
    assert result["ok"] is False


def test_status_auth_required_without_snapshot(isolated_project):
    result = adapter.local_status()
    assert result["ok"] is True
    assert result["auth_ok"] is False          # AUTH_REQUIRED
    assert result["snapshot_age_days"] is None


def test_status_ready_with_fresh_snapshot(isolated_project):
    _, user_root = isolated_project
    snapshot = _snapshot_path(user_root)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text("{}", encoding="utf-8")  # mtime = now → 新鲜
    result = adapter.local_status()
    assert result["ok"] is True
    assert result["auth_ok"] is True           # READY
    assert result["snapshot_age_days"] is not None


def test_status_auth_required_with_stale_snapshot(isolated_project):
    _, user_root = isolated_project
    snapshot = _snapshot_path(user_root)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text("{}", encoding="utf-8")
    stale = time.time() - 40 * 86400           # 40 天前 → 过期
    os.utime(snapshot, (stale, stale))
    result = adapter.local_status()
    assert result["ok"] is True
    assert result["auth_ok"] is False


# ---------------------------------------------------------------- 插件形态（不导入宿主模块）

def test_plugin_file_declares_contract():
    plugin_src = (Path(__file__).resolve().parents[1] / "plugin.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(plugin_src)
    ids = {
        node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and getattr(node.targets[0], "id", "") == "PLUGIN_ID"
    }
    assert ids == {"tju-info-retrieval"}       # PluginLoader 白名单 id
    func_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert "create_plugin" in func_names       # PluginLoader 工厂契约
    for method in ("search", "open_login", "open_ui", "status"):
        assert method in func_names            # 宿主期待的能力面
