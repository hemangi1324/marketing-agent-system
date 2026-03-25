"""
tools/file_tool.py
Reads brand guidelines and saves outputs.
"""
import os
from crewai.tools import BaseTool


class BrandGuidelinesTool(BaseTool):
    name: str = "Brand Guidelines Reader"
    description: str = (
        "Read the company brand guidelines including tone of voice, "
        "target audience, key messages, and products. "
        "Always call this before writing any content."
    )

    def _run(self, query: str = "") -> str:
        path = os.path.join(os.path.dirname(__file__), "..", "config", "brand_guidelines.md")
        try:
            with open(path) as f:
                return f.read()
        except FileNotFoundError:
            return "Brand guidelines not found. Use friendly, professional tone."


class OutputSaverTool(BaseTool):
    name: str = "Output Saver"
    description: str = "Save content to the outputs folder. Input: the content text to save."

    def _run(self, content: str) -> str:
        from datetime import datetime
        out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fpath = os.path.join(out_dir, f"output_{ts}.md")
        with open(fpath, "w") as f:
            f.write(content)
        return f"Saved to outputs/output_{ts}.md"
