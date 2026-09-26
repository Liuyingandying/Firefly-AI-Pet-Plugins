# tju_info_retrieval — TJU 信息检索插件（薄适配器）

Firefly Quick Tools 的天津大学信息检索入口。本插件**自身零检索逻辑**：所有检索能力
（CNKI 等数据源、受控浏览器登录态）归属外部工程
[tju-research-assistant](https://github.com/Liuyingandying/tju-research-assistant)，
本插件只做配置、subprocess 桥接、超时与 JSON 解析、状态归一化和错误隔离。

接口契约全文见 [INTERFACE.md](INTERFACE.md)；bridge 命令级协议见
[docs/TJU_BRIDGE_CONTRACT.md](docs/TJU_BRIDGE_CONTRACT.md)。

```
Firefly Agent / Quick Tools
   ↓
本插件（宿主进程内适配器）
   ↓ 每个请求 = 一个全新隔离子进程
python -m tju_info_retrieval.bridge <command>   ← 外部工程的 Bridge CLI
   ↓
tju-research-assistant（检索 / 登录态 / GUI 的唯一实现方）
```

## 能力面

| 入口 | 行为 |
|---|---|
| `search(query, top_k=5)` | 走 bridge `search`；登录过期抛 `TjuAuthRequiredError`（聊天侧渲染重新登录提示） |
| `open_login()` | 打开受控 Edge 进行**手动**登录；全程不读取/不存储任何凭据 |
| `open()` / `open_ui()` | 启动外部工程独立 GUI（`python main.py`），独立于 On/Off 开关 |
| `status()` | 纯本地状态查询，**零副作用**（绝不拉起浏览器） |

状态四态：`READY`（可用且登录新鲜）/ `AUTH_REQUIRED`（登录缺失或 >30 天快照）/
`OFFLINE`（Quick Tools 关闭）/ `ERROR`（外部工程或环境缺失）。

## 安装

1. **克隆外部工程**（检索能力的真实载体）：

   ```bash
   git clone https://github.com/Liuyingandying/tju-research-assistant.git
   ```

   按该工程 README 安装其依赖（Python 3.10+、`pip install -r requirements.txt`、
   Playwright + Microsoft Edge）。本插件不内置任何默认路径。

2. **设置环境变量**（唯一必需配置）：

   ```
   TJU_INFO_RETRIEVAL_ROOT=<tju-research-assistant 克隆目录>
   # 可选：显式指定外部工程解释器（默认自动探测：项目 venv → 宿主 venv 的 base 解释器）
   # TJU_INFO_RETRIEVAL_PYTHON=<python.exe>
   ```

3. **安装插件**：把 `tju_info_retrieval/` 目录复制到 Firefly 插件运行时根
   `%LOCALAPPDATA%\FireflyAI\plugins\`，重启宿主，在 Quick Tools 中开启。

未配置 `TJU_INFO_RETRIEVAL_ROOT` 时插件**不会崩溃**：status 报 `ERROR`，
search/open_ui 返回带克隆指引的错误信息（fail-fast with instructions）。

## 使用（聊天触发词，保守匹配）

- `用TJU信息检索查 THz ISAC` / `用信息检索系统搜索 …` → 检索
- `用TJU信息检索重新登录` → 打开受控浏览器手动登录
- `打开TJU信息检索` / Quick Tools 卡片「打开」→ 启动独立 GUI

## 隐私与凭据边界

- 适配器**全程不读、不存、不传**任何账号凭据；登录只走受控 Edge 的手动流程。
- 登录态（storage state / Edge profile）只归属外部工程；本插件最多查看快照文件的
  修改时间（判断新鲜度），绝不读取内容。
- 检索面向 CNKI 等校内资源，需要你持有对应机构的有效授权。

## 自测

```bash
python -m pytest tju_info_retrieval/tests -q
```

（纯单元测试：契约归一化、状态机、错误分类——不启动浏览器、不需要外部工程。）
