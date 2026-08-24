# -*- coding: utf-8 -*-
"""OJ-Anti-AI 一键启动脚本。

用法:
  python start.py                     启动 Web 服务并打开浏览器
  python start.py --port 9000         指定端口
  python start.py --rebuild-problems  重新生成题库
  python start.py --mock-experiment   运行一次 mock 对照实验（演示管线）
  python start.py --analyze           对已有实验数据生成统计与图表
"""
import argparse
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / (
    "python.exe" if sys.platform == "win32" else "python")


def ensure_env():
    """确保虚拟环境与依赖就绪，返回待使用的 python 可执行文件路径。"""
    if VENV_PY.exists():
        return str(VENV_PY)
    print("[setup] 未找到虚拟环境，创建中…")
    subprocess.check_call(
        [sys.executable, "-m", "venv", str(ROOT / ".venv")],
        cwd=ROOT,
    )
    print("[setup] 安装依赖…")
    # Windows 下 pip 默认用系统代码页(GBK)解码 requirements.txt，
    # 若文件含非 ASCII 字符会报 UnicodeDecodeError；强制 UTF-8 读取。
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    subprocess.check_call([str(VENV_PY), "-m", "pip", "install", "-r",
                           str(ROOT / "requirements.txt"),
                           "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
                          env=env, cwd=ROOT)
    return str(VENV_PY)


def ensure_problems(py):
    out = ROOT / "server" / "problems"
    if not out.exists() or not list(out.glob("P*.json")):
        print("[setup] 生成题库…")
        subprocess.check_call(
            [py, "-X", "utf8", str(ROOT / "tools" / "build_problems.py")],
            cwd=ROOT,
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--rebuild-problems", action="store_true")
    ap.add_argument("--mock-experiment", action="store_true",
                    help="不启动服务，运行一次 mock 对照实验")
    ap.add_argument("--analyze", action="store_true",
                    help="不启动服务，对已有实验数据生成统计图表")
    args = ap.parse_args()

    py = ensure_env()
    if args.rebuild_problems:
        subprocess.check_call(
            [py, "-X", "utf8", str(ROOT / "tools" / "build_problems.py")],
            cwd=ROOT,
        )
        return
    ensure_problems(py)

    if args.mock_experiment:
        subprocess.check_call([py, "-X", "utf8", str(ROOT / "experiment" / "run_experiment.py"),
                               "--mock"], cwd=ROOT)
        return
    if args.analyze:
        subprocess.check_call(
            [py, "-X", "utf8", str(ROOT / "experiment" / "analyze.py")],
            cwd=ROOT,
        )
        return

    url = "http://127.0.0.1:%d" % args.port
    print("[start] 服务地址: %s （Ctrl+C 停止）" % url)
    if not args.no_browser:
        webbrowser.open(url)
    subprocess.check_call([
        py, "-X", "utf8", "-m", "uvicorn", "server.app:app",
        "--host", "127.0.0.1", "--port", str(args.port),
    ], cwd=ROOT)


if __name__ == "__main__":
    main()
