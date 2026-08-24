# Harness 索引（文件速查）

> 本文件是 Harness 的"索引"，逐文件说明作用与何时使用。
> 配套总则见 `PRINCIPLES.md`；整体说明见 `README.md`。

| 文件 / 目录 | 类型 | 作用 | 何时看 / 用 |
|------------|------|------|------------|
| `README.md` | 文档 | 总则、索引、三步流程、使用方式的总入口 | 第一次接触 harness 时通读 |
| `PRINCIPLES.md` | 文档 | 总则：目的、原则、适用范围、工作流 | 想了解为什么这么约束时 |
| `INDEX.md` | 文档 | 本文件：文件速查表 | 找某个文件做什么时 |
| `scripts/harness.py` | 脚本 | 主 CLI：`session-start` / `plan` / `execute` / `verify` / `lint` / `check-env` / `validate-state` | 每个阶段都要运行它做校验 |
| `schemas/plan.schema.json` | 约束 | 计划文档的字段校验（必填 task/changes/acceptance） | `harness plan` 自动调用 |
| `schemas/execute.schema.json` | 约束 | 执行记录的字段校验（含 `in_plan` 越界标记） | `harness execute` 自动调用 |
| `schemas/verify.schema.json` | 约束 | 核对记录的字段校验（checks 结果枚举） | `harness verify` 自动调用 |
| `rules/scope.json` | 规则 | 允许/禁止改动的文件或目录范围（机器可读） | 执行前确认边界；越界检测依据 |
| `templates/plan.json` | 模板 | 计划 JSON 模板，复制填写 | 新任务开始前复制 |
| `templates/execute.json` | 模板 | 执行记录 JSON 模板 | 执行完成后复制填写 |
| `templates/verify.json` | 模板 | 核对记录 JSON 模板 | 自测完成后复制填写 |
| `execute/rules.md` | 文档 | 执行阶段 6 条硬约束（不改无关模块/不引新依赖/先读后改/密钥不入库/假实现标注/编码规范） | 执行前必读 |
| `execute/scope.md` | 文档 | 范围控制说明 + 全局默认范围表 + 输出要求 | 执行前必读，配合 `rules/scope.json` |
| `execute/_template.md` | 模板 | 执行记录 Markdown 模板 | 需要人读版执行记录时 |
| `verify/checklist.md` | 文档 | 23 项自测检查清单（启动/判题/防护/实验/文档/编码）+ 日常最小集 4 项 | 核对阶段逐项打勾 |
| `verify/_template.md` | 模板 | 核对记录 Markdown 模板 | 核对结果人读版 |
| `tests/test_harness.py` | 脚本 | 回归测试（8 项，直接 import 模块验证） | 改完 harness 自身后运行 |
| `plan/` `execute/` `verify/` | 目录 | 各阶段运行态记录（带时间戳 JSON 副本） | 查看历史改动追溯 |
| `work/` | 目录 | 会话状态（`session.json`） | `validate-state` 读取 |
| `output/` | 目录 | 自测输出（日志/截图/报告） | 排查问题时翻看 |
