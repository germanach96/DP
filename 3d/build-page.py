"""Assemble the single-file ../index.html from page.template.html, the generated
factory (dist/createObjectModel.js, transpiled from src/createObjectModel.ts) and decals.js."""
import re
from pathlib import Path

here = Path(__file__).parent

def strip(js: str) -> str:
    js = js.replace("import * as THREE from 'three';\n", "")
    return re.sub(r"^export (?=(function|const|class|type|let)\b)", "", js, flags=re.M)

page = (here / "page.template.html").read_text()
# The print material's photo maps are replaced at runtime by the canvas decals (decals.js),
# so the page drops their file references and stays a self-contained single file.
factory = strip((here / "dist/createObjectModel.js").read_text())
factory = re.sub(r'"(url|path)": "[^"]*material-evidence/[^"]*\.png"', r'"\1": null', factory)
page = page.replace("/*__FACTORY__*/", factory)
page = page.replace("/*__DECALS__*/", strip((here / "decals.js").read_text()))
(here.parent / "index.html").write_text(page)
print("index.html", len(page), "bytes")
