
"""
=====================================================================================
 universal_file_viewer.py  -  ONE file that runs in Google Colab AND on Streamlit
=====================================================================================
 Upload ANY file -> it is read as text AND shown as images, charts, diagrams,
 tables or media players wherever possible.

 ▶ ON STREAMLIT CLOUD (GitHub)
     Put this file in your repo and set it as the "Main file path".
     The repo also needs requirements.txt and packages.txt (see the bottom of
     this docstring). Those are settings lists for the server, not code.

 ▶ IN GOOGLE COLAB (3 short cells)
     Cell 1:  first line   %%writefile universal_file_viewer.py
              then paste this WHOLE file below it, and run the cell.
              (Or just upload this .py file with Colab's 📁 Files panel.)
     Cell 2:  %run universal_file_viewer.py
              -> installs anything missing (first time only, ~1-2 min),
                 shows an Upload button, and displays the results right in Colab.
     Cell 3:  %run universal_file_viewer.py --host        (optional)
              -> starts the Streamlit app and prints a public web link.

 ▶ requirements.txt (add these lines to your existing list):
       pandas, numpy, matplotlib, pillow, pymupdf, python-docx, python-pptx,
       openpyxl, chardet, pytesseract, opencv-python-headless   (one per line)
 ▶ packages.txt (system programs, NO comment lines in that file):
       tesseract-ocr
       tesseract-ocr-hin
       tesseract-ocr-guj

 ─────────────── MINI PYTHON GLOSSARY (read once, refer back anytime) ───────────────
  variable   a name that stores a value              age = 25
  str        text                                    "hello"
  bytes      raw file data (numbers 0-255)           b"\\x89PNG..."
  list       ordered collection                      [1, 2, 3]
  dict       key -> value pairs                      {"name": "Saavan", "age": 25}
  tuple      fixed collection                        (1, "a")
  set        collection without duplicates           {"png", "jpg"}
  function   reusable block of code                  def add(a, b): return a + b
  import     load code written by others (a "library" / "module")
  f-string   text with values inside                 f"Hi {name}" -> "Hi Saavan"
  try/except "try this; if it crashes, do this instead"
  with ...:  open something and close it automatically afterwards
  list comprehension   short way to build a list      [x * 2 for x in nums]
  None       "nothing / no value"         True / False   yes / no
=====================================================================================
"""
# (The text above, between triple quotes, is a "docstring": notes for humans.
#  Python skips it when running.)


# =====================================================================
# PART 0 - WHERE ARE WE RUNNING?  (and auto-install in Colab)
# Only built-in libraries here, because they always exist.
# =====================================================================
import importlib.util   # lets us check "is this library installed?" without importing it
import shutil           # shutil.which("tesseract") -> finds a program on the computer
import subprocess       # runs other programs (pip, apt-get, streamlit, cloudflared)
import sys              # info about Python itself, e.g. sys.argv = command-line words


def running_in_streamlit():
    """True when this file is being run by 'streamlit run'."""
    try:
        from streamlit.runtime import exists     # only works if streamlit is installed
        return exists()
    except Exception:                            # not installed / not running -> False
        return False


# find_spec returns None when a module doesn't exist. google.colab exists only in Colab.
IN_COLAB = importlib.util.find_spec("google.colab") is not None

# python "import name" -> "pip install name" (they are not always the same!)
PIP_PACKAGES = {
    "streamlit": "streamlit", "fitz": "pymupdf", "docx": "python-docx",
    "pptx": "python-pptx", "openpyxl": "openpyxl", "chardet": "chardet",
    "pytesseract": "pytesseract", "graphviz": "graphviz", "cv2": "opencv-python-headless",
}


def install_colab_dependencies():
    """Install whatever is missing, so Colab needs no separate install cell."""
    # list comprehension: keep the pip name of every module that isn't installed
    missing = [pip_name for module, pip_name in PIP_PACKAGES.items()
               if importlib.util.find_spec(module) is None]
    if missing:
        print("📦 Installing:", ", ".join(missing), "(first run only)...")
        # sys.executable = this Python. "-m pip" runs pip for exactly this Python.
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=False)
    if shutil.which("tesseract") is None or shutil.which("dot") is None:
        print("📦 Installing OCR (English, Hindi, Gujarati) and Graphviz...")
        subprocess.run("apt-get -qq install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-guj "
                       "graphviz > /dev/null", shell=True, check=False)
    importlib.invalidate_caches()                # make Python notice the new packages


# Run the installer only in Colab, and not inside the Streamlit process it may start.
if IN_COLAB and not running_in_streamlit():
    install_colab_dependencies()


# =====================================================================
# PART 1 - IMPORTS
# =====================================================================
import ast              # reads Python code as a "tree" (to find functions/classes)
import base64           # bytes <-> safe text (to embed images inside HTML)
import collections      # Counter (counts things), OrderedDict (dict that keeps order)
import functools        # lru_cache: remember a function's answer so it runs only once
import html             # html.escape() makes text safe to put inside HTML
import io               # io.BytesIO = a "file" that lives in memory
import json             # reads JSON
import mimetypes        # guesses a file type from its name
import os               # file names, paths, permissions
import re               # regular expressions: text search patterns
import time             # time.sleep()
import zipfile          # opens .zip files (docx/pptx/xlsx are zips inside!)
import xml.etree.ElementTree as ET    # reads XML ("as ET" = short nickname)
from dataclasses import dataclass, field

import numpy as np              # fast maths on many numbers
import pandas as pd             # tables (DataFrames), like Excel in Python
import matplotlib.pyplot as plt # charts
from PIL import Image, ExifTags # Pillow: images

# OPTIONAL libraries: if one is missing we set it to None instead of crashing,
# and every feature checks "if xxx is None" before using it.
try:
    import fitz                        # PyMuPDF -> PDFs
except ImportError:
    fitz = None
try:
    import docx                        # python-docx -> Word .docx
except ImportError:
    docx = None
try:
    from pptx import Presentation      # python-pptx -> PowerPoint .pptx
except ImportError:
    Presentation = None
try:
    import chardet                     # guesses text encodings
except ImportError:
    chardet = None
try:
    import pytesseract                 # OCR: text inside images
except ImportError:
    pytesseract = None
try:
    import cv2                         # OpenCV: cleans images before OCR (better accuracy)
except ImportError:
    cv2 = None
try:
    import streamlit as st             # the web-app library
    import streamlit.components.v1 as components   # shows custom HTML (Mermaid, web pages)
except ImportError:
    st = components = None


# =====================================================================
# PART 2 - SETTINGS  (CAPITAL names = "constants": set once, easy to tweak)
# =====================================================================
MAX_TEXT_CHARS = 50_000        # "_" in numbers is only for readability
MAX_TABLE_ROWS = 1_000
MAX_PDF_PAGES = 5              # pages turned into pictures (text covers ALL pages)
MAX_EMBEDDED_IMAGES = 12
MAX_TREE_NODES = 150           # max boxes in a generated diagram
MAX_MEDIA_MB = 40              # bigger audio/video isn't embedded in Colab

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".ico"}
AUDIO_EXT = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
             ".m4a": "audio/mp4", ".flac": "audio/flac", ".aac": "audio/aac"}
VIDEO_EXT = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
             ".m4v": "video/mp4", ".ogv": "video/ogg"}
GRAPHVIZ_EXT = {".dot", ".gv"}
MERMAID_EXT = {".mmd", ".mermaid"}
CODE_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "javascript",
    ".java": "java", ".c": "c", ".h": "c", ".cpp": "cpp", ".cs": "csharp", ".go": "go",
    ".rs": "rust", ".rb": "ruby", ".php": "php", ".sh": "bash", ".sql": "sql",
    ".css": "css", ".yaml": "yaml", ".yml": "yaml", ".r": "r", ".kt": "kotlin",
    ".swift": "swift", ".toml": "toml", ".ini": "ini", ".json": "json", ".xml": "xml",
    ".html": "html", ".htm": "html", ".md": "markdown",
}
# Little words we skip in the "most frequent words" chart
STOPWORDS = set("""the and for are but not you all any can had her was one our out has have
him his how its may new now old see two way who did get let put say she too use with this that
from they will would there their what about which when your into than them then these some were
been also just more only over such very like here where while each other most must should could""".split())

# Which tab each kind of output goes into
SECTION_OF = {
    "info": "Overview", "note": "Overview", "warning": "Overview",
    "text": "Text", "code": "Text", "markdown": "Text",
    "image": "Visuals", "svg": "Visuals", "chart": "Charts",
    "graphviz": "Diagrams", "mermaid": "Diagrams",
    "table": "Data", "json": "Data",
    "html": "Preview", "audio": "Preview", "video": "Preview",
}
SECTION_ORDER = ["Overview", "Text", "Visuals", "Charts", "Diagrams", "Data", "Preview"]
ICONS = {"Overview": "ℹ️", "Text": "📝", "Visuals": "🖼️", "Charts": "📊",
         "Diagrams": "🧭", "Data": "🗃️", "Preview": "▶️"}

# Graphviz "DOT" is a mini-language for diagrams (a -> b;). This sets the look.
DOT_HEADER = ('digraph G {\n  rankdir=LR;\n'
              '  node [shape=box, style="rounded,filled", fillcolor="#EEF3FB", fontname="Helvetica", fontsize=10];\n'
              '  edge [color="#888888"];')


# =====================================================================
# PART 3 - THE "Output" BOX + SMALL HELPERS
# BIG IDEA: the analyze functions never DRAW anything. They return a list of
# Output objects ("show this text", "show this chart"...). Then the Streamlit
# part or the Colab part decides HOW to display them. Same brain, two faces.
# =====================================================================
@dataclass            # a "decorator" that auto-writes the setup code for a data class
class Output:
    """kind  : info | note | warning | text | code | markdown | image | svg | chart |
               graphviz | mermaid | table | json | html | audio | video
       data  : the content (text, bytes, table, chart, dict ...)
       title : heading shown above it
       extra : extra settings, e.g. {"language": "python"} or {"mime": "audio/mpeg"}"""
    kind: str                                   # ": str" is a type hint (a note for humans)
    data: object = None                         # "= None" is a default value
    title: str = ""
    extra: dict = field(default_factory=dict)   # every Output gets its OWN empty dict


def group_outputs(outputs):
    """Put outputs into tabs (sections), keeping their order."""
    groups = collections.OrderedDict((s, []) for s in SECTION_ORDER)
    for o in outputs:
        groups[SECTION_OF.get(o.kind, "Overview")].append(o)   # .get(key, default)
    return groups


def get_ext(name):
    """'Report.PDF' -> '.pdf'"""
    return os.path.splitext(name)[1].lower()


def human_size(n):
    """1536 -> '1.5 KB'"""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"   # :.1f = 1 decimal
        n /= 1024
    return f"{n:.1f} TB"


def q(text, maxlen=40):
    """Make text safe as a Graphviz label (escape quotes/backslashes, shorten)."""
    s = str(text).replace("\n", " ").replace("\\", "\\\\").replace('"', '\\"')
    if len(s) > maxlen:
        s = s[:maxlen - 1] + "…"                 # s[:10] = first 10 characters
    return f'"{s}"'


def truncate(text, limit=MAX_TEXT_CHARS):
    """Shorten very long text so the page stays fast."""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n... [truncated: showing {limit:,} of {len(text):,} characters]"


def unique_columns(cols):
    """Tables can't repeat a column name -> 'Name', 'Name_2', 'Name_3'..."""
    seen, out = collections.Counter(), []
    for c in cols:
        c = str(c).strip() or "column"           # "x or y" -> y when x is empty
        seen[c] += 1
        out.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
    return out


def sniff(data):
    """Guess the REAL type from the first bytes ("magic numbers"), ignoring the name."""
    if data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff") or data[:4] == b"GIF8":
        return "image"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio"
    if data.startswith(b"ID3") or data[:4] in (b"fLaC", b"OggS"):
        return "audio"
    if data[4:8] == b"ftyp":
        return "video"
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return "zip"
    return None


def looks_binary(data):
    """Binary files (like .exe) contain null bytes / many control characters; text doesn't."""
    sample = data[:8192]
    if not sample:
        return False
    if b"\x00" in sample:
        return True
    control = sum(1 for b in sample if b < 9 or 13 < b < 32)
    return control / len(sample) > 0.10


def decode_text(data):
    """bytes -> str. Try UTF-8, then chardet's guess, then latin-1 (never fails).
    Returns TWO values: (text, encoding_name)."""
    try:
        return data.decode("utf-8-sig"), "UTF-8"
    except UnicodeDecodeError:
        pass
    if chardet is not None:
        guess = chardet.detect(data[:200_000]).get("encoding")
        if guess:
            try:
                return data.decode(guess), guess
            except (UnicodeDecodeError, LookupError):
                pass
    return data.decode("latin-1"), "latin-1 (fallback)"


def image_bytes_for_display(img, raw=None):
    """Browsers show PNG/JPEG/GIF/WEBP directly; other formats are converted to PNG."""
    if raw is not None and img.format in ("PNG", "JPEG", "GIF", "WEBP"):
        return raw
    buf = io.BytesIO()
    try:
        frame = img if img.mode in ("RGB", "RGBA", "L") else img.convert("RGBA")
    except Exception:
        frame = img.convert("RGB")
    frame.save(buf, format="PNG")                # save into the memory "file"
    return buf.getvalue()                        # take the bytes back out


def raw_image_to_display(raw):
    """Image bytes -> displayable bytes, or None if Pillow can't read it."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        return image_bytes_for_display(img, raw)
    except Exception:
        return None


def mermaid_html(src, height=450):
    """HTML that draws a Mermaid diagram in the browser ({{ }} = literal braces in f-strings)."""
    return f"""
<div class="mermaid" style="min-height:{height - 50}px">{html.escape(src)}</div>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{ startOnLoad: true }});
</script>"""


def svg_html(svg_text):
    b64 = base64.b64encode(svg_text.encode("utf-8")).decode()
    return f'<img src="data:image/svg+xml;base64,{b64}" style="max-width:100%;max-height:600px">'


def bar_chart(labels, values, title, xlabel="", horizontal=True):
    """Make a bar chart and RETURN it (it is displayed later)."""
    labels = [str(l)[:30] for l in labels]
    if horizontal:
        fig, ax = plt.subplots(figsize=(7, max(2.5, 0.35 * len(labels))))
        ax.barh(labels[::-1], values[::-1], color="#4C78A8")    # [::-1] reverses -> biggest on top
        ax.set_xlabel(xlabel)
    else:
        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.bar(labels, values, color="#4C78A8")
        ax.set_ylabel(xlabel)
        ax.tick_params(axis="x", rotation=45)
    ax.set_title(title)
    fig.tight_layout()
    return fig


# =====================================================================
# PART 4 - OCR (reading text inside pictures)
# Tesseract reads best when text is big, sharp and black-on-white, so we
# clean the image a few ways, try a few layout modes, and keep the best.
# =====================================================================
@functools.lru_cache(maxsize=1)       # remember the answer -> this only runs once
def ocr_languages():
    """Use English + Hindi + Gujarati, but only the ones actually installed."""
    if pytesseract is None:
        return "eng"
    try:
        available = set(pytesseract.get_languages(config=""))
        wanted = [lang for lang in ("eng", "hin", "guj") if lang in available]
        return "+".join(wanted) or "eng"         # e.g. "eng+hin+guj"
    except Exception:
        return "eng"


def ocr_variants(img):
    """Yield cleaned-up versions of the image. 'yield' hands them out one at a time."""
    gray = np.array(img.convert("L"))            # "L" = grayscale; numpy array of pixels
    if cv2 is None:                              # without OpenCV: just use grayscale
        yield gray
        return
    h, w = gray.shape
    if max(h, w) < 1500:                         # enlarge small images (letters ~30px tall is ideal)
        factor = 1500 / max(h, w)
        gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    gray = cv2.fastNlMeansDenoising(gray, h=10)  # remove grainy noise
    yield gray
    # Otsu: pure black text on pure white, picking the cut-off automatically
    yield cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # Adaptive: a different cut-off per area -> handles shadows and uneven light
    yield cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)


def ocr_best(img):
    """Return (best_text, confidence_percent).
    PSM = page layout mode: 3 = full page, 6 = one block of text, 11 = scattered text (signs)."""
    if pytesseract is None:
        return None, 0.0
    langs = ocr_languages()
    candidates = []                              # (average confidence, word count, config, image)
    for variant in ocr_variants(img):
        for psm in (3, 6, 11):
            config = f"--oem 1 --psm {psm}"      # oem 1 = Tesseract's neural-network engine
            try:
                d = pytesseract.image_to_data(variant, lang=langs, config=config,
                                              output_type=pytesseract.Output.DICT)
            except Exception:
                continue                         # skip this try, go to the next one
            confs = [float(c) for t, c in zip(d["text"], d["conf"]) if t.strip() and float(c) >= 0]
            if confs:
                candidates.append((sum(confs) / len(confs), len(confs), config, variant))
    if not candidates:
        return None, 0.0
    # Ignore versions that found far fewer words, then pick the most confident one.
    most_words = max(c[1] for c in candidates)
    good = [c for c in candidates if c[1] >= 0.7 * most_words]
    conf, _, config, variant = max(good, key=lambda c: c[0])   # key= tells max() what to compare
    try:
        text = pytesseract.image_to_string(variant, lang=langs, config=config).strip()
    except Exception:
        return None, 0.0
    return (text or None), conf


def ocr_text(img):
    """Just the text (used for scanned PDFs)."""
    return ocr_best(img)[0]


# =====================================================================
# PART 5 - TEXT (every file ends up as text in some form)
# =====================================================================
def text_outputs(text, title="Text content", language=None, word_chart=True):
    """Statistics + the text itself + a word-frequency chart."""
    lines = text.splitlines()
    outs = [Output("info", {
        "Characters": f"{len(text):,}",                       # {x:,} -> 50,000
        "Words": f"{len(re.findall(r'\S+', text)):,}",          # \S+ = a run of non-spaces
        "Lines": f"{len(lines):,}",
        "Non-empty lines": f"{sum(1 for l in lines if l.strip()):,}",
    }, f"{title} – statistics")]
    outs.append(Output("code" if language else "text", truncate(text), title, {"language": language}))
    if word_chart:
        # [^\W\d_]{3,} = words of 3+ letters in ANY language (English, Hindi, Gujarati...)
        words = [w.lower() for w in re.findall(r"[^\W\d_]{3,}", text)]
        counts = collections.Counter(w for w in words if w not in STOPWORDS).most_common(15)
        if len(counts) >= 3:
            labels, values = zip(*counts)        # [("a",5),("b",3)] -> ("a","b"), (5,3)
            outs.append(Output("chart", bar_chart(list(labels), list(values), "Most frequent words", "count"),
                               f"{title} – word frequency"))
    return outs


MERMAID_START = ("graph ", "graph\n", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram",
                 "erDiagram", "gantt", "pie", "journey", "mindmap", "timeline", "gitGraph")


def diagram_outputs_from_text(text):
    """Turn diagrams written as text (```mermaid / ```dot blocks, or whole files) into pictures."""
    outs = []
    for lang, body in re.findall(r"```(mermaid|dot|graphviz)[^\n]*\n(.*?)```", text, re.S | re.I):
        kind = "mermaid" if lang.lower() == "mermaid" else "graphviz"
        outs.append(Output(kind, body.strip(), f"{lang} diagram found in text"))
    if not outs:
        s = text.lstrip()
        if re.match(r"(strict\s+)?(di)?graph\b", s, re.I) and "{" in s:
            outs.append(Output("graphviz", s, "Graphviz diagram"))
        elif s.startswith(MERMAID_START):
            outs.append(Output("mermaid", s, "Mermaid diagram"))
    return outs


def python_structure_dot(code):
    """Diagram of a Python file: classes, methods, functions, who-calls-whom."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    func_ids = {f.name: f"f{i}" for i, f in enumerate(funcs)}     # dict comprehension
    lines = [DOT_HEADER, '  module [label="module", shape=folder, fillcolor="#D6EAF8"];']
    imports, count = [], 0
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports += [f"{node.module}.{a.name}" for a in node.names]
        elif isinstance(node, ast.ClassDef):
            cid = f"c{count}"; count += 1
            lines.append(f'  {cid} [label={q("class " + node.name)}, fillcolor="#FDEBD0"];')
            lines.append(f"  module -> {cid};")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and count < MAX_TREE_NODES:
                    mid = f"m{count}"; count += 1
                    lines.append(f"  {mid} [label={q(item.name + '()')}];")
                    lines.append(f"  {cid} -> {mid};")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += 1
            lines.append(f"  {func_ids[node.name]} [label={q(node.name + '()')}];")
            lines.append(f"  module -> {func_ids[node.name]};")
    calls = set()                                # set = no duplicates
    for f in funcs:
        for sub in ast.walk(f):                  # visit every piece inside the function
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                    and sub.func.id in func_ids and sub.func.id != f.name:
                calls.add((f.name, sub.func.id))
    for a, b in calls:
        lines.append(f'  {func_ids[a]} -> {func_ids[b]} [style=dashed, color="#C0392B", label="calls", fontsize=8];')
    if imports:
        label = "imports: " + ", ".join(imports[:12]) + (" …" if len(imports) > 12 else "")
        lines.append(f'  imports [label={q(label, 120)}, shape=note, fillcolor="#E8F8F5"];')
        lines.append("  module -> imports;")
    if count == 0 and not imports:
        return None
    lines.append("}")
    return "\n".join(lines)


def headings_dot(title, headings):
    """[(level, text), ...] -> outline tree (level-2 hangs under the level-1 above it)."""
    lines = [DOT_HEADER, f'  root [label={q(title)}, shape=folder, fillcolor="#D6EAF8"];']
    stack = [(0, "root")]                        # remembers the current chain of parents
    for i, (level, text) in enumerate(headings[:MAX_TREE_NODES]):
        nid = f"h{i}"
        lines.append(f"  {nid} [label={q(text)}];")
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()                          # go back up to a smaller level
        lines.append(f"  {stack[-1][1]} -> {nid};")
        stack.append((level, nid))
    lines.append("}")
    return "\n".join(lines)


def analyze_text(data, ext):
    text, encoding = decode_text(data)
    language = CODE_LANG.get(ext)
    outs = [Output("note", f"Read as text using the {encoding} encoding.")]
    outs += text_outputs(text, "File content", language, word_chart=language in (None, "markdown"))
    if ext == ".py":
        dot = python_structure_dot(text)
        if dot:
            outs.append(Output("graphviz", dot, "Code structure (classes, functions, calls)"))
    return outs + diagram_outputs_from_text(text)


# =====================================================================
# PART 6 - ONE FUNCTION PER FILE TYPE
# =====================================================================
def analyze_image(data):
    img = Image.open(io.BytesIO(data))
    img.load()
    info = {"Format": img.format, "Dimensions": f"{img.width} × {img.height} px",
            "Colour mode": img.mode, "Frames": getattr(img, "n_frames", 1)}
    try:
        for tag_id, value in list(img.getexif().items())[:15]:          # hidden photo details
            info[f"EXIF {ExifTags.TAGS.get(tag_id, tag_id)}"] = str(value)[:60]
    except Exception:
        pass
    outs = [Output("info", info, "Image details"),
            Output("image", image_bytes_for_display(img, data), "Image preview")]
    try:                                         # colour histogram
        hist = img.convert("RGB").histogram()    # 256 red + 256 green + 256 blue numbers
        fig, ax = plt.subplots(figsize=(7, 3))
        for i, colour in enumerate(("red", "green", "blue")):
            ax.plot(range(256), hist[i * 256:(i + 1) * 256], color=colour, label=colour)
        ax.set_title("Colour histogram"); ax.set_xlabel("pixel value (0–255)"); ax.legend()
        fig.tight_layout()
        outs.append(Output("chart", fig, "Colour distribution"))
    except Exception:
        pass
    text, conf = ocr_best(img)                   # "consider it as text"
    if text:
        outs.append(Output("note", f"OCR confidence: {conf:.0f}% (Tesseract's own estimate; "
                                   "below ~80% usually means many mistakes)."))
        outs += text_outputs(text, "Text found in image (OCR)")
    else:
        outs.append(Output("note", "No readable text detected in this image." if pytesseract
                           else "OCR not available - install tesseract + pytesseract."))
    return outs


def analyze_svg(data):
    text, _ = decode_text(data)                  # "_" = a value we don't need
    return [Output("svg", text, "SVG preview")] + text_outputs(text, "SVG source", "xml", word_chart=False)


def analyze_pdf(data):
    if fitz is None:
        return [Output("warning", "PyMuPDF is not installed, so the PDF is shown as raw data.")] + analyze_binary(data)
    doc = fitz.open(stream=data, filetype="pdf")
    meta = doc.metadata or {}
    outs = [Output("info", {"Pages": doc.page_count, "Title": meta.get("title") or "–",
                            "Author": meta.get("author") or "–", "Created with": meta.get("producer") or "–"},
                   "PDF details")]
    page_texts, rendered = [], []
    for i, page in enumerate(doc):
        page_texts.append(page.get_text())
        if i < MAX_PDF_PAGES:
            png = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).tobytes("png")   # 150% zoom
            rendered.append(png)
            outs.append(Output("image", png, f"Page {i + 1}"))
    if doc.page_count > MAX_PDF_PAGES:
        outs.append(Output("note", f"First {MAX_PDF_PAGES} pages shown as images; the text covers all {doc.page_count} pages."))
    # Scanned PDF = photos of pages with no real text -> use OCR
    if sum(len(t.strip()) for t in page_texts) < 50 and pytesseract is not None:
        ocr = [ocr_text(Image.open(io.BytesIO(p))) or "" for p in rendered]
        if any(ocr):
            page_texts = ocr
            outs.append(Output("note", "This looks like a scanned PDF - text was read with OCR."))
    full_text = "\n\n".join(f"--- Page {i + 1} ---\n{t}" for i, t in enumerate(page_texts))
    outs += text_outputs(full_text, "Extracted text")
    if 1 < len(page_texts) <= 60:
        counts = [len(t.split()) for t in page_texts]
        outs.append(Output("chart", bar_chart([str(i + 1) for i in range(len(counts))], counts,
                                              "Words per page", "words", horizontal=False), "Words per page"))
    seen, found = set(), 0                       # pictures stored inside the PDF
    for page in doc:
        for im in page.get_images(full=True):
            xref = im[0]                         # the PDF's internal id for the picture
            if xref in seen or found >= MAX_EMBEDDED_IMAGES:
                continue
            seen.add(xref)
            try:
                shown = raw_image_to_display(doc.extract_image(xref)["image"])
            except Exception:
                shown = None
            if shown:
                found += 1
                outs.append(Output("image", shown, f"Embedded image {found} (page {page.number + 1})"))
    return outs


def zip_images(data, prefix):
    """Office files keep their pictures in a media folder inside the zip."""
    outs = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [n for n in z.namelist() if n.startswith(prefix) and get_ext(n) in IMAGE_EXT]
        for n in names[:MAX_EMBEDDED_IMAGES]:
            shown = raw_image_to_display(z.read(n))
            if shown:
                outs.append(Output("image", shown, f"Embedded image: {os.path.basename(n)}"))
    return outs


def analyze_docx(data):
    if docx is None:
        return [Output("warning", "python-docx is not installed.")] + analyze_zip(data)
    d = docx.Document(io.BytesIO(data))
    md, headings, plain = [], [], []
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        plain.append(t)
        style = (p.style.name if p.style is not None else "").lower()    # e.g. "heading 2"
        if style.startswith("heading") or style == "title":
            digits = re.findall(r"\d+", style)
            level = int(digits[0]) if digits else 1
            md.append("#" * min(level + 1, 6) + " " + t)                  # markdown heading
            headings.append((level, t))
        elif "list" in style:
            md.append(f"- {t}")
        else:
            md.append(t)
    outs = [Output("info", {"Paragraphs": len(plain), "Headings": len(headings), "Tables": len(d.tables)},
                   "Word document details"),
            Output("markdown", "\n\n".join(md) or "_(no text)_", "Document (formatted)")]
    outs += text_outputs("\n".join(plain), "Document text")
    if headings:
        outs.append(Output("graphviz", headings_dot("Document", headings), "Document outline"))
    for i, t in enumerate(d.tables, 1):
        rows = [[c.text for c in r.cells] for r in t.rows]
        if rows:
            df = pd.DataFrame(rows[1:], columns=unique_columns(rows[0])) if len(rows) > 1 else pd.DataFrame(rows)
            outs.append(Output("table", df, f"Table {i}"))
    return outs + zip_images(data, "word/media/")


def analyze_pptx(data):
    if Presentation is None:
        return [Output("warning", "python-pptx is not installed.")] + analyze_zip(data)
    prs = Presentation(io.BytesIO(data))
    md, all_text, titles, words_per_slide = [], [], [], []
    for i, slide in enumerate(prs.slides, 1):
        title_shape = slide.shapes.title
        title = title_shape.text.strip() if title_shape is not None and title_shape.text.strip() else f"Slide {i}"
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts += [p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip()]
        notes = ""
        if slide.has_notes_slide:
            frame = slide.notes_slide.notes_text_frame
            notes = frame.text.strip() if frame is not None else ""
        body = "\n".join(f"- {t}" for t in texts if t != title)
        md.append(f"### Slide {i}: {title}\n{body}" + (f"\n\n> Notes: {notes}" if notes else ""))
        all_text += [title] + texts + ([notes] if notes else [])
        titles.append((1, f"{i}. {title}"))
        words_per_slide.append(len(" ".join(texts).split()))
    outs = [Output("info", {"Slides": len(prs.slides)}, "Presentation details"),
            Output("markdown", "\n\n".join(md), "Slides (text)")]
    outs += text_outputs("\n".join(all_text), "Presentation text")
    if titles:
        outs.append(Output("graphviz", headings_dot("Presentation", titles), "Slide outline"))
    if len(words_per_slide) > 1:
        outs.append(Output("chart", bar_chart([str(i + 1) for i in range(len(words_per_slide))], words_per_slide,
                                              "Words per slide", "words", horizontal=False), "Words per slide"))
    return outs + zip_images(data, "ppt/media/")


def safe_nunique(series):
    try:
        return series.nunique()                  # number of different values
    except TypeError:
        return -1


def dataframe_outputs(df, title):
    """Any table: summary, data, statistics and automatic charts."""
    df = df.copy()
    df.columns = unique_columns(df.columns)
    num = df.select_dtypes(include="number")     # numeric columns only
    outs = [Output("info", {"Rows": f"{len(df):,}", "Columns": len(df.columns),
                            "Numeric columns": len(num.columns),
                            "Missing values": f"{int(df.isna().sum().sum()):,}"}, f"{title} – summary"),
            Output("table", df.head(MAX_TABLE_ROWS),
                   title + (f" (first {MAX_TABLE_ROWS:,} rows)" if len(df) > MAX_TABLE_ROWS else ""))]
    if not num.empty:
        outs.append(Output("table", num.describe().T.round(3), f"{title} – statistics"))
        cols = list(num.columns[:4])             # histograms of up to 4 columns
        fig, axes = plt.subplots(1, len(cols), figsize=(3.6 * len(cols), 3))
        for ax, c in zip(np.atleast_1d(axes), cols):
            ax.hist(num[c].dropna(), bins=20, color="#4C78A8")
            ax.set_title(str(c)[:25], fontsize=9)
        fig.suptitle("Distributions"); fig.tight_layout()
        outs.append(Output("chart", fig, f"{title} – distributions"))
        if len(df) > 1:                          # values row by row
            fig, ax = plt.subplots(figsize=(8, 3.2))
            for c in num.columns[:3]:
                ax.plot(num[c].values[:5000], label=str(c)[:25])
            ax.set_title("Values by row"); ax.set_xlabel("row"); ax.legend(); fig.tight_layout()
            outs.append(Output("chart", fig, f"{title} – trend"))
        if len(num.columns) >= 2:                # do columns move together?
            corr = num.iloc[:, :12].corr()
            fig, ax = plt.subplots(figsize=(5.5, 4.5))
            im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr))); ax.set_xticklabels([str(c)[:12] for c in corr.columns], rotation=45, ha="right")
            ax.set_yticks(range(len(corr))); ax.set_yticklabels([str(c)[:12] for c in corr.columns])
            fig.colorbar(im); ax.set_title("Correlation between numeric columns"); fig.tight_layout()
            outs.append(Output("chart", fig, f"{title} – correlation"))
    cat_cols = [c for c in df.columns if c not in num.columns and 1 < safe_nunique(df[c]) <= 30]
    if cat_cols:                                 # e.g. counts per "City"
        c = cat_cols[0]
        vc = df[c].astype(str).value_counts().head(15)
        outs.append(Output("chart", bar_chart(list(vc.index), list(vc.values), f"Counts of '{c}'", "count"),
                           f"{title} – categories"))
    return outs


def analyze_csv(data, ext):
    text, _ = decode_text(data)
    sep = "\t" if ext == ".tsv" else None        # None + engine="python" = auto-detect , ; |
    df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
    return dataframe_outputs(df, "Table") + text_outputs(text, "Raw text", word_chart=False)


def analyze_excel(data):
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)   # ALL sheets as a dict
    outs = [Output("info", {"Sheets": ", ".join(map(str, sheets.keys()))}, "Workbook details")]
    for name, df in sheets.items():
        outs += dataframe_outputs(df, f"Sheet '{name}'")
        outs.append(Output("text", truncate(df.to_csv(index=False)), f"Sheet '{name}' as text"))
    return outs


def json_tree_dot(obj):
    """JSON as a tree. RECURSION: add() calls itself for every child."""
    lines, count = [DOT_HEADER], [0]

    def add(o, label):
        if count[0] >= MAX_TREE_NODES:
            return None
        nid = f"n{count[0]}"; count[0] += 1
        if isinstance(o, dict):
            text, items = f"{label} {{{len(o)}}}", list(o.items())[:20]
        elif isinstance(o, list):
            text, items = f"{label} [{len(o)}]", [(f"[{i}]", v) for i, v in enumerate(o[:10])]
        else:
            text, items = f"{label}: {o}", []
        lines.append(f"  {nid} [label={q(text)}];")
        for k, v in items:
            cid = add(v, k)
            if cid:
                lines.append(f"  {nid} -> {cid};")
        return nid

    add(obj, "root")
    lines.append("}")
    return "\n".join(lines)


def analyze_json(data):
    text, _ = decode_text(data)
    obj = json.loads(text)
    outs = [Output("json", obj, "JSON data"), Output("graphviz", json_tree_dot(obj), "JSON structure")]
    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj[:50]):
        outs += dataframe_outputs(pd.json_normalize(obj), "JSON records")
    return outs + text_outputs(text, "JSON source", "json", word_chart=False)


def analyze_notebook(data):
    nb = json.loads(decode_text(data)[0])
    cells = nb.get("cells", [])
    kinds = collections.Counter(c.get("cell_type", "?") for c in cells)
    outs = [Output("info", {"Cells": len(cells), **{f"{k} cells": v for k, v in kinds.items()}}, "Notebook details")]
    for i, cell in enumerate(cells[:60], 1):
        src = cell.get("source", "")
        src = "".join(src) if isinstance(src, list) else str(src)
        if cell.get("cell_type") == "markdown":
            outs.append(Output("markdown", src, f"Cell {i} (markdown)"))
            continue
        outs.append(Output("code", src, f"Cell {i} (code)", {"language": "python"}))
        for out in cell.get("outputs", []):
            d = out.get("data", {})
            if "image/png" in d:
                png = d["image/png"]
                png = "".join(png) if isinstance(png, list) else png
                outs.append(Output("image", base64.b64decode(png), f"Cell {i} output image"))
            elif "text/plain" in d or "text" in out:
                t = d.get("text/plain", out.get("text", ""))
                outs.append(Output("text", "".join(t) if isinstance(t, list) else str(t), f"Cell {i} output"))
    return outs


def analyze_markdown(data):
    text, _ = decode_text(data)
    outs = [Output("markdown", text, "Rendered markdown")] + text_outputs(text, "Markdown source", "markdown")
    headings = [(len(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.M)]
    if headings:
        outs.append(Output("graphviz", headings_dot("Document", headings), "Heading outline"))
    return outs + diagram_outputs_from_text(text)


def analyze_html(data):
    text, _ = decode_text(data)
    visible = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)    # drop scripts/styles
    visible = html.unescape(re.sub(r"<[^>]+>", " ", visible))        # drop tags
    visible = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", visible)).strip()
    outs = [Output("info", {"Links": len(re.findall(r"<a\s", text, re.I)),
                            "Images": len(re.findall(r"<img\s", text, re.I))}, "HTML details"),
            Output("html", text, "Rendered page")]
    outs += text_outputs(visible, "Visible text")
    return outs + text_outputs(text, "HTML source", "html", word_chart=False)


def xml_tree_dot(root):
    lines, count = [DOT_HEADER], [0]

    def add(el):
        if count[0] >= MAX_TREE_NODES:
            return None
        nid = f"x{count[0]}"; count[0] += 1
        tag = el.tag.split("}")[-1]              # remove {namespace}
        txt = (el.text or "").strip()
        lines.append(f"  {nid} [label={q(tag + (': ' + txt if txt else ''))}];")
        for child in list(el)[:15]:
            cid = add(child)
            if cid:
                lines.append(f"  {nid} -> {cid};")
        return nid

    add(root)
    lines.append("}")
    return "\n".join(lines)


def analyze_xml(data):
    text, _ = decode_text(data)
    outs = []
    try:
        outs.append(Output("graphviz", xml_tree_dot(ET.fromstring(data)), "XML structure"))
    except ET.ParseError as e:
        outs.append(Output("warning", f"XML could not be parsed: {e}"))
    return outs + text_outputs(text, "XML source", "xml", word_chart=False)


def analyze_media(data, ext, kind):
    mime = AUDIO_EXT.get(ext, "audio/mpeg") if kind == "audio" else VIDEO_EXT.get(ext, "video/mp4")
    return [Output(kind, data, f"{kind.title()} player", {"mime": mime}),
            Output("note", f"{kind.title()} has no text layer to show; play it in the Preview tab.")]


def folder_tree_dot(paths):
    nodes = {"": "root"}
    lines = [DOT_HEADER, '  root [label="(archive)", shape=folder, fillcolor="#D6EAF8"];']
    for p in paths:
        parts = [x for x in p.strip("/").split("/") if x]
        for depth in range(1, len(parts) + 1):
            key = "/".join(parts[:depth])
            if key in nodes or len(nodes) > MAX_TREE_NODES:
                continue
            nid = f"z{len(nodes)}"
            nodes[key] = nid
            shape = ", shape=folder" if depth < len(parts) else ""
            lines.append(f"  {nid} [label={q(parts[depth - 1])}{shape}];")
            lines.append(f"  {nodes['/'.join(parts[:depth - 1])]} -> {nid};")
    lines.append("}")
    return "\n".join(lines)


def analyze_zip(data):
    outs = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        outs.append(Output("info", {"Files inside": len(infos),
                                    "Total uncompressed": human_size(sum(i.file_size for i in infos))},
                           "Archive details"))
        outs.append(Output("table", pd.DataFrame([{"File": i.filename, "Size": human_size(i.file_size),
                                                   "Compressed": human_size(i.compress_size)} for i in infos[:500]]),
                           "Contents"))
        types = collections.Counter(get_ext(i.filename) or "(none)" for i in infos).most_common(12)
        if types:
            labels, values = zip(*types)
            outs.append(Output("chart", bar_chart(list(labels), list(values), "Files by type", "files"), "File types"))
        outs.append(Output("graphviz", folder_tree_dot([i.filename for i in infos]), "Folder structure"))
        shown_img = shown_txt = 0
        for i in infos:
            ext = get_ext(i.filename)
            if ext in IMAGE_EXT and shown_img < MAX_EMBEDDED_IMAGES:
                img = raw_image_to_display(z.read(i))
                if img:
                    outs.append(Output("image", img, i.filename)); shown_img += 1
            elif shown_txt < 3 and i.file_size < 200_000:
                raw = z.read(i)
                if not looks_binary(raw):
                    outs.append(Output("code", truncate(decode_text(raw)[0], 20_000), f"Preview: {i.filename}",
                                       {"language": CODE_LANG.get(ext)}))
                    shown_txt += 1
    return outs


def hex_dump(data, n=512):
    """offset | bytes in hexadecimal | readable characters"""
    rows = []
    for off in range(0, min(len(data), n), 16):
        chunk = data[off:off + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        rows.append(f"{off:08x}  {hex_part:<47}  {ascii_part}")
    return "\n".join(rows)


def analyze_binary(data):
    """Unknown binary: readable strings (= its text), hex dump and a byte chart."""
    sample = np.frombuffer(data[:5_000_000], dtype=np.uint8)
    counts = np.bincount(sample, minlength=256)
    p = counts[counts > 0] / max(len(sample), 1)
    entropy = float(-(p * np.log2(p)).sum())    # ~8 = compressed or encrypted
    outs = [Output("info", {"Entropy (bits/byte)": f"{entropy:.2f}  (8 = random/compressed/encrypted)"},
                   "Binary details")]
    strings = [s.decode("ascii") for s in re.findall(rb"[\x20-\x7e]{4,}", data[:5_000_000])][:400]
    if strings:
        outs += text_outputs("\n".join(strings), "Readable text found inside the file")
    outs.append(Output("code", hex_dump(data), "Hex dump (first 512 bytes)", {"language": "text"}))
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(range(256), counts, color="#4C78A8", width=1.0)
    ax.set_title("Byte value distribution"); ax.set_xlabel("byte value (0–255)"); ax.set_ylabel("count")
    fig.tight_layout()
    outs.append(Output("chart", fig, "Byte histogram"))
    return outs


# =====================================================================
# PART 7 - THE BRAIN: decide the file type and collect all outputs
# =====================================================================
def analyze(name, data):
    ext, kind = get_ext(name), sniff(data)      # type from the NAME, and from the CONTENT
    guessed = mimetypes.guess_type(name)[0]
    outs = [Output("info", {"File name": name, "Extension": ext or "(none)",
                            "Detected type": guessed or kind or ("text" if not looks_binary(data) else "binary"),
                            "Size": human_size(len(data))}, "File details")]
    if not data:
        return outs + [Output("warning", "The file is empty.")]
    try:
        # if/elif chain: the FIRST matching line wins, so the order matters
        if ext == ".svg":
            outs += analyze_svg(data)
        elif ext in IMAGE_EXT or kind == "image":
            outs += analyze_image(data)
        elif ext == ".pdf" or kind == "pdf":
            outs += analyze_pdf(data)
        elif ext == ".docx":
            outs += analyze_docx(data)
        elif ext == ".pptx":
            outs += analyze_pptx(data)
        elif ext in (".xlsx", ".xlsm", ".xls"):
            outs += analyze_excel(data)
        elif ext in (".csv", ".tsv"):
            outs += analyze_csv(data, ext)
        elif ext == ".ipynb":
            outs += analyze_notebook(data)
        elif ext == ".json":
            outs += analyze_json(data)
        elif ext in (".md", ".markdown"):
            outs += analyze_markdown(data)
        elif ext in (".html", ".htm"):
            outs += analyze_html(data)
        elif ext == ".xml":
            outs += analyze_xml(data)
        elif ext in AUDIO_EXT or kind == "audio":
            outs += analyze_media(data, ext, "audio")
        elif ext in VIDEO_EXT or kind == "video":
            outs += analyze_media(data, ext, "video")
        elif ext in (".zip", ".jar", ".apk", ".epub") or kind == "zip":
            outs += analyze_zip(data)
        elif ext in GRAPHVIZ_EXT:
            text, _ = decode_text(data)
            outs += [Output("graphviz", text, "Graphviz diagram")] + text_outputs(text, "DOT source", "text", False)
        elif ext in MERMAID_EXT:
            text, _ = decode_text(data)
            outs += [Output("mermaid", text, "Mermaid diagram")] + text_outputs(text, "Mermaid source", "text", False)
        elif not looks_binary(data):
            outs += analyze_text(data, ext)      # .txt, .log, code ...
        else:
            outs += analyze_binary(data)         # .exe, .bin, .dat ...
    except Exception as e:
        # Safety net: a corrupt or mislabelled file never crashes the app
        outs.append(Output("warning", f"Couldn't fully read this as '{ext or 'unknown'}' "
                                      f"({type(e).__name__}: {e}). Showing it as text instead."))
        outs += analyze_text(data, ext) if not looks_binary(data) else analyze_binary(data)
    return outs


def capabilities():
    """Which optional features work right now (shown in the sidebar)."""
    ocr_ok = False
    if pytesseract is not None:
        try:
            pytesseract.get_tesseract_version()  # fails if the tesseract PROGRAM is missing
            ocr_ok = True
        except Exception:
            pass
    return {"PDF (PyMuPDF)": fitz is not None, "Word (python-docx)": docx is not None,
            "PowerPoint (python-pptx)": Presentation is not None,
            "Encoding detection (chardet)": chardet is not None,
            "OCR (tesseract)": ocr_ok,
            f"OCR languages: {ocr_languages() if ocr_ok else '-'}": ocr_ok,
            "OCR image clean-up (OpenCV)": cv2 is not None}


# =====================================================================
# PART 8 - FACE #1: STREAMLIT WEB APP
# Remember: Streamlit re-runs the WHOLE file each time the user does something.
# =====================================================================
def st_render(o):
    """Show ONE Output with the matching Streamlit command."""
    if o.title:
        st.markdown(f"**{o.title}**")
    k = o.kind
    if k == "info":
        st.dataframe(pd.DataFrame({"Property": list(o.data.keys()),
                                   "Value": [str(v) for v in o.data.values()]}), hide_index=True)
    elif k == "note":
        st.info(o.data)
    elif k == "warning":
        st.warning(o.data)
    elif k == "text":
        with st.container(height=400):           # scrollable box
            st.text(o.data)
    elif k == "code":
        with st.container(height=400):
            st.code(o.data, language=o.extra.get("language") or None)
    elif k == "markdown":
        with st.container(height=500):
            st.markdown(o.data)
    elif k == "image":
        st.image(o.data)
    elif k == "svg":
        st.markdown(svg_html(o.data), unsafe_allow_html=True)
    elif k == "chart":
        st.pyplot(o.data)
        plt.close(o.data)                        # free memory
    elif k == "table":
        try:
            st.dataframe(o.data)
        except Exception:
            st.dataframe(o.data.astype(str))     # mixed types -> show as text
    elif k == "json":
        st.json(o.data)
    elif k == "graphviz":
        try:
            st.graphviz_chart(o.data)
        except Exception as e:
            st.warning(f"Diagram couldn't be drawn: {e}")
            st.code(o.data)
    elif k == "mermaid":
        components.html(mermaid_html(o.data), height=480, scrolling=True)
    elif k == "html":
        components.html(o.data, height=500, scrolling=True)
    elif k == "audio":
        st.audio(o.data, format=o.extra.get("mime", "audio/mpeg"))
    elif k == "video":
        st.video(o.data, format=o.extra.get("mime", "video/mp4"))
    st.write("")


def streamlit_main():
    st.set_page_config(page_title="Universal File Viewer", page_icon="🗂️", layout="wide")
    st.title("🗂️ Universal File Viewer")
    st.caption("Upload any file. It's read as text, and shown as images, charts, diagrams, "
               "tables or media wherever possible.")
    with st.sidebar:
        st.header("What it can show")
        st.markdown(
            "- **Text & code**: stats and word charts\n"
            "- **Images**: preview, EXIF, colour histogram, OCR text\n"
            "- **PDF**: page images, text, embedded pictures\n"
            "- **Word / PowerPoint**: text, outline diagram, tables, images\n"
            "- **CSV / Excel / JSON**: tables, statistics, charts\n"
            "- **Diagrams**: Graphviz and Mermaid\n"
            "- **Python**: code-structure diagram\n"
            "- **Audio / video**: players\n"
            "- **ZIP**: contents, folder tree, previews\n"
            "- **Anything else**: readable strings, hex dump, byte chart"
        )
        st.subheader("Optional features")
        for feature, ok in capabilities().items():
            st.write(("✅ " if ok else "❌ ") + feature)

    files = st.file_uploader("Upload one or more files (any type)", accept_multiple_files=True)
    if not files:
        st.info("⬆️ Upload a file to begin.")
        return
    for f in files:
        st.divider()
        data = f.getvalue()                      # file content as bytes
        st.header(f"📄 {f.name}  ·  {human_size(len(data))}")
        with st.spinner("Analysing file..."):
            groups = group_outputs(analyze(f.name, data))
        sections = [s for s in SECTION_ORDER if groups[s]]
        tabs = st.tabs([f"{ICONS[s]} {s} ({len(groups[s])})" for s in sections])
        for tab, s in zip(tabs, sections):
            with tab:
                for o in groups[s]:
                    st_render(o)


# =====================================================================
# PART 9 - FACE #2: COLAB / JUPYTER OUTPUT
# =====================================================================
def colab_render(o):
    """Show ONE Output in the notebook output area."""
    from IPython.display import display, HTML, Markdown   # imported here: only notebooks have it

    def box(text):                               # scrollable box for long text
        return HTML(f"<pre style='max-height:400px;overflow:auto;white-space:pre-wrap;"
                    f"border:1px solid #ddd;padding:8px'>{html.escape(text)}</pre>")

    if o.title:
        display(HTML(f"<b>{html.escape(o.title)}</b>"))
    k = o.kind
    if k == "info":
        display(pd.DataFrame({"Property": list(o.data.keys()), "Value": [str(v) for v in o.data.values()]}))
    elif k in ("note", "warning"):
        colour = "#E8F4FD" if k == "note" else "#FFF4E5"
        display(HTML(f"<div style='background:{colour};padding:8px;border-radius:6px'>{html.escape(o.data)}</div>"))
    elif k in ("text", "code"):
        display(box(o.data))
    elif k == "markdown":
        display(Markdown(o.data))
    elif k == "image":
        fmt = (Image.open(io.BytesIO(o.data)).format or "png").lower()
        b64 = base64.b64encode(o.data).decode()
        display(HTML(f'<img src="data:image/{fmt};base64,{b64}" style="max-width:100%;max-height:600px">'))
    elif k == "svg":
        display(HTML(svg_html(o.data)))
    elif k == "chart":
        display(o.data)
        plt.close(o.data)
    elif k == "table":
        display(o.data)
    elif k == "json":
        display(box(json.dumps(o.data, indent=2, ensure_ascii=False, default=str)[:50_000]))
    elif k == "graphviz":
        try:
            import graphviz
            display(graphviz.Source(o.data))
        except Exception as e:
            display(HTML(f"<i>Diagram couldn't be drawn ({html.escape(str(e))}); DOT source:</i>"))
            display(box(o.data))
    elif k == "mermaid":
        display(HTML(mermaid_html(o.data)))
    elif k == "html":
        display(HTML(f'<iframe srcdoc="{html.escape(o.data)}" sandbox '
                     f'style="width:100%;height:450px;border:1px solid #ccc"></iframe>'))
    elif k in ("audio", "video"):
        if len(o.data) > MAX_MEDIA_MB * 1024 * 1024:
            display(HTML(f"<i>{k.title()} is larger than {MAX_MEDIA_MB} MB; use the Streamlit app.</i>"))
        else:
            b64 = base64.b64encode(o.data).decode()
            tag = "audio" if k == "audio" else "video style='max-width:100%'"
            display(HTML(f"<{tag} controls src='data:{o.extra['mime']};base64,{b64}'></{k}>"))


def colab_main():
    """Colab: show an Upload button. Jupyter/terminal: read file paths given after the file name."""
    from IPython.display import display, HTML
    if IN_COLAB:
        from google.colab import files
        uploaded = files.upload()                # {file name: file bytes}
    else:
        paths = [a for a in sys.argv[1:] if not a.startswith("--")]
        if not paths:
            print("Usage:  %run universal_file_viewer.py path/to/file1 path/to/file2")
            return
        uploaded = {}
        for p in paths:
            with open(p, "rb") as fh:            # "rb" = read bytes
                uploaded[os.path.basename(p)] = fh.read()
    for name, data in uploaded.items():
        display(HTML(f"<hr><h2>📄 {html.escape(name)} · {human_size(len(data))}</h2>"))
        groups = group_outputs(analyze(name, data))
        for section in SECTION_ORDER:
            if groups[section]:
                display(HTML(f"<h3 style='color:#2E86C1'>{ICONS[section]} {section}</h3>"))
                for o in groups[section]:
                    colab_render(o)


# =====================================================================
# PART 10 - HOST THE STREAMLIT APP FROM COLAB  (%run universal_file_viewer.py --host)
# Colab runs on Google's computer, so we use a free Cloudflare "tunnel"
# to get a public link to the app.
# =====================================================================
def host_from_colab(port=8501):
    import urllib.request
    script = os.path.abspath(__file__)           # the path of THIS file
    subprocess.Popen([sys.executable, "-m", "streamlit", "run", script,
                      "--server.port", str(port), "--server.headless", "true"],
                     stdout=open("streamlit.log", "w"), stderr=subprocess.STDOUT)
    time.sleep(5)                                # give Streamlit a moment to start
    if not os.path.exists("cloudflared"):
        print("⬇️ Downloading cloudflared (one time)...")
        urllib.request.urlretrieve(
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
            "cloudflared")
        os.chmod("cloudflared", 0o755)           # make it runnable
    tunnel = subprocess.Popen(["./cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in tunnel.stdout:                   # read its messages until the link appears
        match = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", line)
        if match:
            print("✅ Your app is live at:", match.group(0))
            print("   It keeps running while this Colab session is open. Errors: see streamlit.log")
            return


# =====================================================================
# PART 11 - START HERE: pick the right "face" automatically
# =====================================================================
# __name__ == "__main__" is True when this file is RUN (by streamlit or %run),
# not when another file imports it.
if __name__ == "__main__":
    if running_in_streamlit():
        streamlit_main()                         # Streamlit Cloud, or the app started by --host
    elif "--host" in sys.argv:
        host_from_colab()                        # Colab: public link to the Streamlit app
    else:
        colab_main()                             # Colab/Jupyter: results in the notebook
