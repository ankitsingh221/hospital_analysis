
import os
import numpy as np
import pandas as pd
from pathlib import Path

RAW_DIR = Path("healthcare_raw_data")
PROCESSED_DIR = Path("healthcare_processed_data")

PROCESSED_DIR.mkdir(exist_ok=True)

patients = pd.read_csv(RAW_DIR / "patients.csv")
encounters = pd.read_csv(RAW_DIR / "encounters.csv")
procedures = pd.read_csv(RAW_DIR / "procedures.csv")
payers = pd.read_csv(RAW_DIR / "payers.csv")

quality_report = []


def record_quality(dataset_name, stage, df):
    quality_report.append({
        "dataset": dataset_name,
        "stage": stage,
        "total_records": len(df),
        "total_columns": len(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum())
    })


def clean_text(df, columns):
    for col in columns:
        df[col] = (
            df[col]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
            .str.title()
        )

        df[col] = df[col].replace("", pd.NA)

    return df


def clean_dates(df, columns):
    for col in columns:
        df[col] = pd.to_datetime(
            df[col],
            errors="coerce"
        )

    return df


def clean_numeric(df, columns):
    for col in columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    return df


def remove_duplicate_ids(df, column):
    df = df.drop_duplicates(
        subset=[column],
        keep="first"
    )

    return df.reset_index(drop=True)


def clean_patients(df):

    print("\nCleaning patients dataset...")

    record_quality("patients", "before_cleaning", df)

    df = df.copy()

    df = remove_duplicate_ids(
        df,
        "patient_id"
    )

    df = clean_text(
        df,
        [
            "gender",
            "city",
            "state",
            "blood_group",
            "smoking_status"
        ]
    )

    df = clean_dates(
        df,
        [
            "date_of_birth",
            "registration_date"
        ]
    )

    df["gender"] = df["gender"].replace({
        "M": "Male",
        "F": "Female",
        "Man": "Male",
        "Woman": "Female"
    })

    valid_genders = ["Male", "Female"]

    df.loc[
        ~df["gender"].isin(valid_genders)
        & df["gender"].notna(),
        "gender"
    ] = pd.NA

    valid_blood_groups = [
        "A+", "A-", "B+", "B-",
        "Ab+", "Ab-", "O+", "O-"
    ]

    df.loc[
        ~df["blood_group"].isin(valid_blood_groups)
        & df["blood_group"].notna(),
        "blood_group"
    ] = pd.NA

    today = pd.Timestamp.today().normalize()

    df.loc[
        df["date_of_birth"] > today,
        "date_of_birth"
    ] = pd.NaT

    df.loc[
        df["registration_date"] > today,
        "registration_date"
    ] = pd.NaT

    df.loc[
        df["registration_date"] < pd.Timestamp("1900-01-01"),
        "registration_date"
    ] = pd.NaT

    df["age"] = (
        today.year
        - df["date_of_birth"].dt.year
        - (
            (
                today.month < df["date_of_birth"].dt.month
            )
            |
            (
                (
                    today.month == df["date_of_birth"].dt.month
                )
                &
                (
                    today.day < df["date_of_birth"].dt.day
                )
            )
        )
    )

    df.loc[
        (df["age"] < 0) | (df["age"] > 120),
        "age"
    ] = np.nan

    df["age_group"] = pd.cut(
        df["age"],
        bins=[0, 18, 35, 50, 65, 120],
        labels=[
            "0-18",
            "19-35",
            "36-50",
            "51-65",
            "65+"
        ],
        include_lowest=True
    )

    record_quality("patients", "after_cleaning", df)

    return df


def clean_payers(df):

    print("\nCleaning payers dataset...")

    record_quality("payers", "before_cleaning", df)

    df = df.copy()

    df = remove_duplicate_ids(
        df,
        "payer_id"
    )

    df = clean_text(
        df,
        [
            "payer_name",
            "payer_type",
            "network_type"
        ]
    )

    df = clean_numeric(
        df,
        ["coverage_rate"]
    )

    df.loc[
        ~df["coverage_rate"].between(0, 1),
        "coverage_rate"
    ] = np.nan

    df["coverage_percentage"] = (
        df["coverage_rate"] * 100
    ).round(2)

    df = df.drop_duplicates(
        subset=["payer_name"],
        keep="first"
    )

    record_quality("payers", "after_cleaning", df)

    return df


def clean_encounters(df, patients_df, payers_df):

    print("\nCleaning encounters dataset...")

    record_quality("encounters", "before_cleaning", df)

    df = df.copy()

    df = remove_duplicate_ids(
        df,
        "encounter_id"
    )

    df = clean_text(
        df,
        [
            "admission_type",
            "department",
            "diagnosis",
            "discharge_status",
            "patient_id",
            "payer_id"
        ]
    )

    df = clean_dates(
        df,
        [
            "encounter_date",
            "discharge_date"
        ]
    )

    df = clean_numeric(
        df,
        [
            "length_of_stay",
            "hospital_charges",
            "amount_covered",
            "patient_responsibility"
        ]
    )

    df.loc[
        df["length_of_stay"] < 0,
        "length_of_stay"
    ] = np.nan

    df.loc[
        df["length_of_stay"] > 365,
        "length_of_stay"
    ] = np.nan

    df.loc[
        (df["hospital_charges"] < 0)
        | (df["hospital_charges"] > 100000),
        "hospital_charges"
    ] = np.nan

    df.loc[
        df["amount_covered"] < 0,
        "amount_covered"
    ] = np.nan

    df.loc[
        df["patient_responsibility"] < 0,
        "patient_responsibility"
    ] = np.nan

    invalid_discharge = (
        df["discharge_date"].notna()
        & df["encounter_date"].notna()
        & (
            df["discharge_date"]
            < df["encounter_date"]
        )
    )

    df.loc[
        invalid_discharge,
        "discharge_date"
    ] = pd.NaT

    valid_patient_ids = set(
        patients_df["patient_id"].dropna()
    )

    valid_payer_ids = set(
        payers_df["payer_id"].dropna()
    )

    df.loc[
        ~df["patient_id"].isin(valid_patient_ids),
        "patient_id"
    ] = pd.NA

    df.loc[
        ~df["payer_id"].isin(valid_payer_ids),
        "payer_id"
    ] = pd.NA

    df.loc[
        df["hospital_charges"].isna(),
        [
            "amount_covered",
            "patient_responsibility"
        ]
    ] = np.nan

    df["encounter_month"] = (
        df["encounter_date"].dt.month
    )

    df["encounter_year"] = (
        df["encounter_date"].dt.year
    )

    df["encounter_month_name"] = (
        df["encounter_date"].dt.month_name()
    )

    df["actual_length_of_stay"] = (
        df["discharge_date"] - df["encounter_date"]
    ).dt.days

    df.loc[
        df["actual_length_of_stay"] < 0,
        "actual_length_of_stay"
    ] = np.nan

    df["length_of_stay_category"] = pd.cut(
        df["length_of_stay"],
        bins=[-1, 0, 3, 7, 14, 365],
        labels=[
            "Same Day",
            "1-3 Days",
            "4-7 Days",
            "8-14 Days",
            "15+ Days"
        ]
    )

    df["insurance_coverage_percentage"] = np.where(
        df["hospital_charges"] > 0,
        (
            df["amount_covered"]
            / df["hospital_charges"]
        ) * 100,
        np.nan
    )

    record_quality("encounters", "after_cleaning", df)

    return df


def clean_procedures(df, encounters_df):

    print("\nCleaning procedures dataset...")

    record_quality("procedures", "before_cleaning", df)

    df = df.copy()

    df = remove_duplicate_ids(
        df,
        "procedure_id"
    )

    df = clean_text(
        df,
        [
            "encounter_id",
            "procedure_name",
            "procedure_category",
            "performed_by"
        ]
    )

    df = clean_dates(
        df,
        ["procedure_date"]
    )

    df = clean_numeric(
        df,
        [
            "procedure_cost",
            "quantity"
        ]
    )

    df.loc[
        (df["procedure_cost"] < 0)
        | (df["procedure_cost"] > 20000),
        "procedure_cost"
    ] = np.nan

    df.loc[
        (df["quantity"] <= 0)
        | (df["quantity"] > 100),
        "quantity"
    ] = np.nan

    valid_encounter_ids = set(
        encounters_df["encounter_id"].dropna()
    )

    df.loc[
        ~df["encounter_id"].isin(valid_encounter_ids),
        "encounter_id"
    ] = pd.NA

    df["total_procedure_cost"] = (
        df["procedure_cost"] * df["quantity"]
    )

    df["procedure_year"] = (
        df["procedure_date"].dt.year
    )

    df["procedure_month"] = (
        df["procedure_date"].dt.month
    )

    df["procedure_month_name"] = (
        df["procedure_date"].dt.month_name()
    )

    record_quality("procedures", "after_cleaning", df)

    return df


# ============================================================
# 2. EXECUTE CLEANING
# ============================================================

patients_clean = clean_patients(patients)

payers_clean = clean_payers(payers)

encounters_clean = clean_encounters(
    encounters,
    patients_clean,
    payers_clean
)

procedures_clean = clean_procedures(
    procedures,
    encounters_clean
)


# ============================================================
# 3. GENERATE PROCESSED DATASETS
# ============================================================

patients_clean.to_csv(
    PROCESSED_DIR / "patients_cleaned.csv",
    index=False
)

encounters_clean.to_csv(
    PROCESSED_DIR / "encounters_cleaned.csv",
    index=False
)

procedures_clean.to_csv(
    PROCESSED_DIR / "procedures_cleaned.csv",
    index=False
)

payers_clean.to_csv(
    PROCESSED_DIR / "payers_cleaned.csv",
    index=False
)



# 4. GENERATE DATA QUALITY REPORT


quality_df = pd.DataFrame(quality_report)

quality_df.to_csv(
    PROCESSED_DIR / "data_quality_report.csv",
    index=False
)



# 5. GENERATE FINAL SUMMARY


print("\n" + "=" * 60)
print("DATA CLEANING COMPLETED SUCCESSFULLY")
print("=" * 60)

print("\nFINAL DATASET SHAPES")

print("Patients:", patients_clean.shape)
print("Encounters:", encounters_clean.shape)
print("Procedures:", procedures_clean.shape)
print("Payers:", payers_clean.shape)

print("\nFINAL MISSING VALUES")

for name, df in {
    "Patients": patients_clean,
    "Encounters": encounters_clean,
    "Procedures": procedures_clean,
    "Payers": payers_clean
}.items():

    print(
        f"{name}: {df.isnull().sum().sum():,}"
    )

print("\nPROCESSED FILES")

for file in sorted(PROCESSED_DIR.iterdir()):
    if file.is_file():
        print(file.name)

print("\nAll cleaned datasets saved in:")
print(PROCESSED_DIR.resolve())

print("\nNEXT STEP: EDA AND DATA ANALYSIS")
