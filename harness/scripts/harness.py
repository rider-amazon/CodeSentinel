#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness —— 工作流约束 CLI（本项目自研，适配 Python 3.8+）

设计理念参考开源 harness-engineering（MIT）的「契约/模板/规则 + 运行态数据」结构，
但去除对 Python 3.11 / jsonschema 的硬依赖，改为纯标准库实现，便于在本项目（Python 3.8）
环境中直接运行。

核心命令：
  python harness/scripts/harness.py --root . session-start
  python harness/scripts/harness.py --root . plan --file harness/plan/xxx.yaml
  python harness/scripts/harness.py --root . execute --file harness/execute/xxx.yaml
  python harness/scripts/harness.py --root . verify --file harness/verify/xxx.yaml
  python harness/scripts/harness.py --root . lint
  python harness/scripts/harness.py --root . check-env
  python harness/scripts/harness.py --root . validate-state

运行态数据落在 harness/work/ 与 harness/{plan,execute,verify}/，
harness/ 已在 .gitignore 忽略，不入库。
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

# 强制 stdout/stderr 使用 UTF-8，避免 Windows GBK 控制台打印 emoji/中文报错
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --------------------------------------------------------------------------
# 兼容性：延迟导入 PyYAML（缺失时仍可解析 .json 模板，避免硬依赖）
# --------------------------------------------------------------------------
_HAS_YAML = False
try:
    import yaml  # type: ignore
    _HAS_YAML = True
except Exception:
    pass


def _load_doc(path):
    """加载 yaml / json 文档，缺失 PyYAML 时回退到 json。"""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    if _HAS_YAML:
        return yaml.safe_load(text)
    raise RuntimeError(
        "未安装 PyYAML，无法解析 %s。请 `pip install pyyaml` 或改用 .json 模板。" % path
    )


# --------------------------------------------------------------------------
# 轻量 schema 校验（不依赖 jsonschema，纯标准库实现）
# --------------------------------------------------------------------------
def _validate(instance, schema, path="$"):
    """基于简化 JSON-Schema 子集做校验：required / type / enum / properties。"""
    errors = []

    if "type" in schema:
        t = schema["type"]
        if t == "object" and not isinstance(instance, dict):
            errors.append("%s: 期望 object，实际 %s" % (path, type(instance).__name__))
        elif t == "array" and not isinstance(instance, list):
            errors.append("%s: 期望 array，实际 %s" % (path, type(instance).__name__))
        elif t == "string" and not isinstance(instance, str):
            errors.append("%s: 期望 string，实际 %s" % (path, type(instance).__name__))

    if "required" in schema and isinstance(instance, dict):
        for field in schema["required"]:
            if field not in instance:
                errors.append("%s: 缺少必填字段 '%s'" % (path, field))

    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: 值 %r 不在可选范围 %s" % (path, instance, schema["enum"]))

    if "properties" in schema and isinstance(instance, dict):
        for key, subschema in schema["properties"].items():
            if key in instance:
                errors.extend(_validate(instance[key], subschema, "%s.%s" % (path, key)))

    return errors


def validate_against_schema(instance, schema_path):
    schema = _load_doc(schema_path)
    return _validate(instance, schema)


# --------------------------------------------------------------------------
# 命令实现
# --------------------------------------------------------------------------
def cmd_session_start(args):
    """初始化运行态目录（work/ 与三个阶段目录）。"""
    root = args.root
    dirs = [
        os.path.join(root, "harness", "work"),
        os.path.join(root, "harness", "plan"),
        os.path.join(root, "harness", "execute"),
        os.path.join(root, "harness", "verify"),
        os.path.join(root, "harness", "output"),
    ]
    created = []
    for d in dirs:
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
            created.append(d)
    stamp = os.path.join(root, "harness", "work", "session.json")
    with open(stamp, "w", encoding="utf-8") as f:
        json.dump(
            {
                "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "root": os.path.abspath(root),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print("[session-start] 已初始化运行态目录")
    for d in created:
        print("  创建: %s" % d)
    print("[session-start] session.json 已写入 harness/work/")
    return 0


def _run_stage(stage, args):
    """plan / execute / verify 三阶段的通用处理：加载 -> 校验 -> 落盘 -> 输出。"""
    doc = _load_doc(args.file)
    schema_path = os.path.join(args.root, "harness", "schemas", "%s.schema.json" % stage)
    errors = validate_against_schema(doc, schema_path)
    if errors:
        print("[%s] ❌ 校验失败：" % stage)
        for e in errors:
            print("  - %s" % e)
        return 2

    # 落盘到对应阶段目录（带时间戳副本，便于追溯）
    stage_dir = os.path.join(args.root, "harness", stage)
    os.makedirs(stage_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.splitext(os.path.basename(args.file))[0]
    out_path = os.path.join(stage_dir, "%s-%s.json" % (base, ts))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print("[%s] ✅ 校验通过，已记录到 %s" % (stage, out_path))

    # 阶段特定反馈
    if stage == "plan":
        files = doc.get("changes", [])
        print("  改动范围: %d 个文件" % len(files))
        print("  验收标准: %d 条" % len(doc.get("acceptance", [])))
    elif stage == "execute":
        changes = doc.get("changes", [])
        oob = [c for c in changes if not c.get("in_plan", True)]
        print("  实际改动: %d 个文件" % len(changes))
        if oob:
            print("  ⚠️ 越界改动: %s" % ", ".join(c.get("path") for c in oob))
        else:
            print("  ✅ 未超出计划范围")
    elif stage == "verify":
        checks = doc.get("checks", [])
        passed = sum(1 for c in checks if c.get("result") == "pass")
        print("  检查项: %d，通过 %d" % (len(checks), passed))
        fails = [c for c in checks if c.get("result") == "fail"]
        if fails:
            print("  ❌ 失败项: %s" % ", ".join(c.get("id") for c in fails))
            print("  → 建议回到计划阶段修正范围或验收标准")
    return 0


def cmd_lint(args):
    """结构巡检：确认 harness 目录契约/模板/规则齐全。"""
    root = args.root
    required = [
        "harness/scripts/harness.py",
        "harness/schemas/plan.schema.json",
        "harness/schemas/execute.schema.json",
        "harness/schemas/verify.schema.json",
        "harness/rules/scope.json",
        "harness/templates/plan.json",
        "harness/templates/execute.json",
        "harness/templates/verify.json",
        "harness/tests/test_harness.py",
    ]
    missing = [p for p in required if not os.path.isfile(os.path.join(root, p))]
    if missing:
        print("[lint] ❌ 缺失必要文件：")
        for m in missing:
            print("  - %s" % m)
        return 2
    print("[lint] ✅ harness 结构完整")
    return 0


def cmd_check_env(args):
    """环境契约检查：本机能否运行主路径（python / 端口 / 依赖）。"""
    print("[check-env] 开始检查项目环境契约 ...")
    problems = []

    # 1. Python 版本
    if sys.version_info < (3, 8):
        problems.append("Python 版本过低 (<3.8)")
    else:
        print("  ✅ Python %d.%d.%d" % sys.version_info[:3])

    # 2. requirements.txt 中的依赖是否可 import（仅做存在性探测，加超时保护）
    req_path = os.path.join(args.root, "requirements.txt")
    if os.path.isfile(req_path):
        with open(req_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r"^([A-Za-z0-9_\-]+)==", line)
                if m:
                    pkg = m.group(1)
                    try:
                        __import__(pkg.replace("-", "_"))
                        print("  ✅ 依赖可导入: %s" % pkg)
                    except Exception:
                        problems.append("依赖未安装: %s" % pkg)
                        print("  ❌ 依赖未安装: %s" % pkg)

    # 3. 端口 8000 是否被占用（Windows / Linux 通用尝试）
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        if s.connect_ex(("127.0.0.1", 8000)) == 0:
            problems.append("端口 8000 已被占用")
            print("  ❌ 端口 8000 已被占用")
        else:
            print("  ✅ 端口 8000 空闲")
        s.close()
    except Exception:
        pass

    if problems:
        print("[check-env] ⚠️ 发现问题：")
        for p in problems:
            print("  - %s" % p)
        return 1
    print("[check-env] ✅ 环境契约通过")
    return 0


def cmd_validate_state(args):
    """状态校验：运行态目录是否就绪、最近一次各阶段记录是否存在。"""
    root = args.root
    work = os.path.join(root, "harness", "work")
    session = os.path.join(work, "session.json")
    if not (os.path.isdir(work) and os.path.isfile(session)):
        print("[validate-state] ❌ 运行态未初始化，请先运行 session-start")
        return 2
    print("[validate-state] ✅ 运行态已初始化: %s" % work)
    for stage in ("plan", "execute", "verify"):
        d = os.path.join(root, "harness", stage)
        files = [f for f in os.listdir(d) if f.endswith(".json")] if os.path.isdir(d) else []
        if files:
            print("  %s: 最近记录 %s" % (stage, sorted(files)[-1]))
        else:
            print("  %s: 暂无记录" % stage)
    return 0


def _fnmatch_any(path, patterns):
    """判断 path 是否匹配 patterns 中的任一模式（支持 * 通配与目录前缀匹配）。"""
    import fnmatch
    path = path.replace("\\", "/")
    for pat in patterns:
        pat = pat.replace("\\", "/").rstrip("/")
        if fnmatch.fnmatch(path, pat):
            return True
        # 目录型模式：path 落在某目录下也算匹配（如 "data/" 匹配 "data/x.json"）
        if pat.endswith("/") and path.startswith(pat):
            return True
        if ("/" not in pat) and fnmatch.fnmatch(os.path.basename(path), pat):
            return True
    return False


def _decode_git_path(s):
    """解码 git quotepath 输出的八进制转义路径（如 /345/256/241... 或 \\345\\256\\241...）。

    git 在 core.quotepath=true（默认）时会把非 ASCII 字符用八进制转义，
    且可能用 '/' 或 '\\' 作为三字节一组的分隔符，整体出现在单引号内或不带引号。
    """
    # 若不含八进制序列（/或\ 后跟三位 0-7 数字），直接返回
    if not re.search(r"[\\/][0-7]{3}", s):
        return s
    try:
        # 收集所有连续的三字节八进制段，反推原字节序列
        octets = re.findall(r"[\\/]([0-7]{3})", s)
        raw = bytes(int(o, 8) for o in octets)
        decoded = raw.decode("utf-8", errors="replace")
        # 仅当确实解出非空才采用，否则退回原串
        if decoded.strip():
            return decoded
    except Exception:
        pass
    return s


def cmd_check_scope(args):
    """范围核对：扫描 git 实际改动文件，与 rules/scope.json 的 allow/deny 比对。

    作用：自动发现「未在执行记录里声明、却实际改动了」的越界文件，
    弥补 execute 阶段仅校验人填 JSON 的盲区，对人和 AI 同时生效。
    """
    root = args.root
    scope_path = os.path.join(root, "harness", "rules", "scope.json")
    if not os.path.isfile(scope_path):
        print("[check-scope] ❌ 找不到范围声明: %s" % scope_path)
        return 2
    scope = json.load(open(scope_path, "r", encoding="utf-8"))
    allow = scope.get("allow", [])
    deny = scope.get("deny", [])

    # 取 git 实际改动（含未暂存/已暂存/未跟踪；排除 harness 运行态本身）
    try:
        out = subprocess.run(
            ["git", "-C", root, "status", "--porcelain", "-uall"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except Exception as e:
        print("[check-scope] ❌ 无法执行 git status: %s" % e)
        return 2

    changed = []
    for line in out.splitlines():
        if not line.strip():
            continue
        # 忽略 harness 的运行态产物（plan/execute/verify 的 json、work/、output/）
        rel_raw = line[3:].strip()
        # git 在 GBK 控制台下可能返回八进制转义（如 \345\256\241），解码为 UTF-8
        rel = _decode_git_path(rel_raw).replace("\\", "/")
        if rel.startswith("harness/plan/") or rel.startswith("harness/execute/") \
           or rel.startswith("harness/verify/") or rel.startswith("harness/work/") \
           or rel.startswith("harness/output/"):
            continue
        if rel:
            changed.append(rel)

    print("[check-scope] 实际改动文件（%d 个，已排除 harness 运行态）：" % len(changed))
    for c in changed:
        print("  - %s" % c)

    violations = []
    for c in changed:
        if _fnmatch_any(c, deny):
            violations.append(("DENY", c))
        elif not _fnmatch_any(c, allow):
            violations.append(("OUT-OF-ALLOW", c))

    if violations:
        print("[check-scope] ❌ 发现越界改动：")
        for kind, c in violations:
            if kind == "DENY":
                print("  🚫 禁止改动: %s（命中 deny 列表）" % c)
            else:
                print("  ⚠️ 超出 allow 范围: %s（须在计划阶段显式说明）" % c)
        return 1
    print("[check-scope] ✅ 全部改动均在 allow 范围内，无越界")
    return 0


# --------------------------------------------------------------------------
# CLI 入口
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(prog="harness", description="工作流约束 CLI")
    p.add_argument("--root", default=".", help="项目根目录（默认当前目录）")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("session-start", help="初始化运行态目录")

    sp = sub.add_parser("plan", help="提交计划并校验")
    sp.add_argument("--file", required=True, help="计划文档路径 (yaml/json)")

    se = sub.add_parser("execute", help="提交执行记录并校验")
    se.add_argument("--file", required=True, help="执行记录路径 (yaml/json)")

    sv = sub.add_parser("verify", help="提交核对记录并校验")
    sv.add_argument("--file", required=True, help="核对记录路径 (yaml/json)")

    sub.add_parser("lint", help="harness 结构巡检")
    sub.add_parser("check-env", help="项目环境契约检查")
    sub.add_parser("validate-state", help="运行态状态校验")
    sub.add_parser("check-scope", help="扫描 git 改动，核对是否在 allow/deny 范围内")
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    handlers = {
        "session-start": cmd_session_start,
        "plan": lambda a: _run_stage("plan", a),
        "execute": lambda a: _run_stage("execute", a),
        "verify": lambda a: _run_stage("verify", a),
        "lint": cmd_lint,
        "check-env": cmd_check_env,
        "validate-state": cmd_validate_state,
        "check-scope": cmd_check_scope,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
