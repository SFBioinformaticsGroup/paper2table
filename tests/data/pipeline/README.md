# Project title

**Members:** [Name 1], [Name 2]

**Topic:** [project topic]

## Goal and question

*Write this before running the pipeline.*

- **Question:** [What...?]
- **Goal:** Using the table extracted from the papers, we want to [...].
- **Information needed from the papers:** [...]

## Papers used

| Title | DOI or link | License |
|---|---|---|
| 85611977005.tables | Arias Toledo, B. (2009). Diversidad de usos, prácticas de recolección y diferencias según género y edad en el uso de plantas medicinales en Córdoba, Argentina. *Boletín Latinoamericano y del Caribe de Plantas Medicinales y Aromáticas*, *8*(5), 389-401. | [...] |

## Tools and version

- paper2table 0.0.post1.dev479+g4cf580178.d20261020
- pymupdf 1.26.6
- google-gla:gemini-2.5-flash

## Data model

**What each row represents:** [e.g.: a data point from a paper / a site / a study]

**Files:**
- `gathers/csv/`: output from `tablegather`, unmodified.
- `[path/to/curated.csv]`: same structure, with manual corrections.

**Columns:**

| Column | Description | Type | Example | Alternative names | Hand-curated |
|---|---|---|---|---|---|
| familia | [...] | text | [...] |  | [...] |
| nombre_cientifico | [...] | text | [...] |  | [...] |
| nombre_popular | [...] | text | [...] |  | [...] |

**Conventions:**
- Missing values: [how they are marked, e.g.: empty cell]
- Units: [...]
- Date format: [...]
- Allowed values: [if any column has a fixed set]

**Changes between raw and curated:** [no columns added or removed / column X was added]

## Results

What table was obtained and what it shows. Mention the result files.

## Curation

- **Corrections made:** [count]
- **Types of errors found:** [e.g.: incorrectly extracted values, missing data]
- **Open issues:** [links or numbers]
