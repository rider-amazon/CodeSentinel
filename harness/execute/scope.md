# 范围控制

> 每次任务的允许改动范围。执行前必须确认本任务的范围，超出范围的改动需回退到计划阶段补充。

---

## 如何使用

每次任务开始前，在计划文件中明确列出**允许改动的文件/目录**。格式如下：

### 范围声明示例

```
## 本次范围

允许改动：
- server/app.py          （新增接口）
- web/problem.html        （前端交互）

不允许改动：
- server/store.py        （数据层不变）
- server/judge/engine.py  （判题引擎不变）
- requirements.txt        （不加新依赖）
```

---

## 全局默认范围（无特殊声明时的基线）

以下目录/文件**任何时候改动都需在计划中显式列出**：

| 类别 | 路径 | 改动门槛 |
|------|------|----------|
| 后端 API | `server/app.py` | 需计划 |
| 数据层 | `server/store.py` | 需计划（影响数据库 schema） |
| 题库 | `server/problems/*.json` | 需计划（生成产物） |
| 防护机制 | `server/defense/*.py` | 需计划 |
| 判题引擎 | `server/judge/engine.py` | 需计划 |
| 前端页面 | `web/*.html` | 需计划 |
| 前端逻辑 | `web/static/common.js` | 需计划 |
| 实验脚本 | `experiment/run_experiment.py` | 需计划 |
| 分析脚本 | `experiment/analyze.py` | 需计划 |
| 入口脚本 | `start.py` | 需计划 |
| 依赖声明 | `requirements.txt` | 需计划 + 比选 |
| 文档 | `*.md` | 低门槛但仍需记录 |

以下目录/文件**通常不需要在计划中逐一列出**（但大改动仍建议记录）：

| 类别 | 路径 | 说明 |
|------|------|------|
| 配置模板 | `experiment/config.example.json` | 只改模板注释 |
| 样式 | `web/static/style.css` | 小调整（颜色/间距） |
| 忽略规则 | `.gitignore` | 加忽略条目 |

---

## 输出要求

执行完毕后，必须在执行记录中附上：
1. **实际改动的文件列表**（与计划范围对比，标注偏差）
2. **自测命令**（可直接复制运行）
3. **通过标准**（什么算通过、什么算失败）

例：
```
## 实际改动
| 文件 | 是否在计划内 | 偏离原因 |
|------|-------------|----------|
| server/app.py | ✅ 是 | — |
| web/problem.html | ✅ 是 | — |

## 自测命令
python start.py
curl http://127.0.0.1:8000/api/problem/P001

## 通过标准
- 服务启动无报错 ✅
- P001 返回含 statement_tree ✅
```
