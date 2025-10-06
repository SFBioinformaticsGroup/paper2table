<div align="center">

# Manual Curator – paper2table

An web interface to manually curate structured tabular data extracted with paper2table from scientific papers (multi‑file, row‑wise or cell‑wise) ensuring provenance, metadata awareness and export-ready curated outputs.

</div>

## ✨ Key Features

- Multi‑file tasks: import several JSON extraction outputs as one curation task.
- Metadata‑aware ingestion: table 0 (if present) treated as document metadata (not counted as data rows) but available for display.
- Dual curation modes: Row‑by‑row or Cell‑by‑cell random navigation via `/next` endpoint.
- Stable progress tracking: Monotonic progress using authoritative backend calculation.
- Agreement highlighting: Adjustable Minimum Agreement slider to visually flag low-agreement options.
- Safe incremental saving: Only persisted when you advance (explicit navigation), avoiding accidental partial states.
- Per‑file curated exports: One curated JSON per original file, with `{ value, curated }` objects unwrapped on export.
- Shuffle + reset: Full reset of curated state with fresh randomized order.
- Theming & accessibility: Light/Dark toggle via simple swatches, semantic tokens, reduced color noise.

## 🧱 Architecture Overview

| Layer | Stack | Notes |
|-------|-------|-------|
| Frontend | React + Vite | Pure client SPA; design tokens in CSS vars. |
| Backend | Express (Node) | Provides task lifecycle & curation endpoints. |
| Data model | JSON (tables[]) | First table optional metadata; subsequent tables contain data rows. |

### Data Expectations
Each imported file is expected to follow a structure similar to:

```jsonc
{
	"tables": [
		{ "table_fragments": [ { "rows": [ { "authors": "...", "year": "..." } ] } ] }, // metadata (optional)
		{ "table_fragments": [ { "rows": [ { "field_a": [ {"value": "x", "agreement_level": 5}, ... ] } ] } ] }
	],
	"citation": "Optional citation string"
}
```

During curation option arrays are wrapped to record the selected value as:
```json
{ "field_a": { "value": "chosen option", "curated": true } }
```

On export these wrapper objects are unwrapped to provide clean output values.

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Run Backend & Frontend (two terminals or add a concurrent script)
```bash
node server/index.js   # starts API (default PORT 3001)
npm run dev            # starts Vite dev server
```

If you prefer a single command, add to `package.json` (needs `concurrently`):
```jsonc
"scripts": {
	"dev:api": "node server/index.js",
	"dev:web": "vite",
	"dev": "concurrently \"npm:dev:api\" \"npm:dev:web\""
}
```

### 3. Open the App
Navigate to the Vite dev URL (often http://localhost:5173) — the frontend will call the API (http://localhost:3001 by default).

## 📡 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/tasks` | Create a new multi‑file task (stores originals) |
| GET | `/api/tasks` | List tasks & flattened row set (with per‑row metadata) |
| GET | `/api/tasks/:task/next?mode=row|cell` | Random next uncurated row or cell |
| POST | `/api/tasks/:task/curated/:fileIndex` | Apply selections to a specific file’s curated version |
| GET | `/api/tasks/:task/progress` | Authoritative progress (curatedCells / totalCells) |
| GET | `/api/tasks/:task/original-summary` | Per original file: counts + metadata rows + citation |
| GET | `/api/tasks/:task/export` | Export curated JSONs (one per original) |
| DELETE | `/api/tasks/:task/curated` | Reset curated state (remove curated files) |
| DELETE | `/api/tasks/:task` | Delete entire task directory |
| POST | `/api/tasks/:task/log` | Append a curation action log entry |
| GET | `/api/tasks/:task/log` | Retrieve log entries |
| DELETE | `/api/tasks/:task/log` | Clear log file |

## 🔍 Progress Calculation
The backend scans original files (excluding metadata table) to compute a stable denominator, and curated files to count curated cells. This prevents regressions due to UI race conditions or partial local state.

## 🧪 Example Flow
1. Import 2 JSON extraction files.
2. App creates task → backend stores originals.
3. Open “Current” tab → random row or cell selection via `/next`.
4. Make selections → press “Next” → backend update persists only changed row’s file.
5. Progress endpoint confirms global monotonic increase.
6. When complete → export delivers one curated file per original.

## 🗂 Output Format (Curated)
Each original file produces a curated counterpart whose table structure is preserved; selected cells are embedded as `{ value, curated: true }`. The export endpoint unwraps these to plain values for downstream consumption.

## 🎚 Agreement Highlighting
The Minimum Agreement slider marks low–agreement cells with a left border accent, aiding prioritization.

## ♻️ Reset & Shuffle
Reset deletes curated artifacts and rebuilds progress from zero; rows are reshuffled to avoid bias in sequential review.

## 🎨 Theming
Two minimalist theme swatches (light/dark) with design tokens for: spacing scale, semantic colors (surface, border, accent, warning), typography and radii. Minimal color noise improves focus.

## 🧩 Folder Structure (Condensed)
```
src/
	components/          # React components (candidates: RenderCell, CurrentTasksView, etc.)
	hooks/               # useTheme, useTaskFiles, etc.
	utils/               # api service & task utilities
	constants/           # constant values
server/
	index.js             # Express API
	utils.js             # Extraction & counting helpers
public/                # (Ignored in this repo per .gitignore – adjust if needed)
```



---
Happy curating! 

