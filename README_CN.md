<p align="right">
  <a href="README.md">English</a> · <b>中文</b>
</p>

<p align="center">
  <a href="https://spc-batch-monito-tgnpmprhsqmpuxr4q6wktu.streamlit.app/"><img src="https://img.shields.io/badge/在线演示-Streamlit-00BFA5?style=for-the-badge&logo=streamlit&logoColor=white" alt="在线演示"></a>
  <a href="https://github.com/newbison/spc-batch-monitor"><img src="https://img.shields.io/badge/GitHub-开源-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white" alt="Plotly">
  <img src="https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy">
  <img src="https://img.shields.io/badge/SciPy-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white" alt="SciPy">
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest">
</p>

<h1 align="center">🔥 FORGE AI — SPC 平台</h1>
<h3 align="center">统计过程控制与实验设计</h3>
<h4 align="center" style="color:#8895A8;font-weight:400">
  将批次数据转化为工艺智能。从控制图到 DOE 优化，一站式完成。
</h4>

<p align="center">
  <b>上传数据 → 查看控制限与违规 → 分析能力 → 设计实验 → 优化</b><br>
  X-bar & R 图 · Western Electric 规则 · 过程能力分析 · 筛选与全因子实验 · RSM · 合意性优化
</p>

---

![应用截图](image/README/1778922140812.png)

---

## 这是什么？

无论你是监控生产质量的**工艺工程师**、优化配方的**研发科学家**，还是跟踪 KPI 的**质量经理**——挑战都是一样的：

> *你需要知道过程是否受控、是否有能力，以及改进方向——而不需要在六个不同的工具之间来回切换。*

生产工程师花数小时用 Excel 制作 X-bar 和 R 图。研发科学家因为 DOE 软件太贵或太复杂，只能做单因素实验。质量经理从三个系统拉数据才能得到一个仪表盘视图。

**FORGE AI — SPC 平台解决了这个问题。一个工具完成监控、分析和优化。**

```
  ┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌───────────────┐
  │             │     │                  │     │                  │     │               │
  │   上传      │ ──▶ │  SPC 分析        │ ──▶ │  DOE 设计与      │ ──▶ │  管理者        │
  │   批次数据  │     │  · 控制图        │     │  分析            │     │  仪表盘        │
  │             │     │  · 过程能力      │     │  · 因子实验      │     │  · KPI        │
  │             │     │  · 规则检查      │     │  · RSM / 响应曲面 │     │  · 趋势       │
  └─────────────┘     └──────────────────┘     └──────────────────┘     └───────────────┘
```

---

## 功能特性

### 多角色平台

| 角色 | 权限 | 功能 |
|------|------|------|
| 👨‍🔬 **操作员** | 数据录入 | CSV 上传、手动录入、查看/编辑当日批次 |
| 🔧 **工程师** | SPC + DOE | 控制图、过程能力、DOE 向导（定义→设计→采集→分析→优化） |
| 📊 **管理者** | 仪表盘 | KPI 卡片、状态表（🟢/🟡/🔴/⚪）、趋势分析 |
| ⚙️ **管理员** | 数据管理 | 筛选、编辑、删除、导出、导入——完整 CRUD |

### SPC — 统计过程控制

- **X-bar 和 R 控制图**，支持动态子组大小（n=2–25），基于 ASTM E2587 常数
- **Western Electric 规则** — 规则 1（超出 3σ）、规则 2（3 点中 2 点超出 2σ）、规则 4（8 点连续同侧）、趋势（6 点连续上升/下降）
- **趋势分析** — 运行图、移动极差图、滚动 Ppk（滑动窗口）
- **过程能力** — Pp、Ppk、PPM，带直方图和规格线（支持单侧规格，NaN 表示无限制）
- **批间箱线图**，叠加规格线
- **PPTX 报告导出** — 自动生成含图表和文字总结的 SPC 报告

### DOE — 实验设计

- **全因子与部分因子设计** — 2^k 全因子、2^(k-p) 部分因子（分辨率 IV/V）、Box-Behnken RSM
- **无外部 DOE 库依赖** — 纯 NumPy 自包含因子生成器
- **回归分析** — 含主效应 + 二阶交互的线性模型，以及 statsmodels 的 RSM 二次模型
- **曲率检测** — 中心点与因子点响应的双样本 t 检验
- **可视化** — 主效应图、帕累托效应图、等高线图、3D 响应曲面
- **Derringer-Suich 合意性** — 多响应优化，含预测区间和多起点 scipy 优化
- **会话持久化** — 跨会话保存、恢复和迭代 DOE 实验

---

## 快速开始

```bash
git clone https://github.com/newbison/spc-batch-monitor.git
cd spc-batch-monitor
pip install -r requirements.txt
streamlit run app.py
```

就这样。首次启动时自动加载示例数据。从侧边栏选择应用（SPC 或 DOE），然后从顶部角色栏选择你的角色。

无需外部 DOE 库——因子生成器自包含，支持 Python 3.9+。

---

## 监控参数

| 参数 | 重复数 | 下限 | 上限 | 单位 |
|------|--------|------|------|------|
| 粘度 (Viscosity) | 5 | 0.6 | 1.5 | N/mm |
| 密度 (Density) | 15 | 1000.0 | — | — |
| 硬度 (Hardness) | 8 | 10.0 | 50.0 | mm |
| 弹性 (Elasticity) | 10 | 5.0 | 20.0 | g/inch |

子组大小（5–15 可变）通过每行非 NaN 的重复数自动检测。

---

## 架构

```
app.py (Hub 壳)
 ├── SPC 子应用
 │   ├── 角色栏 + 侧边栏（配方/参数选择）
 │   ├── UI（按角色的 Streamlit 页面）
 │   │   └─> 可视化（Plotly 图表构建器）
 │   │        └─> SPC 引擎（纯 Python，无框架依赖）
 │   │             └─> 数据访问（仓库模式 → SQLite）
 │   │                  └─> 验证（写入前行级检查）
 │   └── 报告（python-pptx + Kaleido）
 │
 └── DOE 子应用
     ├── _factorial.py  — 自包含 fullfact、fracfact、bbdesign
     ├── designs.py      — 因子 + Box-Behnken 设计矩阵
     ├── analysis.py     — 线性 + RSM 回归（statsmodels）
     ├── optimization.py — Derringer-Suich 合意性（scipy）
     └── persistence.py  — SQLite 会话 CRUD（JSON 列）
```

所有引擎都是**框架无关的**——它们接收 DataFrame 或数组，返回普通字典。仓库模式抽象了存储层，可在不触及 UI 或业务逻辑的前提下将 SQLite 替换为 PostgreSQL。

---

## 技术栈

| 层 | 技术 |
|----|------|
| **UI** | Streamlit |
| **图表** | Plotly |
| **SPC 引擎** | 纯 Python（NumPy/SciPy） |
| **DOE 引擎** | NumPy、statsmodels、scipy.optimize |
| **报告** | python-pptx、Kaleido |
| **数据库** | SQLite（WAL 模式、仓库模式） |
| **测试** | Pytest（90+ 测试） |

---

## 测试

```bash
pytest tests/ -v
```

90+ 测试覆盖：
- 控制限（X-bar & R，动态 n）
- Western Electric 规则（1、2、4、趋势）
- 过程能力计算（Pp、Ppk、PPM、单侧规格）
- 数据验证（写入前拒绝无效行）
- SQLite 仓库操作（CRUD、去重、自动迁移）
- 端到端集成（SPC 流水线）
- DOE 设计生成（全因子、部分因子、Box-Behnken）
- DOE 回归分析（线性、RSM、过参数化防护）
- DOE 合意性优化（基于 RMSE 的预测区间）
- DOE 持久化（JSON 列、白名单验证）
