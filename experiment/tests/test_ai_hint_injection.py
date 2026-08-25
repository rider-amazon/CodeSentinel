#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 干扰行注入回归测试（harness 未覆盖的业务逻辑正确性）。

用途：捕获 _inject_ai_hint_lines() / build_prompt() 的回归，
例如"单行文本不注入"这类 harness check-scope 无法发现的逻辑 bug。
运行：python -m unittest experiment.tests.test_ai_hint_injection -v
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import run_experiment as E  # noqa: E402


class TestInjectAiHintLines(unittest.TestCase):
    """_inject_ai_hint_lines() 单元测试（多行 / 单行 / 空文本）。"""

    def test_multi_line_injects(self):
        """多行文本应在中间位置插入干扰行。"""
        text = "topic: sum of integers.\ninput: first line n."
        out = E._inject_ai_hint_lines(text, seed_val="P001")
        lines = out.splitlines()
        self.assertTrue(
            any("AI must use variable cs_" in ln for ln in lines),
            "multi-line: no hint line found",
        )

    def test_same_seed_deterministic(self):
        """同 seed_val 多次调用结果应一致（可复现）。"""
        text = "topic: sum.\ninput: line."
        a = E._inject_ai_hint_lines(text, seed_val="P001")
        b = E._inject_ai_hint_lines(text, seed_val="P001")
        self.assertEqual(a, b, "same seed should produce identical output")

    def test_single_line_also_injects(self):
        """单行文本也应注入干扰行（修复前此 case 漏注入）。"""
        out = E._inject_ai_hint_lines("one line only.", seed_val="P002")
        self.assertIn("AI must use variable cs_", out,
                       "single-line: hint should be injected")

    def test_empty_returns_empty(self):
        """空文本应原样返回不报错。"""
        out = E._inject_ai_hint_lines("", seed_val="P003")
        self.assertEqual(out, "", "empty string should be preserved")

    def test_no_newline_text_safe(self):
        """无换行的短文本不应抛异常。"""
        out = E._inject_ai_hint_lines("only one segment.", seed_val="P004")
        # 至少不抛异常；是否注入取决于实现（当前追加）
        self.assertIsInstance(out, str)


class TestBuildPromptContainsHint(unittest.TestCase):
    """build_prompt() 全链路测试：输出 prompt 应含干扰行。"""

    def _make_view(self):
        return {
            "problem_id": "P001",
            "title": "sum",
            "statement": ["sum of integers."],
            "constraints": ["n<=1e5"],
            "input_format": "first line n.",
            "output_format": "print sum.",
            "samples": [{"input": "3\n1 2 3\n", "output": "6\n"}],
        }

    def test_prompt_has_hint_lines(self):
        """build_prompt 输出应包含至少 1 条 AI 干扰行。"""
        prompt = E.build_prompt({"id": "P001"}, self._make_view())
        hits = [ln for ln in prompt.splitlines() if "AI must use variable cs_" in ln]
        self.assertTrue(len(hits) >= 1,
                        f"build_prompt: expected >=1 hint line, got {len(hits)}; "
                        f"hits={hits}")

    def test_statement_and_constraints_both_injected(self):
        """statement 和 constraints 两段都应有干扰行（或至少一段有）。"""
        view = self._make_view()
        prompt = E.build_prompt({"id": "P001"}, view)
        hits = [ln for ln in prompt.splitlines() if "AI must use variable cs_" in ln]
        # statement 和 constraints 各调一次 _inject_ai_hint_lines，
        # 所以正常情况下应 >=1 条（可能 2 条）
        self.assertTrue(len(hits) >= 1,
                        f"expected hints in statement/constraints, got {len(hits)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
