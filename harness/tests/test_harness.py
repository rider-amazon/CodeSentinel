#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness CLI 回归测试（纯标准库，直接调用模块函数，避开 subprocess 的 3.8 兼容问题）。"""

import argparse
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "harness", "scripts"))
import harness as H  # noqa: E402


def _args(command, root, **kw):
    a = argparse.Namespace(root=root, command=command, **kw)
    return a


class TestHarnessCLI(unittest.TestCase):
    def test_lint_pass(self):
        rc = H.cmd_lint(_args("lint", ROOT))
        self.assertEqual(rc, 0)

    def test_session_start(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(ROOT, "harness"), os.path.join(tmp, "harness"))
            rc = H.cmd_session_start(_args("session-start", tmp))
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "harness", "work", "session.json")))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_plan_validate(self):
        plan = os.path.join(ROOT, "harness", "templates", "plan.json")
        rc = H._run_stage("plan", _args("plan", ROOT, file=plan))
        self.assertEqual(rc, 0)

    def test_execute_validate(self):
        ex = os.path.join(ROOT, "harness", "templates", "execute.json")
        rc = H._run_stage("execute", _args("execute", ROOT, file=ex))
        self.assertEqual(rc, 0)

    def test_verify_validate(self):
        vf = os.path.join(ROOT, "harness", "templates", "verify.json")
        rc = H._run_stage("verify", _args("verify", ROOT, file=vf))
        self.assertEqual(rc, 0)

    def test_schema_rejects_missing(self):
        # 空对象应被 required 校验拒绝
        import json as _json
        tmp = tempfile.mktemp(suffix=".json")
        with open(tmp, "w", encoding="utf-8") as f:
            _json.dump({}, f)
        try:
            rc = H._run_stage("plan", _args("plan", ROOT, file=tmp))
            self.assertEqual(rc, 2)  # 校验失败返回 2
        finally:
            os.remove(tmp)

    def test_check_env_runs(self):
        # check-env 不强制 returncode，只要能运行不抛异常
        rc = H.cmd_check_env(_args("check-env", ROOT))
        self.assertIn(rc, (0, 1))

    def test_validate_state_needs_session(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(ROOT, "harness"), os.path.join(tmp, "harness"))
            # 移除 session.json 以模拟「未初始化」状态（copytree 会带上真实的运行态副本）
            s = os.path.join(tmp, "harness", "work", "session.json")
            if os.path.isfile(s):
                os.remove(s)
            rc = H.cmd_validate_state(_args("validate-state", tmp))
            self.assertEqual(rc, 2)  # 未初始化
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
