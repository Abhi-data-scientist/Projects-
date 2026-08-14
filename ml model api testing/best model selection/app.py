import os
import joblib
import seaborn as sns
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from sklearn.linear_model import (
    LinearRegression,
    Ridge,
    Lasso,
    ElasticNet
)

from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# =========================================================
# 1. CREATE MODELS FOLDER
# =========================================================

os.makedirs("models", exist_ok=True)


# =========================================================
# 2. LOAD DATASET
# =========================================================

df = sns.load_dataset("tips")

print("Dataset:")
print(df.head())

print("\nShape:")
print(df.shape)

print("\nMissing Values:")
print(df.isnull().sum())


# =========================================================
# 3. DEFINE FEATURES AND TARGET
# =========================================================

X = df.drop("tip", axis=1)
y = df["tip"]


# =========================================================
# 4. ENCODE CATEGORICAL COLUMNS
# =========================================================

categorical_columns = [
    "sex",
    "smoker",
    "day",
    "time"
]

encoders = {}

for column in categorical_columns:

    encoder = LabelEncoder()

    X[column] = encoder.fit_transform(X[column])

    encoders[column] = encoder

    # Save individual encoder
    joblib.dump(
        encoder,
        f"models/{column}_encoder.pkl"
    )


print("\nEncoded Data:")
print(X.head())


# =========================================================
# 5. TRAIN TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# =========================================================
# 6. FEATURE SCALING
# =========================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)

X_test_scaled = scaler.transform(X_test)


# Save scaler
joblib.dump(
    scaler,
    "models/scaler.pkl"
)


# =========================================================
# 7. CREATE MODELS
# =========================================================

models = {

    "Linear Regression": LinearRegression(),

    "Ridge": Ridge(),

    "Lasso": Lasso(),

    "ElasticNet": ElasticNet(),

    "Decision Tree": DecisionTreeRegressor(
        random_state=42
    ),

    "Random Forest": RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

}


# =========================================================
# 8. TRAIN AND EVALUATE MODELS
# =========================================================

results = []

trained_models = {}


for name, model in models.items():

    model.fit(
        X_train_scaled,
        y_train
    )

    y_pred = model.predict(
        X_test_scaled
    )

    mae = mean_absolute_error(
        y_test,
        y_pred
    )

    mse = mean_squared_error(
        y_test,
        y_pred
    )

    rmse = mse ** 0.5

    r2 = r2_score(
        y_test,
        y_pred
    )


    results.append({

        "Model": name,

        "MAE": mae,

        "MSE": mse,

        "RMSE": rmse,

        "R2 Score": r2

    })


    trained_models[name] = model


# =========================================================
# 9. SHOW MODEL COMPARISON
# =========================================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="R2 Score",
    ascending=False
)

print("\nModel Comparison:")
print(results_df)


# =========================================================
# 10. SELECT BEST MODEL
# =========================================================

best_model_name = results_df.iloc[0]["Model"]

best_model = trained_models[
    best_model_name
]


print(
    f"\nBest Model: {best_model_name}"
)


# =========================================================
# 11. SAVE BEST MODEL
# =========================================================

joblib.dump(
    best_model,
    "models/model.pkl"
)


print("\nFiles saved successfully!")