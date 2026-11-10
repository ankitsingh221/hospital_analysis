
from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
FEATURE_DIR = BASE_DIR / "feature_engineered_data"
CLEAN_DIR = BASE_DIR / "healthcare_processed_data"
OUTPUT_DIR = BASE_DIR / "sql_outputs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = OUTPUT_DIR / "healthcare.db"

required_files = {
    "patients": FEATURE_DIR / "patients_feature_engineered.csv",
    "encounters": FEATURE_DIR / "encounters_feature_engineered.csv",
    "patient_summary": FEATURE_DIR / "patient_summary.csv",
    "procedures": CLEAN_DIR / "procedures_cleaned.csv",
    "payers": CLEAN_DIR / "payers_cleaned.csv"
}

missing_files = [
    str(path) for path in required_files.values()
    if not path.exists()
]

if missing_files:
    raise FileNotFoundError(
        "Required files are missing. Run feature_engineering.py first:\n"
        + "\n".join(missing_files)
    )


dataframes = {
    table: pd.read_csv(path)
    for table, path in required_files.items()
}


def standardize_id(df, column):
    if column in df.columns:
        df[column] = df[column].astype("string").str.strip().str.upper()


for table, columns in {
    "patients": ["patient_id"],
    "encounters": ["patient_id", "encounter_id", "payer_id"],
    "patient_summary": ["patient_id"],
    "procedures": ["encounter_id"],
    "payers": ["payer_id"]
}.items():
    for column in columns:
        standardize_id(dataframes[table], column)


connection = sqlite3.connect(DB_PATH)

for table, df in dataframes.items():
    df.to_sql(
        table,
        connection,
        if_exists="replace",
        index=False
    )


queries = {
    "01_department_encounters": """
        SELECT
            department,
            COUNT(*) AS total_encounters
        FROM encounters
        WHERE department IS NOT NULL
        GROUP BY department
        ORDER BY total_encounters DESC;
    """,

    "02_monthly_encounters": """
        SELECT
            year_month,
            COUNT(*) AS total_encounters
        FROM encounters
        WHERE year_month IS NOT NULL
        GROUP BY year_month
        ORDER BY year_month;
    """,

    "03_top_diagnoses": """
        SELECT
            diagnosis,
            COUNT(*) AS total_cases
        FROM encounters
        WHERE diagnosis IS NOT NULL
        GROUP BY diagnosis
        ORDER BY total_cases DESC
        LIMIT 15;
    """,

    "04_payer_analysis": """
        SELECT
            p.payer_name,
            COUNT(e.encounter_id) AS total_encounters,
            SUM(e.hospital_charges) AS total_hospital_charges,
            AVG(e.hospital_charges) AS average_hospital_charges
        FROM encounters e
        LEFT JOIN payers p
            ON e.payer_id = p.payer_id
        GROUP BY p.payer_name
        ORDER BY total_hospital_charges DESC;
    """,

    "05_department_cost": """
        SELECT
            department,
            COUNT(*) AS total_encounters,
            SUM(hospital_charges) AS total_charges,
            AVG(hospital_charges) AS average_charges
        FROM encounters
        WHERE department IS NOT NULL
        GROUP BY department
        ORDER BY total_charges DESC;
    """,

    "06_high_cost_encounters": """
        SELECT
            encounter_id,
            patient_id,
            department,
            diagnosis,
            hospital_charges
        FROM encounters
        WHERE hospital_charges IS NOT NULL
        ORDER BY hospital_charges DESC
        LIMIT 20;
    """,

    "07_patient_visit_frequency": """
        SELECT
            patient_id,
            total_encounters,
            visit_category
        FROM patient_summary
        ORDER BY total_encounters DESC
        LIMIT 20;
    """,

    "08_readmission_analysis": """
        SELECT
            department,
            COUNT(*) AS total_encounters,
            SUM(readmission_30_days) AS readmissions,
            ROUND(
                100.0 * SUM(readmission_30_days) /
                NULLIF(COUNT(readmission_30_days), 0),
                2
            ) AS readmission_percentage
        FROM encounters
        WHERE readmission_30_days IS NOT NULL
        GROUP BY department
        ORDER BY readmission_percentage DESC;
    """,

    "09_average_length_of_stay": """
        SELECT
            department,
            AVG(actual_length_of_stay) AS average_length_of_stay
        FROM encounters
        WHERE actual_length_of_stay IS NOT NULL
        GROUP BY department
        ORDER BY average_length_of_stay DESC;
    """,

    "10_top_patients_by_cost": """
        SELECT
            patient_id,
            total_hospital_charges,
            total_procedure_cost,
            total_encounters
        FROM patient_summary
        ORDER BY total_hospital_charges DESC
        LIMIT 20;
    """,

    "11_procedure_category_cost": """
        SELECT
            procedure_category,
            COUNT(*) AS procedure_count,
            SUM(total_cost) AS total_procedure_cost,
            AVG(total_cost) AS average_procedure_cost
        FROM procedures
        WHERE procedure_category IS NOT NULL
        GROUP BY procedure_category
        ORDER BY total_procedure_cost DESC;
    """,

    "12_payer_patient_responsibility": """
        SELECT
            p.payer_name,
            SUM(e.patient_payment) AS total_patient_payment,
            AVG(e.patient_payment) AS average_patient_payment
        FROM encounters e
        LEFT JOIN payers p
            ON e.payer_id = p.payer_id
        GROUP BY p.payer_name
        ORDER BY total_patient_payment DESC;
    """,

    "13_quarterly_hospital_cost": """
        SELECT
            encounter_quarter,
            SUM(hospital_charges) AS total_hospital_charges,
            AVG(hospital_charges) AS average_hospital_charges,
            COUNT(*) AS total_encounters
        FROM encounters
        WHERE encounter_quarter IS NOT NULL
        GROUP BY encounter_quarter
        ORDER BY encounter_quarter;
    """,

    "14_procedure_volume_by_encounter": """
        SELECT
            encounter_id,
            COUNT(*) AS procedure_count,
            SUM(total_cost) AS total_procedure_cost
        FROM procedures
        GROUP BY encounter_id
        ORDER BY total_procedure_cost DESC
        LIMIT 20;
    """,

    "15_patient_demographics": """
        SELECT
            gender,
            age_group,
            COUNT(DISTINCT patient_id) AS total_patients
        FROM patients
        GROUP BY gender, age_group
        ORDER BY total_patients DESC;
    """
}


for query_name, query in queries.items():

    try:
        result = pd.read_sql_query(query, connection)

        result.to_csv(
            OUTPUT_DIR / f"{query_name}.csv",
            index=False
        )

        print(f"\n{query_name}")
        print(result.head(10).to_string(index=False))

    except Exception as error:
        print(f"\nError in {query_name}: {error}")


connection.close()

print("\nSQL ANALYSIS COMPLETED")
print(f"Database: {DB_PATH}")
print(f"Results folder: {OUTPUT_DIR}")
