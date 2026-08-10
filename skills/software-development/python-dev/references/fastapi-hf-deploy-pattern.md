# FastAPI + HuggingFace Hub Deployment Pattern

## Final Working Configuration (Tested May 2026)

### Project Structure
```
project/
├── app.py              # FastAPI backend
├── index.html          # Frontend (Jinja2 template)
├── requirements.txt    # Dependencies
└── .gitignore
```

### app.py (Production-Ready)

```python
import os
import re
import torch
from fastapi import FastAPI, Request
from pydantic import BaseModel
from transformers import T5ForConditionalGeneration, T5Tokenizer
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI(title="Text Summarizer App", version="1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)

# Load model from HuggingFace Hub
HF_MODEL = "username/model_name"  # underscore, not hyphen
model = T5ForConditionalGeneration.from_pretrained(HF_MODEL)
tokenizer = T5Tokenizer.from_pretrained(HF_MODEL)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

class DialogueInput(BaseModel):
    dialogue: str

def clean_data(text):
    text = re.sub(r"\r\n", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"<.*?>", " ", text)
    text = text.strip().lower()
    return text

def summarize_dialogue(dialogue: str) -> str:
    dialogue = clean_data(dialogue)
    inputs = tokenizer(dialogue, padding="max_length", max_length=512,
                       truncation=True, return_tensors="pt").to(device)
    with torch.no_grad():
        targets = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=150, num_beams=4, early_stopping=True
        )
    return tokenizer.decode(targets[0], skip_special_tokens=True)

@app.post("/summarize/")
async def summarize(dialogue_input: DialogueInput):
    return {"summary": summarize_dialogue(dialogue_input.dialogue)}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### Key Fixes from Tutorial Code
1. `torch.cuda.is_availanle()` → `is_available()` (typo)
2. `Jinja2Templates(directory=".")` → use `BASE_DIR` absolute path
3. Added `model.eval()` — reduces memory
4. Added `torch.no_grad()` — reduces inference memory ~30-40%
5. Use HF Hub model name instead of local path for deployment

### Resume Wording
- CORRECT: "Hosted the fine-tuned model on HuggingFace Hub"
- CORRECT: "Built a REST API using FastAPI"
- WRONG: "Deployed on HuggingFace website"
- WRONG: "Deployed the model on HuggingFace"