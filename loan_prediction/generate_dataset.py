"""Create a synthetic dataset for this demo project.

The values are simulated for learning purposes only. They must not be used
to make real lending decisions.
"""

import numpy as np
import pandas as pd


RNG = np.random.default_rng(42)
ROWS = 2_000


def choose(values, probabilities):
    return RNG.choice(values, size=ROWS, p=probabilities)


gender = choose(["Male", "Female"], [0.58, 0.42])
married = choose(["Yes", "No"], [0.62, 0.38])
dependents = choose(["0", "1", "2", "3+"], [0.48, 0.22, 0.20, 0.10])
education = choose(["Graduate", "Not Graduate"], [0.72, 0.28])
self_employed = choose(["No", "Yes"], [0.84, 0.16])
property_area = choose(["Rural", "Semiurban", "Urban"], [0.30, 0.38, 0.32])

# Incomes and loan amounts are positive, skewed values similar to real-world
# financial data. Co-applicant income is more likely in married applications.
applicant_income = np.clip(RNG.lognormal(8.55, 0.48, ROWS), 1_500, 25_000).round().astype(int)
coapplicant_income = np.where(
    married == "Yes",
    RNG.gamma(2.1, 780, ROWS),
    RNG.gamma(1.1, 390, ROWS),
).round().astype(int)
coapplicant_income[RNG.random(ROWS) < 0.28] = 0
loan_amount_term = choose([120, 180, 240, 300, 360], [0.05, 0.10, 0.16, 0.14, 0.55]).astype(int)
total_income = applicant_income + coapplicant_income
loan_amount = np.clip(
    total_income * RNG.uniform(0.012, 0.035, ROWS) + RNG.normal(15, 20, ROWS),
    45,
    450,
).round().astype(int)

# Credit history is important, but never an automatic approval/rejection.
credit_history = RNG.binomial(1, 0.79, ROWS)
income_per_month = total_income / 1_000
loan_pressure = loan_amount / np.maximum(income_per_month * 12, 1)
area_bonus = np.select(
    [property_area == "Semiurban", property_area == "Urban"], [0.25, 0.10], default=0.0
)
education_bonus = np.where(education == "Graduate", 0.12, 0.0)

score = (
    +0.20
    + 1.30 * credit_history
    + 0.16 * income_per_month
    - 1.10 * loan_pressure
    + area_bonus
    + education_bonus
    + RNG.normal(0, 0.72, ROWS)
)
approval_probability = 1 / (1 + np.exp(-score))
loan_status = np.where(RNG.random(ROWS) < approval_probability, "Y", "N")

dataset = pd.DataFrame(
    {
        "Loan_ID": [f"LP{100000 + index:06d}" for index in range(ROWS)],
        "Gender": gender,
        "Married": married,
        "Dependents": dependents,
        "Education": education,
        "Self_Employed": self_employed,
        "ApplicantIncome": applicant_income,
        "CoapplicantIncome": coapplicant_income,
        "LoanAmount": loan_amount,
        "Loan_Amount_Term": loan_amount_term,
        "Credit_History": credit_history,
        "Property_Area": property_area,
        "Loan_Status": loan_status,
    }
)

dataset.to_csv("loan_dataset.csv", index=False)
print(f"Created {len(dataset)} rows. Approval rate: {(dataset['Loan_Status'] == 'Y').mean():.1%}")
