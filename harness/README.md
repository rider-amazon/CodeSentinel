# Harness —— 工作流约束

> 把规则、禁令、检查脚本放在一起，作为工作流约束（Harness）。
> 本目录**已随仓库分发**（规则/脚本/模板/文档入库；plan/execute/verify 的运行态 JSON 与 work/output 不入库）。
>
> 对人和 AI 助手同时生效：规定能改哪些文件、不能碰哪些、改动怎样算做完。
> 核心流程：**计划 → 执行 → 核对**，失败则回退修正。

---

## 总则与索引

- **总则**：见 [`PRINCIPLES.md`](./PRINCIPLES.md)（目的、原则、适用范围、工作流一句话）。
- **文件索引**：见 [`INDEX.md`](./INDEX.md)（逐文件作用与何时使用）。

---

## 目录结构

```
harness/
├── README.md              # 本说明文件
├── plan/                  # 计划：改哪些文件、完成哪条验收、如何自测（运行态记录）
├── execute/               # 执行：按计划在给定范围内修改（运行态记录）
├── verify/                # 核对：运行自测、对照预期、失败回退（运行态记录）
├── scripts/
│   └── harness.py         # 主 CLI：session-start / plan / execute / verify / lint / check-env / validate-state
├── schemas/               # JSON Schema（计划/执行/核对三段校验）
│   ├── plan.schema.json
│   ├── execute.schema.json
│   └── verify.schema.json
├── rules/
│   └── scope.json         # 允许改动的文件/目录范围（机器可读，执行越界检测）
├── templates/             # 可直接复制填写的 JSON 模板
│   ├── plan.json
│   ├── execute.json
│   └── verify.json
├── tests/
│   └── test_harness.py    # harness 自身回归测试（python -m unittest）
├── output/                # 自测输出（日志/截图/报告），不入库
└── README.md              # 本说明文件
```

---

## 三步闭环

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│  计划    │───▶│  执行    │───▶│  核对    │
│ Plan     │    │ Execute │    │ Verify  │
└─────────┘    └─────────┘    └────┬────┘
                   ▲                │
                   │   失败则回退    │
                   └────────────────┘
                       (修正范围/标准)
```

### 第一步：计划

写清：**改哪些文件、完成哪条验收、如何自测**。

入口：`plan/YYYY-MM-DD-任务名.md`（或项目根目录 `当日报告-*.md` 的"今日目标"章节）。

### 第二步：执行

按计划助助手**只在给定范围内修改**。

关键控制：
- **约束**（`execute/rules.md`）：不得改无关模块；不得擅自引入未比选的新依赖。
- **需求**（来自计划）：本模块用户故事与验收标准。
- **范围**（`execute/scope.md`）：允许改动的文件或目录列表。
- **输出**（`execute/_template.md` 记录）：自测命令与通过标准。

例：只改提交相关目录；创建提交后状态为 pending；附上可复制的调用示例。

### 第三步：核对

运行自测；对照预期；**失败则带着报错与现象回到计划**，收紧范围或改写验收标准后再试。

入口：`verify/checklist.md`（逐项打勾）+ `verify/_template.md`（记录结果）。

> **harness 的边界**：`lint`/`check-env`/`check-scope` 管的是"结构/环境/改动范围"，**查不出业务逻辑正确性**（例如函数对边界输入是否漏处理）。这类问题要靠**回归测试**补位——见末尾「回归测试」一节。

---

## 快速开始（一次任务怎么走）

> 一句话：**每次任务 = `plan` 列范围 → 改代码 → `execute` 记一笔 → `lint`+`check-env`+`check-scope` 三连查 → `verify` 自测。**

```bash
# 1) 计划：复制模板，列清要改哪些文件 + 验收标准，跑校验
python harness/scripts/harness.py --root . session-start
cp harness/templates/plan.json harness/plan/20260824-任务名.json
#   编辑 plan.json：task / changes（文件清单，须在 scope.json 的 allow 内）/ acceptance
python harness/scripts/harness.py --root . plan --file harness/plan/20260824-任务名.json

# 2) 执行：先读规则与范围，再动手；改完记录实际改动
#   读 harness/execute/rules.md（R1~R6）与 harness/rules/scope.json（allow/deny）
cp harness/templates/execute.json harness/execute/20260824-任务名.json
#   填 changes（实际改了哪些文件，in_plan 标是否越界）
python harness/scripts/harness.py --root . execute --file harness/execute/20260824-任务名.json

# 3) 核对（提交前兜底三连查）
python harness/scripts/harness.py --root . lint          # harness 结构完整
python harness/scripts/harness.py --root . check-env     # 本机环境（Python/依赖/端口）
python harness/scripts/harness.py --root . check-scope   # 扫 git 改动，看是否超范围
#   check-scope 全绿=✅ 都在 allow 内；有越界=标红 ⚠️/🚫 并返回非 0，须回计划补充说明或不提交

# 4) 自测：逐项打勾后记录结果
cp harness/templates/verify.json harness/verify/20260824-任务名.json
python harness/scripts/harness.py --root . verify --file harness/verify/20260824-任务名.json
```

**双人组用法**：谁改哪块就在 `plan.json` 的 `changes` 写明；对方 review 时直接看 `harness/plan/` 与 `harness/execute/` 的 JSON 即知范围。让 AI 改代码时也应只在其列出的文件内动；跑 `check-scope` 可发现 AI 是否偷改 `deny` 里的 `.env` 或范围外文件。

---

## 使用方式

1. **开始新任务前**：复制 `templates/plan.json` 到 `plan/YYYYMMDD-任务名.json`，填写后运行校验：
   ```bash
   python harness/scripts/harness.py --root . session-start
   python harness/scripts/harness.py --root . plan --file harness/plan/YYYYMMDD-任务名.json
   ```
2. **执行时**：先读 `execute/rules.md` 与 `rules/scope.json`，确认改动边界；执行完复制 `templates/execute.json` 记录并提交校验。
3. **完成后**：按 `verify/checklist.md` 逐项自测，复制 `templates/verify.json` 记录结果：
   ```bash
   python harness/scripts/harness.py --root . verify --file harness/verify/YYYYMMDD-任务名.json
   ```
4. **提交前范围核对**：扫描 git 实际改动，确认没有超出 `rules/scope.json` 的 allow 或命中 deny：
   ```bash
   python harness/scripts/harness.py --root . check-scope
   ```
   若有越界（返回非 0），须回到计划阶段把该文件显式列入改动范围，或确认不提交。
5. **核对不通过**：回到计划阶段，调整范围或验收标准，重新走一遍。

## 结构巡检与环境检查

```bash
python harness/scripts/harness.py --root . lint          # 巡检 harness 结构完整
python harness/scripts/harness.py --root . check-env    # 检查本机环境契约
python harness/scripts/harness.py --root . check-scope  # 扫描 git 改动，核对范围
python harness/scripts/harness.py --root . validate-state
```

## 回归测试

harness 自身的结构/范围检查（lint/check-scope）无法发现**业务逻辑正确性**问题（如某函数对单行输入漏注入、对空值崩）。这类盲点由专门的回归测试覆盖。

### 1) harness 自身回归

```bash
python -m unittest discover -s harness/tests -p "test_*.py" -v
```

### 2) 业务回归（补 harness 盲点）

针对"harness 查不出、但会破坏功能"的逻辑，落在本仓库各模块的 `tests/` 目录，提交前或 CI 应一并跑：

```bash
# AI 干扰行注入：多行/单行/空文本/全链路 prompt 含干扰行（堵住 _inject_ai_hint_lines 边界 bug）
python -m unittest experiment.tests.test_ai_hint_injection -v
#   运行结果：Ran 7 tests — OK
```

> 约定：新增功能若在通检/排错中发现"harness 没拦住"的逻辑缺陷，应顺手把对应断言固化成 `*/tests/test_*.py`，让 CI 自动捕获同类回归。
