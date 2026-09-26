# TJU Bridge CLI 契约（适配器 ↔ tju-research-assistant）

对照源码：插件侧 `../adapter.py` ↔ 桥接侧
[tju-research-assistant `src/tju_info_retrieval/bridge.py`](https://github.com/Liuyingandying/tju-research-assistant/blob/main/src/tju_info_retrieval/bridge.py)。

每个请求 = 一个全新的隔离子进程（`shell=False` / timeout / UTF-8 / cwd=工程根 /
`PYTHONPATH=<root>/src`），无长驻进程。

## 统一约定

- **stdout**：单个 JSON 对象（UTF-8）；诊断/浏览器日志只进 stderr，绝不混入 stdout。
- **业务失败不产生非零退出码**：失败走 `{"ok": false, "error": ..., "error_type": ...}`；
  调用方读 JSON 优雅降级。
- **错误分类**：`error_type == "AuthError"` 或错误文案含「登录」→ 适配器抛
  `TjuAuthRequiredError`；其余 → `TjuRetrievalUnavailableError`。

## 命令契约

| command | 调用形式 | 适配器超时 | stdout data | 登录态影响 |
|---|---|---|---|---|
| health | `bridge health` | 20s | `{ok, version, edge, auth_profile_present, user_data_root, error}`：Edge 可执行文件探测 + 授权 profile 存在性 + 版本 | 无（只查文件存在） |
| auth_status | `bridge auth_status` | 40s | `{ok, auth_ok, state, error}`；`state ∈ {logged_in, not_logged_in, unknown,…}`。**会启动受控 Edge 只读探测门户页面**——适配器只在显式调用时使用，Quick Tools 面板刷新永不调用 | 只读，不填任何凭据 |
| auth | `bridge auth --timeout_s 300` | 330s | `{ok, auth_ok, state, error}`。打开受控 Edge 供**人工**完成统一身份认证；轮询页面（不导航、不干扰登录表单）；登录完成 / 浏览器被关闭 / 超时 三者之一返回 | 成功后持久化 profile，后续 search/auth_status 复用 |
| search | `bridge search --query <q> [--top_k 5] [--sources CNKI,Wanfang,IEEE]` | 150s | `{ok, query, count, results: [...], error}`。复用生产 SearchService + BrowserSession 同一管线；结束后只停止本次会话自己的 Playwright 运行时 | 需要有效校园授权；未登录返回带「登录」文案的失败 JSON |

search 单条结果字段（bridge `_result_to_dict` 归一化，缺失为 null）：
`rank, title, authors, source, year, detail_url, document_type, database, abstract, doi, keywords, venue, citation_count`。
适配器映射：`title→title`、`abstract→snippet`、`database|source→source`，
其余原样进入 `RetrievalResult.metadata`，永不修改桥接返回内容。

## 状态机（适配器 `status()`，零副作用）

| 状态 | 判定（纯本地，无子进程） |
|---|---|
| `OFFLINE` | Quick Tools 开关关闭 |
| `ERROR` | `TJU_INFO_RETRIEVAL_ROOT` 未配置，或工程目录 / `main.py` 不存在 |
| `AUTH_REQUIRED` | 工程在，但登录快照缺失或 mtime 距今 > 30 天 |
| `READY` | 工程在且快照新鲜（真实凭据校验延迟到实际使用时） |

## 环境变量

| 变量 | 作用 |
|---|---|
| `TJU_INFO_RETRIEVAL_ROOT` | **必需**。外部工程根目录（含 `main.py`、`src/`）。无内置默认路径 |
| `TJU_INFO_RETRIEVAL_PYTHON` | 可选。外部工程解释器显式覆盖（最高优先级，不校验直接采用） |
| `TEST_USER_DATA_ROOT` | 仅测试：登录态快照/用户数据根目录覆盖（隔离测试用，不进 fixture） |

## 解释器解析链（无硬编码路径）

优先级从高到低，逐个用 `python -c "import playwright"` 探测验证
（结果按 (解释器, 模块) 缓存；显式覆盖不校验）：

1. `TJU_INFO_RETRIEVAL_PYTHON` 环境变量
2. `<工程根>/.venv/Scripts/python.exe`、`<工程根>/venv/Scripts/python.exe`
3. 宿主 venv 的 **base** 解释器（`sys.base_prefix`）——手动终端启动实际解析到的那个
4. `sys.executable`（Firefly 自身解释器，兜底）

全部候选探测失败时返回首个存在者，让子进程自己的 stderr 作为最终事实来源。
