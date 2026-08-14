"""Train models, optionally use PCA, and select the best model."""

import pandas as pd
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler

from data_processing import build_preprocessor
from ml_models import get_models
from model_evaluation import evaluate_model


def create_pipeline(features, model, model_name: str, use_pca: bool = False, pca_components=0.95):
    """Create one complete pipeline. MultinomialNB needs non-negative features."""
    preprocessor = build_preprocessor(features, use_minmax_scaler=model_name == "Multinomial Naive Bayes")
    steps = [("preprocessing", preprocessor)]
    if use_pca:
        steps.append(("pca", PCA(n_components=pca_components, random_state=42)))
        # PCA can produce negative values; MultinomialNB accepts only non-negative input.
        if model_name == "Multinomial Naive Bayes":
            steps.append(("post_pca_scaling", MinMaxScaler()))
    steps.append(("model", model))
    return Pipeline(steps)


def train_and_select_best_model(x_train, x_test, y_train, y_test, task_type: str, use_pca: bool = False):
    """Train all requested models and return best_pipeline, leaderboard."""
    results, best_pipeline, best_score = [], None, float("-inf")
    for name, model in get_models(task_type).items():
        try:
            pipeline = create_pipeline(x_train, model, name, use_pca)
            pipeline.fit(x_train, y_train)
            metrics = evaluate_model(pipeline, x_test, y_test, task_type)
            results.append({"model": name, **metrics})
            if metrics["score"] > best_score:
                best_pipeline, best_score = pipeline, metrics["score"]
        except Exception as error:
            # A model can be incompatible with a very small or unusual data set.
            results.append({"model": name, "score": float("nan"), "error": str(error)})
    leaderboard = pd.DataFrame(results).sort_values("score", ascending=False).reset_index(drop=True)
    if best_pipeline is None:
        raise RuntimeError("No model could be trained. Check your data and target column.")
    return best_pipeline, leaderboard
