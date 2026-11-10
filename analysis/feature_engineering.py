
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "healthcare_processed_data"
OUTPUT_DIR = BASE_DIR / "feature_engineered_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

patients = pd.read_csv(DATA_DIR / "patients_cleaned.csv")
encounters = pd.read_csv(DATA_DIR / "encounters_cleaned.csv")
procedures = pd.read_csv(DATA_DIR / "procedures_cleaned.csv")
payers = pd.read_csv(DATA_DIR / "payers_cleaned.csv")


def standardize_id(df, column):
    if column in df.columns:
        df[column] = df[column].astype("string").str.strip().str.upper()


for df, columns in [
    (patients, ["patient_id"]),
    (encounters, ["patient_id", "encounter_id", "payer_id"]),
    (procedures, ["encounter_id"]),
    (payers, ["payer_id"])
]:
    for column in columns:
        standardize_id(df, column)


def parse_date(df, column):
    if column in df.columns:
        df[column] = pd.to_datetime(df[column], errors="coerce")


for column in ["date_of_birth", "registration_date"]:
    parse_date(patients, column)

for column in ["encounter_date", "admission_date", "discharge_date"]:
    parse_date(encounters, column)

parse_date(procedures, "procedure_date")


def numeric_column(df, column):
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")


for column in ["hospital_charges", "patient_payment", "insurance_covered", "length_of_stay"]:
    numeric_column(encounters, column)

for column in ["quantity", "unit_cost", "total_cost"]:
    numeric_column(procedures, column)


if "date_of_birth" in patients.columns:
    today = pd.Timestamp.today().normalize()

    patients["age"] = (
        today.year
        - patients["date_of_birth"].dt.year
        - (
            (today.month < patients["date_of_birth"].dt.month)
            | (
                (today.month == patients["date_of_birth"].dt.month)
                & (today.day < patients["date_of_birth"].dt.day)
            )
        )
    )

    patients.loc[
        (patients["age"] < 0) | (patients["age"] > 120),
        "age"
    ] = np.nan

    patients["age_group"] = pd.cut(
        patients["age"],
        bins=[0, 18, 35, 50, 65, 120],
        labels=[
            "0-18",
            "19-35",
            "36-50",
            "51-65",
            "Above 65"
        ],
        include_lowest=True
    )


if "encounter_date" in encounters.columns:
    encounters["encounter_year"] = encounters["encounter_date"].dt.year
    encounters["encounter_month"] = encounters["encounter_date"].dt.month
    encounters["encounter_quarter"] = (
        encounters["encounter_date"].dt.to_period("Q").astype("string")
    )
    encounters["year_month"] = (
        encounters["encounter_date"].dt.to_period("M").astype("string")
    )


if {"admission_date", "discharge_date"}.issubset(encounters.columns):
    encounters["actual_length_of_stay"] = (
        encounters["discharge_date"] - encounters["admission_date"]
    ).dt.total_seconds() / 86400

    encounters.loc[
        encounters["actual_length_of_stay"] < 0,
        "actual_length_of_stay"
    ] = np.nan

elif "length_of_stay" in encounters.columns:
    encounters["actual_length_of_stay"] = encounters["length_of_stay"]


if {"hospital_charges", "actual_length_of_stay"}.issubset(encounters.columns):
    encounters["cost_per_hospital_day"] = np.where(
        encounters["actual_length_of_stay"] > 0,
        encounters["hospital_charges"] / encounters["actual_length_of_stay"],
        np.nan
    )


if {"hospital_charges", "patient_payment"}.issubset(encounters.columns):
    encounters["patient_payment_percentage"] = np.where(
        encounters["hospital_charges"] > 0,
        encounters["patient_payment"] / encounters["hospital_charges"] * 100,
        np.nan
    )


if {"hospital_charges", "insurance_covered"}.issubset(encounters.columns):
    encounters["insurance_coverage_percentage"] = np.where(
        encounters["hospital_charges"] > 0,
        encounters["insurance_covered"] / encounters["hospital_charges"] * 100,
        np.nan
    )


if {"patient_id", "encounter_date", "discharge_date"}.issubset(encounters.columns):

    encounters = encounters.sort_values(
        ["patient_id", "encounter_date"]
    ).reset_index(drop=True)

    encounters["previous_discharge_date"] = (
        encounters.groupby("patient_id")["discharge_date"].shift(1)
    )

    encounters["days_since_previous_discharge"] = (
        encounters["encounter_date"] - encounters["previous_discharge_date"]
    ).dt.total_seconds() / 86400

    encounters["readmission_30_days"] = np.where(
        encounters["previous_discharge_date"].notna()
        & encounters["days_since_previous_discharge"].between(0, 30),
        1,
        0
    )

    encounters.loc[
        encounters["patient_id"].isna()
        | encounters["encounter_date"].isna()
        | encounters["previous_discharge_date"].isna(),
        "readmission_30_days"
    ] = np.nan


if "encounter_id" in procedures.columns:

    procedure_aggregation = {}

    if "procedure_id" in procedures.columns:
        procedure_aggregation["procedure_id"] = "count"

    if "quantity" in procedures.columns:
        procedure_aggregation["quantity"] = "sum"

    if "total_cost" in procedures.columns:
        procedure_aggregation["total_cost"] = ["sum", "mean", "max"]

    if "unit_cost" in procedures.columns:
        procedure_aggregation["unit_cost"] = "mean"

    if procedure_aggregation:
        procedure_summary = (
            procedures.groupby("encounter_id")
            .agg(procedure_aggregation)
        )

        procedure_summary.columns = [
            "_".join(str(part) for part in col if part)
            if isinstance(col, tuple) else str(col)
            for col in procedure_summary.columns
        ]

        procedure_summary = procedure_summary.reset_index()

        rename_columns = {
            "procedure_id_count": "procedure_count",
            "quantity_sum": "total_procedure_quantity",
            "total_cost_sum": "total_procedure_cost",
            "total_cost_mean": "average_procedure_cost",
            "total_cost_max": "highest_procedure_cost",
            "unit_cost_mean": "average_unit_cost"
        }

        procedure_summary = procedure_summary.rename(
            columns=rename_columns
        )

        encounters = encounters.merge(
            procedure_summary,
            on="encounter_id",
            how="left"
        )

        encounters.to_csv(
            OUTPUT_DIR / "encounter_procedure_summary.csv",
            index=False
        )

        for column in [
            "procedure_count",
            "total_procedure_quantity",
            "total_procedure_cost",
            "average_procedure_cost",
            "highest_procedure_cost",
            "average_unit_cost"
        ]:
            if column in encounters.columns:
                encounters[column] = encounters[column].fillna(0)


if "hospital_charges" in encounters.columns:
    encounters["cost_category"] = pd.cut(
        encounters["hospital_charges"],
        bins=[-np.inf, 1000, 5000, 10000, np.inf],
        labels=["Low", "Medium", "High", "Very High"]
    )


if {"hospital_charges", "total_procedure_cost"}.issubset(encounters.columns):
    encounters["procedure_to_hospital_cost_ratio"] = np.where(
        encounters["hospital_charges"] > 0,
        encounters["total_procedure_cost"] / encounters["hospital_charges"],
        np.nan
    )


patient_columns = [
    column for column in [
        "patient_id",
        "gender",
        "race",
        "ethnicity",
        "city",
        "state",
        "age",
        "age_group"
    ]
    if column in patients.columns
]

if "patient_id" in patients.columns and "patient_id" in encounters.columns:
    patient_encounters = encounters.merge(
        patients[patient_columns].drop_duplicates("patient_id"),
        on="patient_id",
        how="left",
        validate="many_to_one",
        suffixes=("", "_patient")
    )
else:
    patient_encounters = encounters.copy()


payer_columns = [
    column for column in [
        "payer_id",
        "payer_name",
        "payer_type",
        "average_coverage_pct",
        "contract_status"
    ]
    if column in payers.columns
]

if "payer_id" in payers.columns and "payer_id" in patient_encounters.columns:
    patient_encounters = patient_encounters.merge(
        payers[payer_columns].drop_duplicates("payer_id"),
        on="payer_id",
        how="left",
        validate="many_to_one",
        suffixes=("", "_payer")
    )


patient_encounters.to_csv(
    OUTPUT_DIR / "encounters_feature_engineered.csv",
    index=False
)


if "patient_id" in patient_encounters.columns:

    aggregations = {}

    if "encounter_id" in patient_encounters.columns:
        aggregations["encounter_id"] = "count"

    if "hospital_charges" in patient_encounters.columns:
        aggregations["hospital_charges"] = ["sum", "mean"]

    if "total_procedure_cost" in patient_encounters.columns:
        aggregations["total_procedure_cost"] = "sum"

    if "actual_length_of_stay" in patient_encounters.columns:
        aggregations["actual_length_of_stay"] = "mean"

    if "readmission_30_days" in patient_encounters.columns:
        aggregations["readmission_30_days"] = "sum"

    if "encounter_date" in patient_encounters.columns:
        aggregations["encounter_date"] = ["min", "max"]

    if aggregations:
        patient_summary = (
            patient_encounters.groupby("patient_id")
            .agg(aggregations)
        )

        patient_summary.columns = [
            "_".join(str(part) for part in col if part)
            if isinstance(col, tuple) else str(col)
            for col in patient_summary.columns
        ]

        patient_summary = patient_summary.reset_index()

        patient_summary = patient_summary.rename(
            columns={
                "encounter_id_count": "total_encounters",
                "hospital_charges_sum": "total_hospital_charges",
                "hospital_charges_mean": "average_hospital_charges",
                "total_procedure_cost_sum": "total_procedure_cost",
                "actual_length_of_stay_mean": "average_length_of_stay",
                "readmission_30_days_sum": "total_readmissions",
                "encounter_date_min": "first_encounter_date",
                "encounter_date_max": "last_encounter_date"
            }
        )

        if "total_encounters" in patient_summary.columns:
            patient_summary["visit_category"] = pd.cut(
                patient_summary["total_encounters"],
                bins=[0, 1, 3, 5, np.inf],
                labels=[
                    "One-time Patient",
                    "Occasional Patient",
                    "Regular Patient",
                    "Frequent Patient"
                ]
            )

        patient_summary.to_csv(
            OUTPUT_DIR / "patient_summary.csv",
            index=False
        )


patients.to_csv(
    OUTPUT_DIR / "patients_feature_engineered.csv",
    index=False
)

print("\nFEATURE ENGINEERING COMPLETED SUCCESSFULLY")
print(f"Output folder: {OUTPUT_DIR}")
