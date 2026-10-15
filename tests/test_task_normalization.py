"""Offline checks: python -m unittest discover -s tests -p test_task_normalization.py"""
import csv
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ml.normalize_task_text_v2 import (
    cache_key, canonicalize_math, check_content, export_csvs, read_csv, write_csv,
)
from ml.finalize_task_texts import finalize, review_hash


class NormalizationTests(unittest.TestCase):
    def test_resume_invalidated_by_source_prompt_or_model(self):
        row = {"code": "t", "text": "n = 5", "answer": "10", "type": "text"}
        key = cache_key(row, "prompt", "model")
        self.assertNotEqual(key, cache_key({**row, "text": "n = 6"}, "prompt", "model"))
        self.assertNotEqual(key, cache_key(row, "new prompt", "model"))
        self.assertNotEqual(key, cache_key(row, "prompt", "other model"))
        self.assertEqual(key, cache_key({**row, "id": "database-id"}, "prompt", "model"))

    def test_changed_numbers_flagged_and_duplicate_counts_allowed(self):
        self.assertEqual(check_content("F(5) F(5) F(5)", "$F(5)$"), [])
        self.assertTrue(check_content("F(5)", "$F(6)$"))

    def test_only_math_minus_canonicalized_idempotently(self):
        original = "Автор – текст. $F(n – 2)$\n\n$$\nF(n) − 1\n$$"
        result = canonicalize_math(original)
        self.assertEqual(result, "Автор – текст. $F(n - 2)$\n\n$$\nF(n) - 1\n$$")
        self.assertEqual(result, canonicalize_math(result))

    def test_added_answer_or_changed_function_flagged(self):
        self.assertTrue(check_content("Найдите F(5)", "$F(5)$\nОтвет: число"))
        self.assertTrue(check_content("Найдите F(5)", "Найдите $G(5)$"))

    def test_export_preserves_answers_and_quarantines_review(self):
        fields = ["code", "text", "answer", "type", "extra"]
        rows = [dict(zip(fields, ["a", "old 5", "001", "text", "value"])),
                dict(zip(fields, ["b", "old 6", "6", "text", "other"]))]
        records = [dict(code="a", normalized_text="$5$", needs_review=False,
                        warnings=[], checks=[], render_errors=[]),
                   dict(code="b", normalized_text="$7$", needs_review=False,
                        warnings=[], checks=["number changed"], render_errors=[])]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            export_csvs(output, fields, rows, records)
            _, checked = read_csv(output / "checked.csv")
            self.assertEqual(checked[0], {**rows[0], "text": "$5$"})
            self.assertEqual(checked[1], rows[1])
            _, candidates = read_csv(output / "candidates.csv")
            self.assertEqual(candidates[1]["text"], "$7$")

    def test_duplicate_codes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "input.csv"
            fields = ["code", "text", "answer", "type"]
            row = dict(zip(fields, ["a", "text", "1", "text"]))
            write_csv(target, fields, [row, row])
            with self.assertRaises(ValueError):
                read_csv(target)

    def test_real_renderer_math_tables_and_broken_input(self):
        root = Path(__file__).resolve().parents[1]
        texts = ["$F(n) = n^2$\n\n| A | B |\n|---|---|\n| 1 | 2 |",
                 r"$\notARealKatexCommand{5}$", r"F(n) = n \cdot n"]
        tasks = [dict(code=f"t{i}", original_text=text, normalized_text=text,
                      warnings=[], checks=[], needs_review=False)
                 for i, text in enumerate(texts)]
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            report.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")
            subprocess.run(["node", str(root / "pwa/scripts/preview-normalized-tasks.mjs"),
                            str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text(encoding="utf-8"))["tasks"]
            self.assertEqual(result[0]["render_errors"], [])
            self.assertEqual(result[0]["formula_count"], 1)
            self.assertTrue(result[1]["render_errors"])
            self.assertTrue(result[2]["render_errors"])
            html = (Path(directory) / "preview.html").read_text(encoding="utf-8")
            self.assertIn('<table', html)
            self.assertIn('class="katex"', html)

    def test_release_requires_exact_semantic_review(self):
        task = dict(code='t', original_text='Find F(5)', normalized_text='$F(5)$',
                    needs_review=False, warnings=[], checks=[])
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            original = dict(code='t', text=task['original_text'], answer='005', type='text')
            write_csv(folder / 'original.csv', list(original), [original])
            report = folder / 'report.json'
            report.write_text(json.dumps({'tasks': [task]}), encoding='utf-8')
            reviews = folder / 'reviews.json'
            reviews.write_text(json.dumps([dict(code='t', equivalent=True, issues=[], hash='stale')]), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unresolved'):
                finalize(report, reviews, None)
            self.assertFalse((folder / 'verified.csv').exists())
            reviews.write_text(json.dumps([dict(code='t', equivalent=True, issues=[], hash=review_hash(task))]), encoding='utf-8')
            finalize(report, reviews, None)
            _, output = read_csv(folder / 'verified.csv')
            self.assertEqual(output, [{**original, 'text': '$F(5)$'}])

    def test_manual_approval_bound_to_original(self):
        task = dict(code='t', original_text='Find F(5)', normalized_text='$F(5)$',
                    needs_review=False, warnings=[], checks=[])
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            row = dict(code='t', text=task['original_text'], answer='005', type='text')
            write_csv(folder / 'original.csv', list(row), [row])
            report, reviews, approvals = [folder / name for name in ('report.json','reviews.json','approvals.json')]
            report.write_text(json.dumps({'tasks': [task]}), encoding='utf-8')
            reviews.write_text('[]', encoding='utf-8')
            approvals.write_text(json.dumps({'t': {'original_sha256': 'wrong', 'note': 'reviewed'}}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Invalid manual approval'):
                finalize(report, reviews, approvals)


if __name__ == "__main__":
    unittest.main()
