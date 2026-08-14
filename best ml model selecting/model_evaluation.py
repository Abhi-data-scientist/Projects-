"""Model evaluation functions."""

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, r2_score


def evaluate_model(model, x_test, y_test, task_type: str) -> dict:
    """Return simple evaluation metrics. score is used to choose the best model."""
    predictions = model.predict(x_test)
    if task_type == "classification":
        return {
            "score": accuracy_score(y_test, predictions),
            "accuracy": accuracy_score(y_test, predictions),
            "f1_score": f1_score(y_test, predictions, average="weighted", zero_division=0),
        }
    return {
        "score": r2_score(y_test, predictions),
        "r2_score": r2_score(y_test, predictions),
        "mae": mean_absolute_error(y_test, predictions),
        "rmse": np.sqrt(mean_squared_error(y_test, predictions)),
    }
