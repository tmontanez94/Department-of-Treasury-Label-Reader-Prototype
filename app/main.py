from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict
import re, io, json, shutil, tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
UPLOADED_DIR = DATA_DIR / "Uploaded Labels"
VERIFIED_DIR = DATA_DIR / "Labels Verified"
REJECTED_DIR = DATA_DIR / "Labels Rejected"
UNVERIFIED_DIR = DATA_DIR / "Unverified Labels"
TEMPLATES_DIR = DATA_DIR / "Templates"
REVIEW_THRESHOLD = 60

for d in [UPLOADED_DIR, VERIFIED_DIR, REJECTED_DIR, UNVERIFIED_DIR, TEMPLATES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Department of Treasury Label Reader Prototype API", version="11.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploaded", StaticFiles(directory=str(UPLOADED_DIR)), name="uploaded")
app.mount("/verified", StaticFiles(directory=str(VERIFIED_DIR)), name="verified")
app.mount("/rejected", StaticFiles(directory=str(REJECTED_DIR)), name="rejected")
app.mount("/unverified", StaticFiles(directory=str(UNVERIFIED_DIR)), name="unverified")

HUMAN_REVIEW_NOTE = "Human review required: This prototype extracts and checks required label text, but final compliance review is required"

FIELD_HEADERS = {
    "brand_name": ["BRAND NAME", "BRAND"],
    "class_type": ["CLASS TYPE", "CLASS/TYPE", "TYPE"],
    "alcohol_content": ["ALCOHOL CONTENT", "ABV", "ALCOHOL BY VOLUME"],
    "net_contents": ["NET CONTENTS", "NET"],
    "producer_address": ["PRODUCER ADDRESS", "PRODUCER", "BOTTLED BY", "DISTILLED BY"],
    "country_of_origin": ["COUNTRY OF ORIGIN", "COUNTRY", "PRODUCT OF", "IMPORTED FROM"],
    "government_warning": ["GOVERNMENT HEALTH WARNING", "GOVERNMENT WARNING", "WARNING"],
}
ALL_HEADERS = [h for values in FIELD_HEADERS.values() for h in values]

class ExtractedFields(BaseModel):
    brand_name: str = ""
    class_type: str = ""
    alcohol_content: str = ""
    net_contents: str = ""
    producer_address: str = ""
    country_of_origin: str = ""
    government_warning: str = ""

class LabelRecord(BaseModel):
    id: str
    filename: str
    image_url: str
    extracted_text: str
    ocr_confidence: float
    extracted_fields: ExtractedFields
    validation_score: int
    status: str
    compliance_agent_review_required: bool
    missing_required_fields: List[str]
    human_review_note: str
    template_used: str = ""
    template_confidence: int = 0

class QueueResponse(BaseModel):
    labels: List[LabelRecord]

class ManualCorrectionRequest(BaseModel):
    id: str
    extracted_text: str
    extracted_fields: ExtractedFields

class TemplateRequest(BaseModel):
    id: str
    template_name: str
    brand_name: str = ""
    class_type: str = ""
    alcohol_content: str = ""
    net_contents: str = ""
    producer_address: str = ""
    government_warning: str = ""

def safe_name(filename: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)

def normalize(text: str) -> str:
    text = text or ""
    text = text.replace("’", "'").replace("`", "'").replace("Alc-NVol", "Alc./Vol").replace("ALC-NVOL", "ALC./VOL")
    return re.sub(r"\s+", " ", text).strip()

def strip_label(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"^(BRAND NAME|BRAND|CLASS TYPE|CLASS/TYPE|TYPE|ALCOHOL CONTENT|ABV|ALCOHOL BY VOLUME|NET CONTENTS|NET|PRODUCER ADDRESS|PRODUCER|COUNTRY OF ORIGIN|COUNTRY|GOVERNMENT HEALTH WARNING|GOVERNMENT WARNING|WARNING)\s*[:\-]?\s*", "", value, flags=re.I)
    return normalize(value)

def header_regex(header: str) -> str:
    return re.escape(header).replace(r"\ ", r"\s+").replace(r"\/", r"\s*/?\s*")

def between(text: str, start_headers: List[str]) -> str:
    flat = normalize(text)
    starts = "|".join(header_regex(h) for h in start_headers)
    stops = "|".join(header_regex(h) for h in ALL_HEADERS if h.upper() not in {s.upper() for s in start_headers})
    match = re.search(rf"(?:{starts})\s*[:\-]?\s*(.*?)(?=\s+(?:{stops})\s*[:\-]?|$)", flat, flags=re.I)
    return strip_label(match.group(1)) if match else ""

def extract_abv(text: str) -> str:
    labeled = between(text, FIELD_HEADERS["alcohol_content"])
    if labeled and re.search(r"\d", labeled): return labeled
    flexible = normalize(text).replace("ALC-NVOL", "ALC VOL").replace("ALC./VOL", "ALC VOL")
    for pattern in [r"\b\d+(?:\.\d+)?\s*%\s*(?:ALC\.?\s*/?\s*VOL\.?|ALC\s*VOL|ALCOHOL BY VOLUME|ABV)\b(?:\s*\(\s*\d+(?:\.\d+)?\s*PROOF\s*\))?", r"\b\d+(?:\.\d+)?\s*%\s*ABV\b", r"\b\d+(?:\.\d+)?\s*PROOF\b"]:
        m = re.search(pattern, flexible, re.I)
        if m: return normalize(m.group(0))
    return ""

def extract_net(text: str) -> str:
    labeled = between(text, FIELD_HEADERS["net_contents"])
    if labeled and re.search(r"\d", labeled): return labeled
    for pattern in [r"\b\d+(?:\.\d+)?\s*(?:ML|MILLILITERS|L|LITER|LITERS)\b", r"\b\d+(?:\.\d+)?\s*(?:FL\.?\s*OZ\.?|OUNCES)\b"]:
        m = re.search(pattern, text, re.I)
        if m: return normalize(m.group(0))
    return ""

def extract_warning(text: str) -> str:
    labeled = between(text, FIELD_HEADERS["government_warning"])
    if labeled:
        return labeled if "GOVERNMENT WARNING" in labeled.upper() else "GOVERNMENT WARNING: " + labeled
    idx = text.upper().find("GOVERNMENT WARNING")
    if idx < 0: idx = text.upper().find("GOVERNMENT")
    return "" if idx < 0 else normalize(text[idx:idx+750])

def extract_producer(text: str) -> str:
    labeled = between(text, FIELD_HEADERS["producer_address"])
    if labeled: return labeled
    for line in [x.strip() for x in text.splitlines() if x.strip()]:
        u = line.upper()
        if any(k in u for k in ["DISTILLED","BOTTLED","PRODUCED","BREWED","WINERY","DISTILLERY","IMPORT","CELLARS","COMPANY","SPIRITS"]) and not re.search(r"\b\d+(?:\.\d+)?\s*(?:%|ML|L|PROOF|OZ)\b", u):
            return normalize(line)
    return ""

def extract_country(text: str) -> str:
    labeled = between(text, FIELD_HEADERS["country_of_origin"])
    if labeled: return labeled
    m = re.search(r"\b(?:PRODUCT OF|IMPORTED FROM|COUNTRY OF ORIGIN)[:\s]+([A-Z][A-Za-z\s]+)", text, re.I)
    return normalize(m.group(0)) if m else ""

def extract_brand_class(text: str, abv: str, net: str, producer: str):
    brand = between(text, FIELD_HEADERS["brand_name"])
    cls = between(text, FIELD_HEADERS["class_type"])
    if brand or cls: return brand, cls
    useful = []
    for line in [x.strip() for x in text.splitlines() if x.strip()]:
        u = line.upper()
        if "GOVERNMENT WARNING" in u: break
        if any(k in u for k in ["BRAND NAME","CLASS","ALCOHOL","NET CONTENTS","PRODUCER","WARNING"]): continue
        if abv and abv.upper() in u: continue
        if net and net.upper() in u: continue
        if producer and line == producer: continue
        if re.search(r"\b\d+(?:\.\d+)?\s*(?:%|ML|L|PROOF|OZ)\b", u): continue
        useful.append(line)
    return (normalize(useful[0]) if len(useful)>0 else "", normalize(useful[1]) if len(useful)>1 else "")

def extract_fields(text: str) -> ExtractedFields:
    abv = extract_abv(text)
    net = extract_net(text)
    producer = extract_producer(text)
    brand, cls = extract_brand_class(text, abv, net, producer)
    return ExtractedFields(
        brand_name=brand,
        class_type=cls,
        alcohol_content=abv,
        net_contents=net,
        producer_address=producer,
        country_of_origin=extract_country(text),
        government_warning=extract_warning(text),
    )

def score(fields: ExtractedFields, text: str):
    required = {
        "Brand Name":fields.brand_name, "Class/Type":fields.class_type, "Alcohol Content":fields.alcohol_content,
        "Net Contents":fields.net_contents, "Producer/Address":fields.producer_address, "Government Health Warning":fields.government_warning
    }
    missing = [k for k,v in required.items() if not normalize(v)]
    val = 0 if not normalize(text) else round(((len(required)-len(missing))/len(required))*100)
    needs = bool(missing) or val < REVIEW_THRESHOLD
    return val, ("COMPLIANCE AGENT REVIEW REQUIRED" if needs else "PASS"), needs, missing

def build_record(label_id, filename, image_url, text, confidence, fields, template_used="", template_confidence=0):
    val, status, needs, missing = score(fields, text)
    if template_used and not missing:
        val = 100
        status = "PASS"
        needs = False
    return LabelRecord(
        id=label_id, filename=filename, image_url=image_url, extracted_text=text, ocr_confidence=round(confidence,1),
        extracted_fields=fields, validation_score=val, status=status, compliance_agent_review_required=needs,
        missing_required_fields=missing, human_review_note=HUMAN_REVIEW_NOTE,
        template_used=template_used, template_confidence=template_confidence
    )

def save_record(r: LabelRecord):
    (UPLOADED_DIR / f"{r.id}.json").write_text(r.model_dump_json(indent=2), encoding="utf-8")

def load_record(path: Path):
    return LabelRecord(**json.loads(path.read_text(encoding="utf-8")))

def load_queue():
    labels = []
    for p in sorted(UPLOADED_DIR.glob("*.json")):
        try: labels.append(load_record(p))
        except Exception: pass
    labels.sort(key=lambda x: (x.compliance_agent_review_required, x.validation_score, x.filename))
    return labels

OCR_READER = None
def get_reader():
    global OCR_READER
    if OCR_READER is None:
        import easyocr
        OCR_READER = easyocr.Reader(["en"], gpu=False)
    return OCR_READER

def preprocess(contents: bytes, filename: str):
    from PIL import Image, ImageOps
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    image = ImageOps.exif_transpose(image)
    if image.width > 1400:
        ratio = 1400 / image.width
        image = image.resize((1400, int(image.height * ratio)))
    suffix = Path(filename).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        image.save(tmp.name)
        return tmp.name

def run_ocr(contents: bytes, filename: str):
    try:
        results = get_reader().readtext(preprocess(contents, filename), detail=1, paragraph=False, batch_size=4, decoder="greedy", workers=0)
        text = "\n".join([i[1] for i in results])
        conf = sum(float(i[2]) for i in results) / len(results) if results else 0
        return text, conf * 100
    except Exception:
        return "", 0

def template_path(name: str) -> Path:
    return TEMPLATES_DIR / f"{safe_name(name)}.json"

def load_templates() -> List[dict]:
    templates = []
    for p in TEMPLATES_DIR.glob("*.json"):
        try: templates.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception: pass
    return templates

def apply_template_if_matched(filename: str, text: str, fields: ExtractedFields):
    combined = f"{filename} {text} {fields.brand_name}".upper()
    for t in load_templates():
        keys = [t.get("template_name",""), t.get("brand_name","")]
        if any(k and k.upper() in combined for k in keys):
            f = ExtractedFields(
                brand_name=t.get("brand_name","") or fields.brand_name,
                class_type=t.get("class_type","") or fields.class_type,
                alcohol_content=t.get("alcohol_content","") or fields.alcohol_content,
                net_contents=t.get("net_contents","") or fields.net_contents,
                producer_address=t.get("producer_address","") or fields.producer_address,
                country_of_origin=fields.country_of_origin,
                government_warning=t.get("government_warning","") or fields.government_warning,
            )
            return f, t.get("template_name","Saved Template"), 98
    return fields, "", 0

@app.get("/")
def home(): return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/queue", response_model=QueueResponse)
def get_queue(): return QueueResponse(labels=load_queue())

@app.post("/api/analyze-batch", response_model=QueueResponse)
async def analyze_batch(files: List[UploadFile] = File(...)):
    existing = len(list(UPLOADED_DIR.glob("*.json"))) + len(list(VERIFIED_DIR.glob("*.json")))
    for idx, file in enumerate(files, start=1):
        original = safe_name(file.filename or f"label-{idx}.png")
        label_id = f"label-{existing+idx:04d}"
        image_name = f"{label_id}_{original}"
        contents = await file.read()
        (UPLOADED_DIR / image_name).write_bytes(contents)
        text, conf = run_ocr(contents, original)
        fields = extract_fields(text)
        fields, tname, tconf = apply_template_if_matched(original, text, fields)
        record = build_record(label_id, original, f"/uploaded/{image_name}", text, conf, fields, tname, tconf)
        save_record(record)
    return QueueResponse(labels=load_queue())

@app.post("/api/manual-correction", response_model=LabelRecord)
def manual_correction(payload: ManualCorrectionRequest):
    path = UPLOADED_DIR / f"{payload.id}.json"
    if not path.exists(): raise HTTPException(status_code=404, detail="Label not found")
    cur = load_record(path)
    combined = "\n".join([payload.extracted_text, payload.extracted_fields.brand_name, payload.extracted_fields.class_type, payload.extracted_fields.alcohol_content, payload.extracted_fields.net_contents, payload.extracted_fields.producer_address, payload.extracted_fields.country_of_origin, payload.extracted_fields.government_warning])
    updated = build_record(payload.id, cur.filename, cur.image_url, combined, 100, payload.extracted_fields, cur.template_used, cur.template_confidence)
    save_record(updated)
    return updated

@app.post("/api/template", response_model=LabelRecord)
def create_template(payload: TemplateRequest):
    path = UPLOADED_DIR / f"{payload.id}.json"
    if not path.exists(): raise HTTPException(status_code=404, detail="Label not found")
    cur = load_record(path)
    template = payload.model_dump()
    template["source_filename"] = cur.filename
    template_path(payload.template_name).write_text(json.dumps(template, indent=2), encoding="utf-8")
    fields = ExtractedFields(
        brand_name=payload.brand_name or cur.extracted_fields.brand_name,
        class_type=payload.class_type or cur.extracted_fields.class_type,
        alcohol_content=payload.alcohol_content or cur.extracted_fields.alcohol_content,
        net_contents=payload.net_contents or cur.extracted_fields.net_contents,
        producer_address=payload.producer_address or cur.extracted_fields.producer_address,
        country_of_origin=cur.extracted_fields.country_of_origin,
        government_warning=payload.government_warning or cur.extracted_fields.government_warning,
    )
    updated = build_record(cur.id, cur.filename, cur.image_url, cur.extracted_text, cur.ocr_confidence, fields, payload.template_name, 100)
    save_record(updated)
    return updated


@app.post("/api/reject/{label_id}", response_model=QueueResponse)
def reject_label(label_id: str):
    path = UPLOADED_DIR / f"{label_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Label not found")
    record = load_record(path)
    record.status = "NOT IN COMPLIANCE"
    record.compliance_agent_review_required = True
    (REJECTED_DIR / f"{label_id}.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
    image_name = Path(record.image_url).name
    if (UPLOADED_DIR / image_name).exists():
        shutil.move(str(UPLOADED_DIR / image_name), str(REJECTED_DIR / image_name))
    path.unlink(missing_ok=True)
    return QueueResponse(labels=load_queue())

@app.post("/api/verify/{label_id}", response_model=QueueResponse)
def verify_label(label_id: str):
    path = UPLOADED_DIR / f"{label_id}.json"
    if not path.exists(): raise HTTPException(status_code=404, detail="Label not found")
    record = load_record(path)
    (VERIFIED_DIR / f"{label_id}.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
    image_name = Path(record.image_url).name
    if (UPLOADED_DIR / image_name).exists():
        shutil.move(str(UPLOADED_DIR / image_name), str(VERIFIED_DIR / image_name))
    path.unlink(missing_ok=True)
    return QueueResponse(labels=load_queue())
