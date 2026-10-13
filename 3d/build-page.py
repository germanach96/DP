"""Assemble the single-file ../index.html from page.template.html, the generated
factory (dist/createObjectModel.js, transpiled from src/createObjectModel.ts) and decals.js."""
import re
from pathlib import Path

here = Path(__file__).parent

def strip(js: str) -> str:
    js = js.replace("import * as THREE from 'three';\n", "")
    return re.sub(r"^export (?=(function|const|class|type|let)\b)", "", js, flags=re.M)

page = (here / "page.template.html").read_text()
factory = strip((here / "dist/createObjectModel.js").read_text()).replace("\"url\": \"material-evidence/", "\"url\": \"3d/material-evidence/")
page = page.replace("/*__FACTORY__*/", factory)
page = page.replace("/*__DECALS__*/", strip((here / "decals.js").read_text()))
(here.parent / "index.html").write_text(page)
print("index.html", len(page), "bytes")
