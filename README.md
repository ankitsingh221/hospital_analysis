# Healthcare Operations & Patient Analytics

An end-to-end, fully synthetic hospital data analytics pipeline. The project generates realistic-but-messy healthcare data, cleans and validates it, explores it visually, engineers analytical features, and loads the results into SQLite for SQL-based business analysis.

All records are synthetic and contain no real patient information.

---

## Table of Contents

- [Overview](#overview)
- [Project Goals](#project-goals)
- [Pipeline Architecture](#pipeline-architecture)
- [Project Structure](#project-structure)
- [Datasets](#datasets)
- [Pipeline Stages](#pipeline-stages)
- [Setup and Installation](#setup-and-installation)
- [Running the Pipeline](#running-the-pipeline)
- [Outputs](#outputs)
- [Configuration](#configuration)
- [Data Quality Report](#data-quality-report)
- [Known Limitations](#known-limitations)
- [Future Work](#future-work)
- [Repository](#repository)

---

## Overview

This repository is a portfolio-style analytics project that simulates the work required to turn raw healthcare operational data into analysis-ready tables and business insights. The workflow covers the full lifecycle:

1. **Synthetic data generation** with deliberately injected quality problems
2. **Data cleaning and validation** with a before/after quality report
3. **Exploratory data analysis (EDA)** with summary tables and charts
4. **Feature engineering** for encounter-level and patient-level analysis
5. **SQL analysis** using SQLite, with query results exported to CSV

The scripts are plain, standalone Python files with no application framework. Each stage reads from and writes to CSV files in dedicated directories, so every stage can be inspected independently.

---

## Project Goals

The project was built to practice and demonstrate:

- Data cleaning: text normalization, date parsing, numeric coercion, deduplication
- Data validation: range checks, categorical checks, foreign-key checks
- Exploratory data analysis: distributions, frequency tables, trends, outliers
- Feature engineering: age groups, time features, cost-per-day, readmission flags
- SQL analysis: aggregation, ranking, cohort analysis, cost and utilization reporting
- Dashboard preparation: the datasets are structured for a downstream Power BI dashboard (no dashboard artifact is included in this repository)

---

## Pipeline Architecture

```text
generate_data.py
      |
      v
healthcare_raw_data/          (patients, encounters, procedures, payers CSVs)
      |
      v
clean_data.py
      |
      v
healthcare_processed_data/    (cleaned CSVs + data_quality_report.csv)
      |
      +-------------------+---------------------+
      |                   |                     |
      v                   v                     v
analysis/eda.py   analysis/feature_engineering.py  (feeds sql_analysis.py)
      |                   |                     |
      v                   v                     v
eda_outputs/      feature_engineered_data/   sql_outputs/
(charts, CSVs)    (modeling-ready tables)    (SQLite DB + query CSVs)
```

---

## Project Structure

```text
hospital_analysis/
├── generate_data.py                 # Synthetic raw data generator
├── clean_data.py                    # Cleaning, validation, quality report
├── analysis/
│   ├── eda.py                       # Descriptive stats and Matplotlib charts
│   ├── feature_engineering.py       # Derived features and aggregate tables
│   └── sql_analysis.py              # SQLite load and 15 analytical queries
├── healthcare_raw_data/             # Generated raw CSVs
│   ├── patients.csv
│   ├── encounters.csv
│   ├── procedures.csv
│   └── payers.csv
├── healthcare_processed_data/       # Cleaned CSVs and quality report
│   ├── patients_cleaned.csv
│   ├── encounters_cleaned.csv
│   ├── procedures_cleaned.csv
│   ├── payers_cleaned.csv
│   └── data_quality_report.csv
├── feature_engineered_data/         # Analysis-ready tables
│   ├── patients_feature_engineered.csv
│   ├── encounters_feature_engineered.csv
│   ├── encounter_procedure_summary.csv
│   └── patient_summary.csv
├── eda_outputs/                     # EDA result CSVs and PNG charts
├── sql_outputs/                     # Query CSVs and healthcare.db
└── README.md                        # This file
```

---

## Datasets

### Raw data (`healthcare_raw_data/`)

| File | Records | Description |
|---|---:|---|
| `patients.csv` | 974 | Demographics and registration details |
| `encounters.csv` | 27,891 | Hospital visits, diagnoses, admissions, charges, payer information |
| `procedures.csv` | 47,701 | Procedures performed during encounters, with costs and quantities |
| `payers.csv` | 10 | Insurance payer organizations and coverage rates |

Key columns:

- **patients**: `patient_id`, `gender`, `date_of_birth`, `city`, `state`, `blood_group`, `registration_date`, `smoking_status`
- **encounters**: `encounter_id`, `patient_id`, `encounter_date`, `discharge_date`, `admission_type`, `department`, `diagnosis`, `length_of_stay`, `discharge_status`, `payer_id`, `hospital_charges`, `amount_covered`, `patient_responsibility`
- **procedures**: `procedure_id`, `encounter_id`, `procedure_name`, `procedure_category`, `procedure_date`, `procedure_cost`, `quantity`, `performed_by`
- **payers**: `payer_id`, `payer_name`, `payer_type`, `coverage_rate`, `network_type`

The generator intentionally injects: missing values, duplicate IDs, inconsistent capitalization/whitespace, invalid dates, invalid charge/cost/quantity values, impossible lengths of stay, and invalid foreign keys.

### Cleaned data (`healthcare_processed_data/`)

Cleaned datasets keep the original record structure and add derived fields such as:

- `age`, `age_group` (patients)
- `coverage_percentage` (payers)
- `encounter_month`, `encounter_year`, `encounter_month_name`, `actual_length_of_stay`, `length_of_stay_category`, `insurance_coverage_percentage` (encounters)
- `total_procedure_cost`, `procedure_year`, `procedure_month`, `procedure_month_name` (procedures)

### Feature-engineered data (`feature_engineered_data/`)

| File | Description |
|---|---|
| `encounters_feature_engineered.csv` | Main analytical encounter table with time features, cost-per-day, readmission flag, patient demographics, and payer attributes |
| `encounter_procedure_summary.csv` | Encounter table joined with per-encounter procedure aggregates |
| `patients_feature_engineered.csv` | Patient-level table with cleaned demographics and age features |
| `patient_summary.csv` | Patient-level rollups: encounters, charges, length of stay, readmissions, first/last encounter dates |

---

## Pipeline Stages

### 1. Data generation — `generate_data.py`

Generates the four raw CSVs using `numpy.random.default_rng(42)`, so the base data is reproducible. Records are generated with realistic category distributions (departments, diagnoses, admission types, payer types, cities, etc.), then quality defects are introduced by helper functions:

- `inject_missing()` — randomly nulls values in selected columns
- `inject_duplicate_ids()` — creates duplicate primary keys
- `inject_inconsistent_text()` — random casing and whitespace
- `save_dataset()` — writes CSVs and prints shape information
- `print_quality_summary()` — prints missing values and duplicate IDs

### 2. Cleaning and validation — `clean_data.py`

Reads raw CSVs and applies:

- `clean_text()` — trim, collapse whitespace, title-case, null empty strings
- `clean_dates()` — parse dates with invalid values coerced to null
- `clean_numeric()` — coerce numeric columns
- `remove_duplicate_ids()` — keep first occurrence of each ID
- Dataset-specific cleaners: `clean_patients()`, `clean_payers()`, `clean_encounters()`, `clean_procedures()`
- `record_quality()` — capture before/after metrics for `data_quality_report.csv`

Validation includes allowed gender and blood-group values, date validity, length-of-stay range (0–365), hospital charge range (0–100,000), procedure cost range (0–20,000), quantity checks, and foreign-key checks against the cleaned parent tables.

### 3. Exploratory data analysis — `analysis/eda.py`

Produces descriptive statistics (`describe()` transposed) and frequency tables for all four cleaned datasets, plus charts such as:

- Patient gender, city, and age distributions
- Encounters by admission type, department, diagnosis, and discharge status
- Hospital charge histograms and box plots
- Length-of-stay distribution
- Monthly encounter trends
- Average hospital charges by department
- Procedure category distribution and quantity distribution
- Payer type and payer name breakdowns

Outputs are written to `eda_outputs/` as both CSV and PNG files.

### 4. Feature engineering — `analysis/feature_engineering.py`

Builds analysis-ready tables by:

- Standardizing ID columns and parsing dates
- Recomputing patient age and age groups
- Adding encounter year, month, quarter, and `year_month`
- Computing length of stay from dates and cost per hospital day
- Deriving previous discharge date, days since previous discharge, and a 30-day readmission flag
- Aggregating procedures per encounter
- Assigning cost categories and patient/payer attributes
- Creating patient-level visit summaries

Outputs are written to `feature_engineered_data/`.

### 5. SQL analysis — `analysis/sql_analysis.py`

Loads five CSVs into SQLite tables (`patients`, `encounters`, `patient_summary`, `procedures`, `payers`) in `sql_outputs/healthcare.db`, then runs 15 queries:

| # | Query | Description |
|---:|---|---|
| 1 | `01_department_encounters` | Encounter counts by department |
| 2 | `02_monthly_encounters` | Encounters by year-month |
| 3 | `03_top_diagnoses` | Top 15 diagnoses |
| 4 | `04_payer_analysis` | Encounters and charges by payer |
| 5 | `05_department_cost` | Total and average charges by department |
| 6 | `06_high_cost_encounters` | 20 highest-cost encounters |
| 7 | `07_patient_visit_frequency` | Patients with the most visits |
| 8 | `08_readmission_analysis` | 30-day readmission rate by department |
| 9 | `09_average_length_of_stay` | Average length of stay by department |
| 10 | `10_top_patients_by_cost` | Patients with the highest total charges |
| 11 | `11_procedure_category_cost` | Procedure costs by category |
| 12 | `12_payer_patient_responsibility` | Patient payments by payer |
| 13 | `13_quarterly_hospital_cost` | Quarterly charge totals and averages |
| 14 | `14_procedure_volume_by_encounter` | Encounters with the most procedures |
| 15 | `15_patient_demographics` | Patient counts by gender and age group |

Successful results are exported as CSV files and the first 10 rows of each are printed to the console.

---

## Setup and Installation

### Requirements

- Python 3.9 or newer (the project has been run with Python 3.13)
- Packages:
  - `pandas`
  - `numpy`
  - `matplotlib`
- `sqlite3` and `pathlib` are part of the Python standard library

There is no dependency manifest in the repository. To create a clean environment manually:

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install pandas numpy matplotlib
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install pandas numpy matplotlib
```

No database server is required; SQLite is file-based and stored in `sql_outputs/healthcare.db`.

---

## Running the Pipeline

Run the scripts from the `hospital_analysis` directory, in this order:

```powershell
cd "C:\Users\Ankit\Desktop\New folder\hospital_analysis"

python generate_data.py
python clean_data.py
python analysis\eda.py
python analysis\feature_engineering.py
python analysis\sql_analysis.py
```

On macOS/Linux, use forward slashes (e.g. `python analysis/eda.py`).

Notes:

- `generate_data.py` and `clean_data.py` resolve their input/output directories relative to the **current working directory**, so run them from the project root.
- The three scripts under `analysis/` resolve paths relative to their own file location and can be run from anywhere.
- Each script is standalone and executes on import; there are no `main()` guards or command-line arguments.
- All scripts overwrite their outputs on each run. `sql_analysis.py` replaces SQLite tables rather than appending.

---

## Outputs

| Directory | Contents |
|---|---|
| `healthcare_raw_data/` | Four generated synthetic CSV files |
| `healthcare_processed_data/` | Four cleaned CSV files plus `data_quality_report.csv` |
| `eda_outputs/` | 18 summary/frequency CSV files and 14 PNG charts |
| `feature_engineered_data/` | Four analysis-ready CSV tables |
| `sql_outputs/` | `healthcare.db` plus one CSV per successful SQL query |

---

## Configuration

Configuration is hard-coded at the top of each script:

| File | Settings |
|---|---|
| `generate_data.py` | `SEED = 42`, `OUTPUT_DIR = "healthcare_raw_data"`, record counts (974 / 27,891 / 47,701 / 10), injected-defect percentages |
| `clean_data.py` | `RAW_DIR`, `PROCESSED_DIR`, validation ranges for length of stay, charges, costs, and coverage |
| `analysis/eda.py` | `BASE_DIR`, `DATA_DIR`, `OUTPUT_DIR = BASE_DIR / "eda_outputs"`, plot sizes and filenames |
| `analysis/feature_engineering.py` | `BASE_DIR`, `DATA_DIR`, `OUTPUT_DIR = BASE_DIR / "feature_engineered_data"`, category bin definitions |
| `analysis/sql_analysis.py` | `DB_PATH = OUTPUT_DIR / "healthcare.db"`, required input files, 15 SQL query strings |

There are no environment variables, config files, or CLI flags.

---

## Data Quality Report

`healthcare_processed_data/data_quality_report.csv` records record counts, column counts, missing values, and duplicate rows before and after cleaning:

| Dataset | Stage | Records | Columns | Missing values | Duplicate rows |
|---|---|---:|---:|---:|---:|
| patients | before_cleaning | 974 | 8 | 96 | 0 |
| patients | after_cleaning | 970 | 10 | 159 | 0 |
| payers | before_cleaning | 10 | 5 | 0 | 0 |
| payers | after_cleaning | 10 | 6 | 0 | 0 |
| encounters | before_cleaning | 27,891 | 13 | 3,896 | 0 |
| encounters | after_cleaning | 27,809 | 19 | 62,285 | 0 |
| procedures | before_cleaning | 47,701 | 8 | 4,767 | 0 |
| procedures | after_cleaning | 47,558 | 12 | 56,274 | 0 |

The high post-cleaning missing counts are largely caused by invalid values being nulled during validation and by the ID-normalization issue described below.

---

## Known Limitations

The pipeline runs end-to-end, but the currently committed outputs reflect a few data issues worth noting before using the results for reporting:

- **Foreign-key normalization mismatch.** `clean_data.py` title-cases `patient_id` and `payer_id` in encounters, and `encounter_id` in procedures, while the parent tables retain uppercase IDs (e.g. `PAT00001`, `PAY001`, `ENC000001`). As a result, most of these foreign keys are treated as invalid and nulled during cleaning. This makes `patient_summary.csv`, patient visit frequency, readmission analysis, and payer analysis empty or incomplete. Later stages uppercase IDs, but the values are already missing.
- **Column-name mismatches.** Some scripts reference columns that the generator does not create: `patient_payment` (actual: `patient_responsibility`), `insurance_covered` (actual: `amount_covered`), `total_cost` (actual: `total_procedure_cost`), `unit_cost` (actual: `procedure_cost`), `admission_date` (actual: `encounter_date`), and `procedure_code` / `procedure_description` (not present). Queries 10, 11, 12, and 14 fail for this reason; `sql_analysis.py` catches and prints these errors, so no CSV is produced for them.
- **No dependency manifest or automated tests.** Dependencies must be installed manually, and correctness is verified by inspecting console output and exported CSVs.
- **Category nulling.** Invalid/admission-type values can be nulled during cleaning, which produces a blank department row in `09_average_length_of_stay.csv`.
- **No dashboard artifact.** Although the docstring mentions Power BI development, no `.pbix`, notebook, or web dashboard is included.

---

## Future Work

- Fix the ID normalization so patient, payer, and encounter foreign keys survive cleaning
- Align column names across generation, feature engineering, and SQL queries
- Add `requirements.txt` and a small test suite
- Add a Power BI or Python dashboard consuming `healthcare.db`
- Externalize configuration into a config file or CLI arguments

---

## Repository

- Remote: `https://github.com/ankitsingh221/hospital_analysis.git`
- Branch: `main`
- Generated outputs are already committed, so the analysis stages can be inspected without regenerating the data.
