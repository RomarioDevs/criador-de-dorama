import ast
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

APP_FILE = Path(__file__).resolve().parents[1] / "app.py"
FUNCTIONS = {"slug", "scene_template", "make_prompt", "fallback_story", "captions_srt", "export_video"}
CONSTANTS = {"APP_NAME", "OLLAMA_URL", "COMFY_URL", "SHOTS", "BEATS"}


def load_core():
    tree = ast.parse(APP_FILE.read_text(encoding="utf-8"))
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import) and any(alias.name == "streamlit" for alias in node.names):
                continue
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in CONSTANTS for t in node.targets):
            nodes.append(node)
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(APP_FILE), "exec"), namespace)
    return namespace


CORE = load_core()


class NovelinhaCoreTests(unittest.TestCase):
    def setUp(self):
        self.project = CORE["fallback_story"]("A herdeira encontra uma carta", "Drama e suspense", "Lívia", 9)

    def test_fallback_has_distinct_scenes(self):
        scenes = self.project["scenes"]
        self.assertEqual(len(scenes), 9)
        self.assertEqual(len({scene["title"] for scene in scenes}), 9)
        self.assertEqual(scenes[-1]["title"].split("—")[-1].strip(), "Cliffhanger")

    def test_prompts_include_character_reference(self):
        prompt = self.project["scenes"][0]["image_prompt"]
        self.assertIn("Lívia", prompt)
        self.assertIn("Roupa:", prompt)
        self.assertIn("9:16", prompt)

    def test_srt_has_timing(self):
        srt = CORE["captions_srt"](self.project["scenes"])
        self.assertIn("-->", srt)
        self.assertTrue(srt.startswith("1\n"))
        self.assertIn("Lívia", srt)

    def test_slug_preserves_accents(self):
        self.assertEqual(CORE["slug"]("Ação: coração e paixão!"), "ação-coração-e-paixão")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe não instalados")
    def test_export_creates_vertical_mp4(self):
        project = CORE["fallback_story"]("Teste de exportação", "Drama", "Ana", 3)
        video = CORE["export_video"](project)
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            f.write(video)
            f.flush()
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=width,height,codec_name", "-of", "json", f.name],
                capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            stream = json.loads(result.stdout)["streams"][0]
            self.assertEqual((stream["width"], stream["height"]), (720, 1280))
            self.assertEqual(stream["codec_name"], "h264")


if __name__ == "__main__":
    unittest.main()
