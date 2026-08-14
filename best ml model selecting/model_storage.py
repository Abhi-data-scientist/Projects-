"""Save and load the complete trained pipeline for FastAPI."""

from pathlib import Path
import joblib


def save_model(model, file_path: str = "best_model.joblib") -> str:
    """Save preprocessing + PCA + model together."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return str(path)


def load_model(file_path: str = "best_model.joblib"):
    """Load pipeline; call loaded_model.predict(input_dataframe) in FastAPI."""
    return joblib.load(file_path)
