"""Embed docs/data.json into pipeline/template.html and write docs/index.html."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
template = (root / "pipeline" / "template.html").read_text()
data = (root / "docs" / "data.json").read_text()
(root / "docs" / "index.html").write_text(template.replace("/*DATA*/", data))
print("wrote docs/index.html")
