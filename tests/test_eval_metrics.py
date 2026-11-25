"""Local checks for scripts/05_eval.py. No GPU and no model.

Compile and raster checks that need a TeX install are skipped when the
programs are absent. Those skips are the result on a machine without them,
not a measured model score.
"""
import difflib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
EVAL_PATH = os.path.join(SCRIPTS, "05_eval.py")
sys.path.insert(0, SCRIPTS)

_spec = importlib.util.spec_from_file_location("eval_metrics", EVAL_PATH)
mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = mod
_spec.loader.exec_module(mod)

import common


def _chunk(tag, data):
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _png(width, height, bit_depth, color_type, raw, plte=None, trns=None, interlace=0):
    ihdr = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, interlace)
    parts = [b"\x89PNG\r\n\x1a\n", _chunk(b"IHDR", ihdr)]
    if plte is not None:
        parts.append(_chunk(b"PLTE", plte))
    if trns is not None:
        parts.append(_chunk(b"tRNS", trns))
    parts.append(_chunk(b"IDAT", zlib.compress(raw)))
    parts.append(_chunk(b"IEND", b""))
    return b"".join(parts)


class _Proc(object):
    def __init__(self, code):
        self.returncode = code


class MetricTests(unittest.TestCase):
    def test_import_does_not_bind_torch(self):
        self.assertNotIn("torch", mod.__dict__)
        self.assertNotIn("AutoTokenizer", mod.__dict__)

    def test_source_does_not_invoke_tex(self):
        with open(EVAL_PATH, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("pdflatex", src)
        self.assertIsNone(re.search(r"""["']latex["']""", src))
        self.assertNotIn("halt=False", src)
        self.assertIn("compile_one", src)
        self.assertIn('"dvipng"', src)
        self.assertIn('"-D", "100"', src)
        self.assertIn('"-T", "tight"', src)
        self.assertEqual(src.count("subprocess.run"), 1)

    def test_task_sets(self):
        self.assertEqual(mod.COMPILE_TASKS, ("fix", "gen", "conv"))
        self.assertEqual(mod.EDIT_TASKS, ("fix", "edit"))
        self.assertNotIn("fim", mod.COMPILE_TASKS)
        self.assertNotIn("edit", mod.COMPILE_TASKS)
        self.assertNotIn("gen", mod.EDIT_TASKS)

    def test_clean_and_exact_norm(self):
        self.assertEqual(mod.clean("```latex\n$x$\n```"), "$x$")
        self.assertEqual(mod.clean("```tex\n$x$\n```"), "$x$")
        self.assertEqual(mod.clean("```\n$x$\n```"), "$x$")
        self.assertEqual(mod.clean("  $x$  "), "$x$")
        self.assertEqual(mod.norm("a b\nc"), "abc")

    def test_levenshtein_and_minimal_edit(self):
        self.assertEqual(mod.levenshtein("abc", "abc"), 0)
        self.assertEqual(mod.levenshtein("", "abc"), 3)
        self.assertEqual(mod.levenshtein("abc", "ab"), 1)
        self.assertEqual(mod.levenshtein("abc", "adc"), 1)
        self.assertEqual(mod.levenshtein("kitten", "sitting"), 3)
        self.assertEqual(mod.levenshtein("sitting", "kitten"), 3)
        self.assertEqual(mod.minimal_edit_score("abc", "abc"), 1.0)
        self.assertEqual(mod.minimal_edit_score("", "abc"), 0.0)
        self.assertAlmostEqual(mod.minimal_edit_score("abc", "ab"), 1.0 - 1.0 / 3.0)
        self.assertAlmostEqual(mod.minimal_edit_score("kitten", "sitting"), 1.0 - 3.0 / 7.0)

    def test_exact_match_keeps_whitespace_and_edit_distance_does_not(self):
        # Patched so a future compile on these tasks fails here instead of
        # launching a missing TeX engine.
        orig = common.subprocess.run

        def boom(*_a, **_k):
            raise AssertionError("compile_one was called")

        common.subprocess.run = boom
        try:
            edit = mod.score_task("edit", ["a b", "ab"], ["ab", "abc"])
            fim = mod.score_task("fim", ["ab"], ["ab"])
            empty = mod.score_task("fim", [], [])
        finally:
            common.subprocess.run = orig
        self.assertEqual(edit["exact_norm"], 0.5)
        self.assertAlmostEqual(edit["minimal_edit"], (
            mod.minimal_edit_score("a b", "ab") + mod.minimal_edit_score("ab", "abc")
        ) / 2.0)
        self.assertAlmostEqual(edit["similarity"], (
            difflib.SequenceMatcher(None, "a b", "ab").ratio()
            + difflib.SequenceMatcher(None, "ab", "abc").ratio()
        ) / 2.0)
        self.assertLess(edit["similarity"], 1.0)
        self.assertNotIn("compile@1", edit)
        self.assertNotIn("render_match", edit)
        self.assertEqual(fim["exact_norm"], 1.0)
        self.assertEqual(fim["similarity"], 1.0)
        self.assertEqual(set(fim), {"n", "exact_norm", "similarity"})
        self.assertEqual(empty, {"n": 0})

    def test_whitespace_pair_differs_on_minimal_edit(self):
        res = mod.score_task("edit", ["a b"], ["ab"])
        self.assertEqual(res["exact_norm"], 1.0)
        self.assertAlmostEqual(res["minimal_edit"], 2.0 / 3.0)
        self.assertAlmostEqual(res["similarity"], difflib.SequenceMatcher(None, "a b", "ab").ratio())
        self.assertAlmostEqual(res["similarity"], 0.8)

    def test_compile_at_k_from_flags(self):
        both = mod.rates_from_flags([[False, False, True], [True, False, False]], 3)
        self.assertEqual(both["compile@1"], 0.5)
        self.assertEqual(both["compile@3"], 1.0)
        none = mod.rates_from_flags([[False, False], [False]], 2)
        self.assertEqual(none["compile@1"], 0.0)
        self.assertEqual(none["compile@2"], 0.0)
        mono = mod.rates_from_flags([[True, False]], 8)
        self.assertEqual(mono["compile@1"], 1.0)
        self.assertEqual(mono["compile@8"], 1.0)
        one = mod.rates_from_flags([[False], [True]], 1)
        self.assertEqual(one, {"compile@1": 0.5})
        self.assertNotIn("compile@8", one)
        with self.assertRaises(ValueError):
            mod.rates_from_flags([], 8)

    def test_score_task_rejects_bad_samples_without_compiling(self):
        orig = common.subprocess.run

        def boom(*_a, **_k):
            raise AssertionError("compile_one was called")

        common.subprocess.run = boom
        try:
            with self.assertRaises(ValueError):
                mod.score_task("fim", ["a"], ["a", "b"])
            with self.assertRaises(ValueError):
                mod.score_task("fim", ["a"], ["a"], samples=[["b"]])
            with self.assertRaises(ValueError):
                mod.score_task("fim", ["a"], ["a"], k=0)
        finally:
            common.subprocess.run = orig

    def test_png_filters_and_pixel_score(self):
        self.assertEqual(mod.decode_png_gray(_png(2, 2, 8, 0, bytes([0, 1, 2, 0, 3, 4]))),
                         [[1, 2], [3, 4]])
        self.assertEqual(mod.decode_png_gray(_png(2, 1, 8, 0, bytes([1, 10, 10]))), [[10, 20]])
        self.assertEqual(mod.decode_png_gray(_png(1, 2, 8, 0, bytes([0, 30, 2, 5]))), [[30], [35]])
        self.assertEqual(mod.decode_png_gray(_png(1, 2, 8, 0, bytes([0, 30, 3, 0]))), [[30], [15]])
        self.assertEqual(mod.decode_png_gray(_png(1, 2, 8, 0, bytes([0, 30, 4, 10]))), [[30], [40]])
        self.assertEqual(mod.decode_png_gray(_png(3, 1, 1, 0, bytes([0, 0b10100000]))),
                         [[255, 0, 255]])
        plte = bytes([0, 0, 0, 255, 255, 255])
        self.assertEqual(mod.decode_png_gray(_png(2, 1, 8, 3, bytes([0, 0, 1]), plte=plte)),
                         [[0, 255]])
        self.assertEqual(
            mod.decode_png_gray(_png(2, 1, 8, 3, bytes([0, 0, 1]), plte=plte, trns=bytes([0]))),
            [[255, 255]])
        self.assertEqual(
            mod.decode_png_gray(_png(2, 1, 8, 0, bytes([0, 10, 20]), trns=struct.pack(">H", 10))),
            [[255, 20]])
        self.assertEqual(mod.decode_png_gray(_png(1, 1, 8, 6, bytes([0, 0, 0, 0, 0]))), [[255]])
        self.assertEqual(mod.decode_png_gray(_png(1, 1, 8, 6, bytes([0, 255, 0, 0, 255]))), [[76]])
        self.assertEqual(mod.raster_similarity([[0, 0]], [[0, 255]]), 0.5)
        self.assertEqual(mod.raster_similarity([[255]], [[255]]), 1.0)
        self.assertEqual(mod.raster_similarity([[0]], [[255]]), 0.0)
        with self.assertRaises(RuntimeError):
            mod.decode_png_gray(_png(1, 1, 8, 0, bytes([0, 1]), interlace=1))
        with self.assertRaises(RuntimeError):
            mod.decode_png_gray(_png(1, 1, 16, 0, b""))
        with self.assertRaises(RuntimeError):
            mod.decode_png_gray(_png(1, 1, 8, 0, bytes([0])))

    def test_rejected_text_is_not_rasterized(self):
        calls = []
        orig = mod.rasterize_dvi

        def boom(dvi):
            calls.append(dvi)
            raise AssertionError("rasterized")

        mod.rasterize_dvi = boom
        try:
            self.assertEqual(mod.render_score(False, b"\xf7partial", True, b"\xf7gold"), 0.0)
            self.assertEqual(mod.render_score(True, b"\xf7pred", False, None), 0.0)
            self.assertEqual(calls, [])
            if shutil.which("dvipng") is None:
                self.assertIsNone(mod.render_score(True, b"\xf7a", True, b"\xf7b"))
                self.assertIsNone(mod.render_score(True, None, True, b"\xf7b"))
                self.assertEqual(calls, [])
            else:
                with self.assertRaises(RuntimeError):
                    mod.render_score(True, None, True, b"\xf7b")
        finally:
            mod.rasterize_dvi = orig

    def test_rasterize_refuses_to_run_without_dvipng(self):
        if shutil.which("dvipng") is not None:
            self.skipTest("dvipng is installed; the missing-tool path is not the one under test")
        orig = mod.subprocess.run

        def boom(*_a, **_k):
            raise AssertionError("rasterize started a process")

        mod.subprocess.run = boom
        try:
            with self.assertRaises(RuntimeError) as ctx:
                mod.rasterize_dvi(b"\xf7")
        finally:
            mod.subprocess.run = orig
        self.assertIn("dvipng", str(ctx.exception))

    def test_dvi_kept_only_when_compile_one_accepts(self):
        seen = {}

        def fake_run(cmd, cwd=None, **_kwargs):
            seen["cmd"] = cmd
            seen["cwd"] = cwd
            seen["calls"] = seen.get("calls", 0) + 1
            with open(os.path.join(cwd, "doc.dvi"), "wb") as f:
                f.write(b"\xf7DVI")
            with open(os.path.join(cwd, "doc.log"), "w", encoding="utf-8") as f:
                f.write("")
            return _Proc(0)

        orig_run = common.subprocess.run
        orig_mk = common.tempfile.mkdtemp
        orig_rm = common.shutil.rmtree
        common.subprocess.run = fake_run
        try:
            ok, dvi = mod.accepted_dvi("Hello.")
        finally:
            common.subprocess.run = orig_run
        self.assertEqual((ok, dvi), (True, b"\xf7DVI"))
        self.assertEqual(seen["calls"], 1)
        self.assertEqual(seen["cmd"][0], "latex")
        self.assertIn("-halt-on-error", seen["cmd"])
        self.assertIn("-no-shell-escape", seen["cmd"])
        self.assertEqual(seen["cmd"][-1], "doc.tex")
        self.assertFalse(os.path.exists(seen["cwd"]))
        self.assertIs(common.tempfile.mkdtemp, orig_mk)
        self.assertIs(common.shutil.rmtree, orig_rm)

        def reject_run(cmd, cwd=None, **_kwargs):
            with open(os.path.join(cwd, "doc.dvi"), "wb") as f:
                f.write(b"\xf7partial")
            with open(os.path.join(cwd, "doc.log"), "w", encoding="utf-8") as f:
                f.write("! error\n")
            return _Proc(1)

        common.subprocess.run = reject_run
        try:
            rejected = mod.accepted_dvi("{")
        finally:
            common.subprocess.run = orig_run
        self.assertEqual(rejected, (False, None))
        self.assertIs(common.tempfile.mkdtemp, orig_mk)
        self.assertIs(common.shutil.rmtree, orig_rm)

    def test_capture_patch_restored_when_engine_is_missing(self):
        seen = {}

        def fake_run(_cmd, cwd=None, **_kwargs):
            seen["cwd"] = cwd
            raise FileNotFoundError("engine binary is not installed")

        orig_run = common.subprocess.run
        orig_mk = common.tempfile.mkdtemp
        orig_rm = common.shutil.rmtree
        common.subprocess.run = fake_run
        try:
            with self.assertRaises(FileNotFoundError):
                mod.accepted_dvi("Hello.")
        finally:
            common.subprocess.run = orig_run
        self.assertFalse(os.path.exists(seen["cwd"]))
        self.assertIs(common.tempfile.mkdtemp, orig_mk)
        self.assertIs(common.shutil.rmtree, orig_rm)

    def test_missing_dvi_after_acceptance_is_an_error(self):
        def fake_run(_cmd, cwd=None, **_kwargs):
            with open(os.path.join(cwd, "doc.log"), "w", encoding="utf-8") as f:
                f.write("")
            return _Proc(0)

        orig_run = common.subprocess.run
        orig_mk = common.tempfile.mkdtemp
        orig_rm = common.shutil.rmtree
        common.subprocess.run = fake_run
        try:
            with self.assertRaises(RuntimeError) as ctx:
                mod.accepted_dvi("Hello.")
        finally:
            common.subprocess.run = orig_run
        self.assertIn("doc.dvi", str(ctx.exception))
        self.assertIs(common.tempfile.mkdtemp, orig_mk)
        self.assertIs(common.shutil.rmtree, orig_rm)

    def test_results_table(self):
        text = mod.results_markdown({
            "base": {
                "fix": {
                    "n": 2,
                    "compile@1": 0.5,
                    "compile@8": 1.0,
                    "render_match": 0.25,
                    "minimal_edit": 0.75,
                    "exact_norm": 0.0,
                    "similarity": 0.5,
                },
                "fim": {"n": 2, "exact_norm": 1.0, "similarity": 1.0},
            }
        })
        self.assertLess(text.index("compile@1"), text.index("compile@8"))
        self.assertLess(text.index("compile@8"), text.index("render_match"))
        self.assertLess(text.index("render_match"), text.index("minimal_edit"))
        self.assertLess(text.index("minimal_edit"), text.index("exact_norm"))
        self.assertLess(text.index("exact_norm"), text.index("similarity"))
        self.assertIn("| fix | compile@1 | 0.500 |", text)
        self.assertIn("| fix | compile@8 | 1.000 |", text)
        self.assertIn("| fix | render_match | 0.250 |", text)
        self.assertIn("| fix | minimal_edit | 0.750 |", text)
        self.assertIn("| fim | exact_norm | 1.000 |", text)
        self.assertNotIn("| fim | compile@1 |", text)
        self.assertNotIn("| fix | n |", text)

    def test_write_results_skips_sample_dumps(self):
        d = tempfile.mkdtemp()
        try:
            with open(os.path.join(d, "base.json"), "w", encoding="utf-8") as f:
                json.dump({"fix": {"exact_norm": 1.0}}, f)
            with open(os.path.join(d, "base_samples.json"), "w", encoding="utf-8") as f:
                json.dump([{"pred": "x"}], f)
            text = mod.write_results(d)
            self.assertIn("| fix | exact_norm | 1.000 |", text)
            self.assertNotIn("base_samples", text)
            self.assertTrue(os.path.exists(os.path.join(d, "results.md")))
        finally:
            shutil.rmtree(d)

    def test_cli_help_and_bad_k_do_not_load_a_model(self):
        help_run = subprocess.run(
            [sys.executable, EVAL_PATH, "--help"],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("--k", help_run.stdout)
        self.assertIn("--temperature", help_run.stdout)
        bad_k = subprocess.run(
            [sys.executable, EVAL_PATH, "--model", "x", "--k", "0"],
            capture_output=True, text=True, timeout=20,
        )
        self.assertNotEqual(bad_k.returncode, 0)
        self.assertIn("--k", bad_k.stderr)
        bad_temp = subprocess.run(
            [sys.executable, EVAL_PATH, "--model", "x", "--k", "8", "--temperature", "0"],
            capture_output=True, text=True, timeout=20,
        )
        self.assertNotEqual(bad_temp.returncode, 0)
        self.assertIn("temperature", bad_temp.stderr)

    @unittest.skipUnless(shutil.which("latex"), "latex not on PATH; compile tests skipped")
    def test_real_compile_one(self):
        ok, log = common.compile_one("Hello.")
        self.assertTrue(ok, log[-500:])
        bad, blog = common.compile_one("{")
        self.assertFalse(bad, "a lone brace was accepted by compile_one")
        math_ok, mlog = common.compile_one("$x$")
        self.assertTrue(math_ok, mlog[-500:])

        accepted = mod.accepted_dvi("Hello.")
        self.assertTrue(accepted[0])
        self.assertTrue(accepted[1].startswith(b"\xf7"), accepted[1][:8])
        self.assertEqual(mod.accepted_dvi("{"), (False, None))

        calls = []
        orig = mod.rasterize_dvi

        def wrap(dvi):
            calls.append(True)
            if shutil.which("dvipng") is None:
                raise AssertionError("rasterize called without dvipng")
            return orig(dvi)

        mod.rasterize_dvi = wrap
        try:
            res = mod.score_task(
                "fix",
                ["Hello.", "{"],
                ["Hello.", "Hello."],
                samples=[["Hello.", "$x$"], ["{", "Hello."]],
                k=2,
            )
            one = mod.score_task("gen", ["Hello."], ["Hello."], k=1)
        finally:
            mod.rasterize_dvi = orig

        self.assertAlmostEqual(res["compile@1"], 0.5)
        self.assertAlmostEqual(res["compile@2"], 1.0)
        self.assertAlmostEqual(res["exact_norm"], 0.5)
        self.assertIn("minimal_edit", res)
        self.assertAlmostEqual(one["compile@1"], 1.0)
        self.assertNotIn("compile@8", one)
        self.assertNotIn("minimal_edit", one)
        if shutil.which("dvipng") is None:
            self.assertNotIn("render_match", res)
            self.assertEqual(calls, [])
        else:
            self.assertAlmostEqual(res["render_match"], 0.5)
            self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
