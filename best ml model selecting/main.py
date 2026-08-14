"""FastAPI app for uploading a dataset, training models, and making predictions.

Run locally:
    uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs to use the interactive API page.
"""

from io import BytesIO
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from data_processing import clean_data, detect_task_type, split_data
from model_storage import load_model, save_model
from model_training import train_and_select_best_model

app = FastAPI(title="ML Model Selector API", version="1.0.0")
MODEL_FOLDER = Path("saved_models")
STATIC_FOLDER = Path("static")
model_registry: dict[str, Path] = {}
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")


class PredictionRequest(BaseModel):
    """Rows must use the same feature column names as the training CSV."""

    records: list[dict[str, Any]]


@app.get("/")
def home():
    """Serve the browser frontend at the same URL as the FastAPI server."""
    return FileResponse(STATIC_FOLDER / "index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/train")
async def train_dataset(
    file: UploadFile = File(..., description="CSV dataset file"),
    target_column: str = Form(..., description="Column to predict"),
    task_type: Literal["auto", "classification", "regression"] = Form("auto"),
    use_pca: bool = Form(False, description="Use PCA after preprocessing"),
):
    """Train all suitable models and return the complete training process."""
    process = ["Received dataset file."]
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    try:
        contents = await file.read()
        data = pd.read_csv(BytesIO(contents))
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {error}") from error

    if data.empty:
        raise HTTPException(status_code=400, detail="The CSV file is empty.")
    if target_column not in data.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Target column '{target_column}' not found. Available: {data.columns.tolist()}",
        )
    process.append(f"Loaded {len(data)} rows and {len(data.columns)} columns.")

    cleaned_data = clean_data(data, target_column)
    removed_rows = len(data) - len(cleaned_data)
    process.append(f"Cleaned data: removed {removed_rows} duplicate or missing-target rows.")
    if len(cleaned_data) < 6:
        raise HTTPException(status_code=400, detail="At least 6 valid rows are needed for training.")

    selected_task = detect_task_type(cleaned_data[target_column]) if task_type == "auto" else task_type
    process.append(f"Selected task type: {selected_task}.")
    process.append("Applied missing-value filling, categorical encoding, and numeric scaling inside each model pipeline.")
    if use_pca:
        process.append("PCA enabled: components will be learned only from training data.")
    else:
        process.append("PCA disabled.")

    try:
        x_train, x_test, y_train, y_test = split_data(cleaned_data, target_column, selected_task)
        process.append(f"Split data into {len(x_train)} training rows and {len(x_test)} testing rows.")
        best_model, leaderboard = train_and_select_best_model(
            x_train, x_test, y_train, y_test, selected_task, use_pca
        )
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Training failed: {error}") from error

    best_name = leaderboard.iloc[0]["model"]
    model_id = uuid4().hex
    model_path = MODEL_FOLDER / f"{model_id}.joblib"
    save_model(best_model, model_path)
    model_registry[model_id] = model_path
    process.append(f"Trained {len(leaderboard)} models and selected {best_name}.")
    process.append("Saved the complete pipeline (preprocessing, optional PCA, and model) for prediction.")

    clean_leaderboard = leaderboard.astype(object).where(pd.notna(leaderboard), None)
    return {
        "process": process,
        "dataset": {
            "original_rows": len(data),
            "cleaned_rows": len(cleaned_data),
            "feature_columns": x_train.columns.tolist(),
            "target_column": target_column,
            "task_type": selected_task,
            "pca_used": use_pca,
        },
        "best_model": best_name,
        "model_id": model_id,
        "leaderboard": clean_leaderboard.to_dict(orient="records"),
        "next_step": f"Send feature records to POST /predict/{model_id}.",
    }


@app.post("/predict/{model_id}")
def predict(model_id: str, request: PredictionRequest):
    """Predict one or more new rows using a model produced by /train."""
    model_path = model_registry.get(model_id)
    if model_path is None or not model_path.exists():
        raise HTTPException(status_code=404, detail="Model not found. Train a dataset first.")
    if not request.records:
        raise HTTPException(status_code=400, detail="Provide at least one record.")

    try:
        model = load_model(model_path)
        predictions = model.predict(pd.DataFrame(request.records)).tolist()
        return {"model_id": model_id, "predictions": predictions}
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {error}") from error
