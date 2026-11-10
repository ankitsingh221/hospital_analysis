
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "healthcare_processed_data"
OUTPUT_DIR = BASE_DIR / "eda_outputs"
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


def save_summary(df, name):
    df.describe(include="all").transpose().to_csv(
        OUTPUT_DIR / f"{name}_summary.csv"
    )


def save_frequency(df, column, name):
    if column in df.columns:
        df[column].value_counts(dropna=False).to_csv(
            OUTPUT_DIR / f"{name}.csv"
        )


def plot_bar(series, title, xlabel, ylabel, filename):
    series = series.dropna()

    if series.empty:
        print(f"Skipping {title}: no data available.")
        return

    plt.figure(figsize=(12, 6))
    series.plot(kind="bar")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename)
    plt.close()


def plot_hist(series, title, xlabel, filename):
    series = pd.to_numeric(series, errors="coerce").dropna()

    if series.empty:
        print(f"Skipping {title}: no data available.")
        return

    plt.figure(figsize=(10, 6))
    plt.hist(series, bins=30)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename)
    plt.close()


def plot_box(series, title, ylabel, filename):
    series = pd.to_numeric(series, errors="coerce").dropna()

    if series.empty:
        print(f"Skipping {title}: no data available.")
        return

    plt.figure(figsize=(9, 5))
    plt.boxplot(series)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename)
    plt.close()


def plot_if_exists(df, column, title, xlabel, ylabel, filename):
    if column in df.columns:
        values = df[column].value_counts().head(15)
        plot_bar(values, title, xlabel, ylabel, filename)


def numeric_if_exists(df, column):
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce")
    return pd.Series(dtype="float64")


def parse_dates(df, columns):
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")


parse_dates(
    patients,
    ["date_of_birth", "registration_date"]
)

parse_dates(
    encounters,
    ["encounter_date", "admission_date", "discharge_date"]
)

parse_dates(
    procedures,
    ["procedure_date"]
)


print("\nPATIENT DATASET EDA")

save_summary(patients, "patients")

for column in [
    "gender", "race", "ethnicity", "city", "state"
]:
    save_frequency(patients, column, f"patients_{column}")

plot_if_exists(
    patients, "gender",
    "Patient Gender Distribution",
    "Gender", "Number of Patients",
    "patient_gender.png"
)

plot_if_exists(
    patients, "city",
    "Patients by City",
    "City", "Number of Patients",
    "patient_city.png"
)

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

    plot_hist(
        patients["age"],
        "Patient Age Distribution",
        "Age",
        "patient_age.png"
    )


print("\nENCOUNTER DATASET EDA")

save_summary(encounters, "encounters")

for column in [
    "admission_type",
    "department",
    "diagnosis",
    "discharge_status",
    "discharge_disposition",
    "claim_status"
]:
    save_frequency(encounters, column, f"encounters_{column}")

for column, title, filename in [
    ("admission_type", "Admission Type Distribution", "admission_type.png"),
    ("department", "Encounters by Department", "department_encounters.png"),
    ("diagnosis", "Top Diagnoses", "top_diagnoses.png"),
    ("discharge_status", "Discharge Status", "discharge_status.png"),
    ("discharge_disposition", "Discharge Disposition", "discharge_disposition.png")
]:
    plot_if_exists(
        encounters, column, title,
        column.replace("_", " ").title(),
        "Number of Encounters",
        filename
    )

for column, title, xlabel, filename in [
    ("hospital_charges", "Hospital Charges Distribution", "Hospital Charges", "hospital_charges.png"),
    ("length_of_stay", "Length of Stay Distribution", "Length of Stay", "length_of_stay.png")
]:
    if column in encounters.columns:
        plot_hist(
            numeric_if_exists(encounters, column),
            title, xlabel, filename
        )

if "hospital_charges" in encounters.columns:
    plot_box(
        encounters["hospital_charges"],
        "Hospital Charges Outlier Analysis",
        "Hospital Charges",
        "hospital_charges_boxplot.png"
    )

if "encounter_date" in encounters.columns:
    monthly = (
        encounters.dropna(subset=["encounter_date"])
        .set_index("encounter_date")
        .resample("ME")
        .size()
    )

    if not monthly.empty:
        monthly.to_csv(OUTPUT_DIR / "monthly_encounters.csv")

        plt.figure(figsize=(12, 6))
        monthly.plot()
        plt.title("Monthly Hospital Encounters")
        plt.xlabel("Month")
        plt.ylabel("Number of Encounters")
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "monthly_encounters.png")
        plt.close()

if {"department", "hospital_charges"}.issubset(encounters.columns):
    department_cost = (
        encounters.groupby("department")["hospital_charges"]
        .mean()
        .sort_values(ascending=False)
    )

    department_cost.to_csv(OUTPUT_DIR / "department_average_cost.csv")

    plot_bar(
        department_cost,
        "Average Hospital Charges by Department",
        "Department",
        "Average Charges",
        "department_average_cost.png"
    )


print("\nPROCEDURE DATASET EDA")

save_summary(procedures, "procedures")

for column in [
    "procedure_code",
    "procedure_description",
    "procedure_category"
]:
    save_frequency(procedures, column, f"procedures_{column}")

for column in ["procedure_description", "procedure_code", "procedure_category"]:
    if column in procedures.columns:
        top_procedures = procedures[column].value_counts().head(15)

        plot_bar(
            top_procedures,
            f"Top Procedures by {column.replace('_', ' ').title()}",
            column.replace("_", " ").title(),
            "Number of Procedures",
            f"top_{column}.png"
        )

for column in ["total_cost", "unit_cost", "quantity"]:
    if column in procedures.columns:
        plot_hist(
            procedures[column],
            f"{column.replace('_', ' ').title()} Distribution",
            column.replace("_", " ").title(),
            f"{column}_distribution.png"
        )


print("\nPAYER DATASET EDA")

save_summary(payers, "payers")

for column in ["payer_name", "payer_type", "contract_status"]:
    save_frequency(payers, column, f"payers_{column}")

if {"payer_id", "payer_id"}.issubset(encounters.columns) and "payer_id" in payers.columns:

    if "payer_id" in encounters.columns:
        payer_analysis = (
            encounters.groupby("payer_id", dropna=True)
            .agg(total_encounters=("encounter_id", "count"))
            .reset_index()
        )

        if "hospital_charges" in encounters.columns:
            payer_cost = (
                encounters.groupby("payer_id")["hospital_charges"]
                .sum()
                .reset_index(name="total_hospital_charges")
            )

            payer_analysis = payer_analysis.merge(
                payer_cost, on="payer_id", how="left"
            )

        if "payer_name" in payers.columns:
            payer_analysis = payer_analysis.merge(
                payers[["payer_id", "payer_name"]].drop_duplicates("payer_id"),
                on="payer_id",
                how="left"
            )
        else:
            payer_analysis["payer_name"] = payer_analysis["payer_id"]

        payer_analysis["payer_name"] = (
            payer_analysis["payer_name"]
            .fillna(payer_analysis["payer_id"])
        )

        payer_analysis.to_csv(
            OUTPUT_DIR / "payer_analysis.csv",
            index=False
        )

        if not payer_analysis.empty:
            plot_bar(
                payer_analysis.set_index("payer_name")["total_encounters"],
                "Encounters by Payer",
                "Payer",
                "Number of Encounters",
                "payer_encounters.png"
            )

            if "total_hospital_charges" in payer_analysis.columns:
                plot_bar(
                    payer_analysis.set_index("payer_name")["total_hospital_charges"],
                    "Hospital Charges by Payer",
                    "Payer",
                    "Total Hospital Charges",
                    "payer_charges.png"
                )
        else:
            print("No payer records matched with encounters.")

print("\nEDA COMPLETED SUCCESSFULLY")
print(f"Output folder: {OUTPUT_DIR}")
