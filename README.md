# cATO Advisor

AI-powered ATO artifact impact detection and Security Impact Analysis generation.

When a code change is made to a system under ATO, cATO Advisor automatically detects which of the 50 ATO artifacts are affected, classifies the change under FedRAMP's 4-tier significant change framework, maps impacts to NIST 800-53 controls, and generates a draft Security Impact Analysis (SIA) document — saving ISSOs 4–8 hours of manual work per change.

---

## Run it locally

```bash
cd /Users/Wilcore/Development/cato-advisor
```

**Backend:**
```bash
cd backend
cp ../.env.example .env          # add your ANTHROPIC_API_KEY
.venv/bin/uvicorn main:app --reload --port 8000
```

**Frontend (separate terminal):**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` — three tabs: Diff Analyzer, Manual Intake, SIA Generator.

---

## What it does

### UC1 — Diff Analyzer
Paste a git diff or enter a GitHub PR URL. The analyzer detects which of 15 code-detectable change types are present (dependency updates, auth changes, infrastructure changes, new external integrations, etc.), maps them to affected ATO artifacts and NIST 800-53 controls, and assigns a FedRAMP significant change tier.

### UC2 — Manual Intake
Report non-code changes (organizational changes, policy updates, vendor changes, scope changes) via structured forms or plain-English AI classification. Produces the same artifact and control impact output as UC1.

### UC3 — SIA Generator
Auto-generates a draft Security Impact Analysis document from any classified change. Downloadable as DOCX for ISSO editing and AO submission.

---

## Structure

```
cato-advisor/
├── backend/
│   ├── core/
│   │   ├── diff_analyzer.py      # Pattern matching for 15 change types
│   │   ├── llm_fallback.py       # Claude API for ambiguous changes
│   │   ├── mapping_engine.py     # Change → artifacts → controls → tier
│   │   └── sia_generator.py      # SIA document builder (DOCX)
│   ├── data/
│   │   ├── artifacts.json        # All 50 ATO artifacts
│   │   ├── change_taxonomy.json  # 27 change types (15 code + 12 manual)
│   │   └── tiers.json            # FedRAMP 4-tier classification rules
│   ├── routers/
│   │   ├── analysis.py           # UC1 endpoints
│   │   ├── manual_intake.py      # UC2 endpoints
│   │   └── documents.py          # UC3 endpoints
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── DiffAnalyzer.tsx
│       │   ├── ManualIntake.tsx
│       │   └── SIAViewer.tsx
│       └── components/
│           └── ImpactReport.tsx
└── docker-compose.yml
```

---

## Environment

```
ANTHROPIC_API_KEY=sk-ant-...
```
