"""Cleaning, features, splitting and preprocessing functions."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler


def clean_data(data: pd.DataFrame, target: str) -> pd.DataFrame:
    """Remove duplicates and rows where the target value is missing."""
    return data.drop_duplicates().dropna(subset=[target]).reset_index(drop=True)


def add_date_features(data: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Convert one date column into year, month and day features."""
    result = data.copy()
    date = pd.to_datetime(result[date_column], errors="coerce")
    result[f"{date_column}_year"] = date.dt.year
    result[f"{date_column}_month"] = date.dt.month
    result[f"{date_column}_day"] = date.dt.day
    return result.drop(columns=[date_column])


def detect_task_type(target: pd.Series) -> str:
    """Simple automatic task detection; pass task_type manually if this is wrong."""
    if target.dtype == "object" or target.dtype.name == "category":
        return "classification"
    return "classification" if target.nunique() <= 20 else "regression"


def split_data(data: pd.DataFrame, target: str, task_type: str, test_size: float = 0.2):
    """Return X_train, X_test, y_train and y_test."""
    x, y = data.drop(columns=[target]), data[target]
    stratify = y if task_type == "classification" and y.value_counts().min() >= 2 else None
    return train_test_split(x, y, test_size=test_size, random_state=42, stratify=stratify)


def build_preprocessor(features: pd.DataFrame, use_minmax_scaler: bool = False) -> ColumnTransformer:
    """Fill missing values, scale numerical columns and encode categorical columns."""
    numeric_columns = features.select_dtypes(include=np.number).columns.tolist()
    categorical_columns = [column for column in features.columns if column not in numeric_columns]
    scaler = MinMaxScaler() if use_minmax_scaler else StandardScaler()
    numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", scaler)])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("numeric", numeric_pipe, numeric_columns),
        ("categorical", categorical_pipe, categorical_columns),
    ])
