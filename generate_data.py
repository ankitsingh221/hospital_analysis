
"""
Healthcare Operations & Patient Analytics Dashboard
----------------------------------------------------

Synthetic Hospital Data Generator

Generates:
1. patients.csv       - 974 patient records
2. encounters.csv     - 27,891 encounter records
3. procedures.csv     - 47,701 procedure records
4. payers.csv         - 10 payer organizations

Purpose:
Practice:
- Data Cleaning
- Data Validation
- Exploratory Data Analysis
- Feature Engineering
- SQL Analysis
- Power BI Dashboard Development

All records are synthetic.
"""

import os
import numpy as np
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

SEED = 42

rng = np.random.default_rng(SEED)

OUTPUT_DIR = "healthcare_raw_data"

NUM_PATIENTS = 974
NUM_ENCOUNTERS = 27891
NUM_PROCEDURES = 47701
NUM_PAYERS = 10

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def inject_missing(df, columns, percentage=0.02):
    """Introduce missing values into selected columns."""

    for col in columns:

        count = int(len(df) * percentage)

        if count > 0:

            indices = rng.choice(
                df.index,
                size=count,
                replace=False
            )

            df.loc[indices, col] = np.nan

    return df


def inject_duplicate_ids(df, column, percentage=0.005):
    """Introduce duplicate primary key values."""

    count = max(1, int(len(df) * percentage))

    source_indices = rng.choice(
        df.index,
        size=count,
        replace=False
    )

    target_indices = rng.choice(
        df.index,
        size=count,
        replace=False
    )

    df.loc[target_indices, column] = (
        df.loc[source_indices, column].values
    )

    return df


def inject_inconsistent_text(df, column):
    """Introduce inconsistent capitalization and whitespace."""

    if column not in df.columns:
        return df

    mask = (
        df[column].notna()
        & (rng.random(len(df)) < 0.06)
    )

    for idx in df.index[mask]:

        value = str(df.loc[idx, column])

        variation = rng.choice([
            value.upper(),
            value.lower(),
            " " + value,
            value + " ",
            " " + value.upper() + " "
        ])

        df.loc[idx, column] = variation

    return df


def save_dataset(df, filename):
    """Save generated dataset as CSV."""

    path = os.path.join(OUTPUT_DIR, filename)

    df.to_csv(path, index=False)

    print(
        f"Generated: {path} | "
        f"Rows: {len(df):,} | "
        f"Columns: {len(df.columns)}"
    )


def print_quality_summary(name, df, id_column):
    """Print basic data quality information."""

    print("\n" + "=" * 55)
    print(name.upper(), "DATA QUALITY SUMMARY")
    print("=" * 55)

    print("Total records:", len(df))
    print("Total columns:", len(df.columns))

    print(
        "Total missing values:",
        df.isnull().sum().sum()
    )

    print(
        "Duplicate IDs:",
        df[id_column].duplicated().sum()
    )

    print("\nMissing values by column:")

    print(
        df.isnull().sum()[
            df.isnull().sum() > 0
        ]
    )


# ============================================================
# 3. PAYERS DATASET
# ============================================================

print("\nGenerating payer dataset...")

payer_names = [
    "BlueCross Health",
    "United Healthcare",
    "Aetna Insurance",
    "Cigna Healthcare",
    "Medicare",
    "Medicaid",
    "Humana",
    "Kaiser Permanente",
    "Molina Healthcare",
    "Anthem Insurance"
]

payers = pd.DataFrame({

    "payer_id": [
        f"PAY{i:03d}"
        for i in range(1, NUM_PAYERS + 1)
    ],

    "payer_name": payer_names,

    "payer_type": [
        "Private",
        "Private",
        "Private",
        "Private",
        "Government",
        "Government",
        "Private",
        "Private",
        "Government",
        "Private"
    ],

    "coverage_rate": [
        0.82, 0.85, 0.78, 0.80, 0.90,
        0.95, 0.83, 0.88, 0.91, 0.79
    ],

    "network_type": [
        "PPO", "HMO", "PPO", "PPO", "Public",
        "Public", "HMO", "HMO", "Public", "PPO"
    ]

})

payers = inject_inconsistent_text(
    payers,
    "payer_type"
)

save_dataset(payers, "payers.csv")


# ============================================================
# 4. PATIENTS DATASET
# ============================================================

print("\nGenerating patient dataset...")

patient_ids = [
    f"PAT{i:05d}"
    for i in range(1, NUM_PATIENTS + 1)
]

genders = rng.choice(
    ["Male", "Female"],
    size=NUM_PATIENTS,
    p=[0.49, 0.51]
)

dob_start = pd.Timestamp("1935-01-01")
dob_end = pd.Timestamp("2005-12-31")

dob_days = (dob_end - dob_start).days

dates_of_birth = (
    dob_start
    + pd.to_timedelta(
        rng.integers(
            0,
            dob_days,
            NUM_PATIENTS
        ),
        unit="D"
    )
)

cities = [
    "New York",
    "Chicago",
    "Los Angeles",
    "Houston",
    "Phoenix",
    "Dallas",
    "San Diego",
    "Seattle",
    "Boston",
    "Miami"
]

states = [
    "NY", "IL", "CA", "TX", "AZ",
    "TX", "CA", "WA", "MA", "FL"
]

city_indices = rng.integers(
    0,
    len(cities),
    NUM_PATIENTS
)

patients = pd.DataFrame({

    "patient_id": patient_ids,

    "gender": genders,

    "date_of_birth": dates_of_birth,

    "city": [
        cities[i]
        for i in city_indices
    ],

    "state": [
        states[i]
        for i in city_indices
    ],

    "blood_group": rng.choice(
        [
            "A+", "A-", "B+", "B-",
            "AB+", "AB-", "O+", "O-"
        ],
        NUM_PATIENTS
    ),

    "registration_date": pd.to_datetime(
        rng.choice(
            pd.date_range(
                "2020-01-01",
                "2025-12-31"
            ),
            NUM_PATIENTS
        )
    ),

    "smoking_status": rng.choice(
        [
            "Never",
            "Former",
            "Current",
            "Unknown"
        ],
        NUM_PATIENTS,
        p=[0.55, 0.20, 0.15, 0.10]
    )

})

# Missing values
patients = inject_missing(
    patients,
    [
        "gender",
        "date_of_birth",
        "city",
        "blood_group"
    ],
    0.025
)

# Inconsistent text
patients = inject_inconsistent_text(
    patients,
    "gender"
)

patients = inject_inconsistent_text(
    patients,
    "city"
)

# Duplicate patient IDs
patients = inject_duplicate_ids(
    patients,
    "patient_id",
    0.005
)

# Invalid future dates of birth
future_indices = rng.choice(
    patients.index,
    size=5,
    replace=False
)

patients.loc[
    future_indices,
    "date_of_birth"
] = pd.Timestamp("2030-01-01")

save_dataset(patients, "patients.csv")


# ============================================================
# 5. ENCOUNTERS DATASET
# ============================================================

print("\nGenerating encounter dataset...")

encounter_ids = [
    f"ENC{i:06d}"
    for i in range(1, NUM_ENCOUNTERS + 1)
]

# Multiple encounters can belong to one patient
encounter_patient_ids = rng.choice(
    patient_ids,
    size=NUM_ENCOUNTERS,
    replace=True
)

encounter_dates = pd.to_datetime(
    rng.choice(
        pd.date_range(
            "2022-01-01",
            "2025-12-31"
        ),
        NUM_ENCOUNTERS
    )
)

admission_types = rng.choice(
    [
        "Emergency",
        "Inpatient",
        "Outpatient",
        "Elective"
    ],
    NUM_ENCOUNTERS,
    p=[0.22, 0.25, 0.38, 0.15]
)

departments = rng.choice(
    [
        "Cardiology",
        "Orthopedics",
        "Neurology",
        "Emergency",
        "General Medicine",
        "Oncology",
        "Pediatrics",
        "Surgery",
        "Radiology",
        "ICU"
    ],
    NUM_ENCOUNTERS
)

diagnoses = rng.choice(
    [
        "Hypertension",
        "Diabetes",
        "Heart Disease",
        "Pneumonia",
        "Fracture",
        "Cancer",
        "Asthma",
        "Kidney Disease",
        "Stroke",
        "Infection"
    ],
    NUM_ENCOUNTERS
)


# ------------------------------------------------------------
# Length of stay based on admission type
# ------------------------------------------------------------

los = []

for admission in admission_types:

    if admission == "Emergency":

        days = rng.choice(
            [0, 1, 2, 3, 4, 5],
            p=[0.25, 0.30, 0.20, 0.12, 0.08, 0.05]
        )

    elif admission == "Inpatient":

        days = rng.integers(1, 16)

    elif admission == "Elective":

        days = rng.integers(1, 8)

    else:

        days = 0

    los.append(days)

los = np.array(los)

discharge_dates = (
    encounter_dates
    + pd.to_timedelta(los, unit="D")
)


# ------------------------------------------------------------
# Discharge status
# ------------------------------------------------------------

discharge_status = rng.choice(
    [
        "Home",
        "Transferred",
        "Rehabilitation",
        "Expired",
        "Against Medical Advice"
    ],
    NUM_ENCOUNTERS,
    p=[0.76, 0.08, 0.08, 0.03, 0.05]
)


# ------------------------------------------------------------
# Payer assignments
# ------------------------------------------------------------

payer_assignments = rng.choice(
    payers["payer_id"].values,
    NUM_ENCOUNTERS
)

coverage_map = dict(
    zip(
        payers["payer_id"],
        payers["coverage_rate"]
    )
)

coverage = np.array([
    coverage_map[p]
    for p in payer_assignments
])


# ------------------------------------------------------------
# Hospital charges
# ------------------------------------------------------------

base_cost = np.select(
    [
        admission_types == "Emergency",
        admission_types == "Inpatient",
        admission_types == "Outpatient",
        admission_types == "Elective"
    ],
    [
        1800,
        4500,
        650,
        3000
    ]
)

hospital_charges = (
    base_cost
    + los * rng.uniform(
        400,
        1200,
        NUM_ENCOUNTERS
    )
    + rng.normal(
        0,
        600,
        NUM_ENCOUNTERS
    )
)

hospital_charges = np.maximum(
    hospital_charges,
    100
).round(2)


# ------------------------------------------------------------
# Insurance coverage
# ------------------------------------------------------------

amount_covered = (
    hospital_charges
    * coverage
    * rng.uniform(
        0.85,
        1.0,
        NUM_ENCOUNTERS
    )
).round(2)

patient_responsibility = (
    hospital_charges - amount_covered
).round(2)


# ------------------------------------------------------------
# Create encounters dataframe
# ------------------------------------------------------------

encounters = pd.DataFrame({

    "encounter_id": encounter_ids,

    "patient_id": encounter_patient_ids,

    "encounter_date": encounter_dates,

    "discharge_date": discharge_dates,

    "admission_type": admission_types,

    "department": departments,

    "diagnosis": diagnoses,

    "length_of_stay": los,

    "discharge_status": discharge_status,

    "payer_id": payer_assignments,

    "hospital_charges": hospital_charges,

    "amount_covered": amount_covered,

    "patient_responsibility": patient_responsibility

})


# ------------------------------------------------------------
# Introduce missing values
# ------------------------------------------------------------

encounters = inject_missing(
    encounters,
    [
        "admission_type",
        "department",
        "diagnosis",
        "discharge_status",
        "payer_id",
        "hospital_charges"
    ],
    0.02
)


# ------------------------------------------------------------
# Inconsistent categories
# ------------------------------------------------------------

encounters = inject_inconsistent_text(
    encounters,
    "admission_type"
)

encounters = inject_inconsistent_text(
    encounters,
    "department"
)

encounters = inject_inconsistent_text(
    encounters,
    "discharge_status"
)


# ------------------------------------------------------------
# Duplicate encounter IDs
# ------------------------------------------------------------

encounters = inject_duplicate_ids(
    encounters,
    "encounter_id",
    0.003
)


# ------------------------------------------------------------
# Invalid financial values
# ------------------------------------------------------------

bad_cost_indices = rng.choice(
    encounters.index,
    size=35,
    replace=False
)

encounters.loc[
    bad_cost_indices[:20],
    "hospital_charges"
] = -500

encounters.loc[
    bad_cost_indices[20:],
    "hospital_charges"
] = 999999


# ------------------------------------------------------------
# Invalid length of stay
# ------------------------------------------------------------

bad_los_indices = rng.choice(
    encounters.index,
    size=25,
    replace=False
)

encounters.loc[
    bad_los_indices,
    "length_of_stay"
] = -2


# ------------------------------------------------------------
# Missing and malformed dates
# IMPORTANT: Convert to object before inserting strings.
# This prevents the Pandas datetime assignment error.
# ------------------------------------------------------------

encounters = inject_missing(
    encounters,
    [
        "encounter_date",
        "discharge_date"
    ],
    0.01
)

malformed_date_indices = rng.choice(
    encounters.index,
    size=30,
    replace=False
)

encounters["encounter_date"] = (
    encounters["encounter_date"].astype("object")
)

encounters["discharge_date"] = (
    encounters["discharge_date"].astype("object")
)

for idx in malformed_date_indices[:15]:

    encounters.loc[
        idx,
        "encounter_date"
    ] = "invalid_date"

for idx in malformed_date_indices[15:]:

    encounters.loc[
        idx,
        "discharge_date"
    ] = "not_available"


# ------------------------------------------------------------
# Invalid foreign keys
# ------------------------------------------------------------

bad_fk_indices = rng.choice(
    encounters.index,
    size=10,
    replace=False
)

encounters.loc[
    bad_fk_indices[:5],
    "patient_id"
] = "PAT99999"

encounters.loc[
    bad_fk_indices[5:],
    "payer_id"
] = "PAY999"


save_dataset(encounters, "encounters.csv")


# ============================================================
# 6. PROCEDURES DATASET
# ============================================================

print("\nGenerating procedure dataset...")

procedure_ids = [
    f"PRC{i:07d}"
    for i in range(1, NUM_PROCEDURES + 1)
]


# ------------------------------------------------------------
# Distribute exactly 47,701 procedures across encounters
# ------------------------------------------------------------

procedure_counts = rng.poisson(
    NUM_PROCEDURES / NUM_ENCOUNTERS,
    NUM_ENCOUNTERS
)

difference = (
    NUM_PROCEDURES - procedure_counts.sum()
)

while difference != 0:

    if difference > 0:

        idx = rng.integers(
            0,
            NUM_ENCOUNTERS
        )

        procedure_counts[idx] += 1

        difference -= 1

    else:

        valid_indices = np.where(
            procedure_counts > 0
        )[0]

        idx = rng.choice(valid_indices)

        procedure_counts[idx] -= 1

        difference += 1


procedure_encounter_ids = np.repeat(
    encounter_ids,
    procedure_counts
)

rng.shuffle(procedure_encounter_ids)


# ------------------------------------------------------------
# Procedure catalog
# ------------------------------------------------------------

procedure_catalog = {

    "Blood Test": (50, 150),

    "X-Ray": (100, 300),

    "MRI Scan": (500, 1500),

    "CT Scan": (400, 1200),

    "ECG": (100, 250),

    "Ultrasound": (200, 600),

    "Surgery": (2500, 10000),

    "Chemotherapy": (1500, 6000),

    "Physical Therapy": (100, 400),

    "Biopsy": (500, 2000),

    "Endoscopy": (800, 2500),

    "Vaccination": (30, 200)

}

procedure_names = list(
    procedure_catalog.keys()
)

selected_procedures = rng.choice(
    procedure_names,
    NUM_PROCEDURES
)


# ------------------------------------------------------------
# Generate procedure costs
# ------------------------------------------------------------

procedure_costs = []

for procedure in selected_procedures:

    low, high = procedure_catalog[procedure]

    cost = rng.uniform(low, high)

    procedure_costs.append(
        round(cost, 2)
    )


# ------------------------------------------------------------
# Create procedures dataframe
# ------------------------------------------------------------

procedures = pd.DataFrame({

    "procedure_id": procedure_ids,

    "encounter_id": procedure_encounter_ids,

    "procedure_name": selected_procedures,

    "procedure_category": rng.choice(
        [
            "Diagnostic",
            "Imaging",
            "Laboratory",
            "Surgical",
            "Therapeutic"
        ],
        NUM_PROCEDURES
    ),

    "procedure_date": pd.to_datetime(
        rng.choice(
            pd.date_range(
                "2022-01-01",
                "2025-12-31"
            ),
            NUM_PROCEDURES
        )
    ),

    "procedure_cost": procedure_costs,

    "quantity": rng.choice(
        [1, 2, 3, 4],
        NUM_PROCEDURES,
        p=[0.75, 0.17, 0.06, 0.02]
    ),

    "performed_by": rng.choice(
        [
            "Doctor",
            "Nurse",
            "Technician",
            "Specialist"
        ],
        NUM_PROCEDURES
    )

})


# ------------------------------------------------------------
# Missing values
# ------------------------------------------------------------

procedures = inject_missing(
    procedures,
    [
        "procedure_name",
        "procedure_category",
        "procedure_date",
        "procedure_cost",
        "performed_by"
    ],
    0.02
)


# ------------------------------------------------------------
# Inconsistent text
# ------------------------------------------------------------

procedures = inject_inconsistent_text(
    procedures,
    "procedure_name"
)

procedures = inject_inconsistent_text(
    procedures,
    "procedure_category"
)


# ------------------------------------------------------------
# Duplicate procedure IDs
# ------------------------------------------------------------

procedures = inject_duplicate_ids(
    procedures,
    "procedure_id",
    0.003
)


# ------------------------------------------------------------
# Invalid procedure costs
# ------------------------------------------------------------

bad_indices = rng.choice(
    procedures.index,
    size=60,
    replace=False
)

procedures.loc[
    bad_indices[:30],
    "procedure_cost"
] = -100

procedures.loc[
    bad_indices[30:],
    "procedure_cost"
] = 50000


# ------------------------------------------------------------
# Invalid quantity
# ------------------------------------------------------------

invalid_quantity_indices = rng.choice(
    procedures.index,
    size=20,
    replace=False
)

procedures.loc[
    invalid_quantity_indices,
    "quantity"
] = -1


# ------------------------------------------------------------
# Invalid encounter foreign keys
# ------------------------------------------------------------

bad_fk = rng.choice(
    procedures.index,
    size=10,
    replace=False
)

procedures.loc[
    bad_fk,
    "encounter_id"
] = "ENC999999"


# ------------------------------------------------------------
# Invalid future procedure dates
# ------------------------------------------------------------

future_indices = rng.choice(
    procedures.index,
    size=20,
    replace=False
)

procedures.loc[
    future_indices,
    "procedure_date"
] = pd.Timestamp("2035-01-01")


save_dataset(procedures, "procedures.csv")


# ============================================================
# 7. FINAL DATA QUALITY SUMMARY
# ============================================================

print("\n\n")
print("#" * 65)
print("HEALTHCARE DATA GENERATION COMPLETED SUCCESSFULLY")
print("#" * 65)

datasets = {

    "Patients": (patients, "patient_id"),

    "Encounters": (encounters, "encounter_id"),

    "Procedures": (procedures, "procedure_id"),

    "Payers": (payers, "payer_id")

}

for name, (df, id_column) in datasets.items():

    print_quality_summary(
        name,
        df,
        id_column
    )


# ============================================================
# 8. VERIFY TOTAL RECORD COUNTS
# ============================================================

print("\n" + "=" * 65)
print("RECORD COUNT VERIFICATION")
print("=" * 65)

print(
    f"Patients:   {len(patients):,} "
    f"(Expected: {NUM_PATIENTS:,})"
)

print(
    f"Encounters: {len(encounters):,} "
    f"(Expected: {NUM_ENCOUNTERS:,})"
)

print(
    f"Procedures: {len(procedures):,} "
    f"(Expected: {NUM_PROCEDURES:,})"
)

print(
    f"Payers:     {len(payers):,} "
    f"(Expected: {NUM_PAYERS:,})"
)

print("\nAll CSV files saved in:", OUTPUT_DIR)

print("\nGenerated files:")

for file in sorted(os.listdir(OUTPUT_DIR)):

    print(" -", file)

print("\nNext steps:")
print("1. Perform data quality assessment.")
print("2. Clean the raw datasets.")
print("3. Perform EDA.")
print("4. Perform feature engineering.")
print("5. Load cleaned data into SQL.")
print("6. Build Power BI dashboard.")

print("\n" + "#" * 65)
