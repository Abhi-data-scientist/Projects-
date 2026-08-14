"""Only the ML models used by this project."""

from sklearn.ensemble import (
    AdaBoostClassifier,
    AdaBoostRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.naive_bayes import GaussianNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

try:
    from xgboost import XGBClassifier, XGBRegressor
except ImportError:
    XGBClassifier = XGBRegressor = None

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
except ImportError:
    LGBMClassifier = LGBMRegressor = None

try:
    from catboost import CatBoostClassifier, CatBoostRegressor
except ImportError:
    CatBoostClassifier = CatBoostRegressor = None


def get_models(task_type: str, random_state: int = 42) -> dict:
    """Return only the requested installed models for classification or regression."""
    if task_type == "regression":
        models = {
            "Linear Regression": LinearRegression(),
            "Ridge": Ridge(),
            "Lasso": Lasso(),
            "ElasticNet": ElasticNet(),
            "Decision Tree Regressor": DecisionTreeRegressor(random_state=random_state),
            "Random Forest Regressor": RandomForestRegressor(n_estimators=200, random_state=random_state),
            "KNN Regressor": KNeighborsRegressor(),
            "SVR": SVR(),
            "AdaBoost": AdaBoostRegressor(random_state=random_state),
            "Gradient Boosting": GradientBoostingRegressor(random_state=random_state),
        }
        if XGBRegressor:
            models["XGBoost"] = XGBRegressor(random_state=random_state, n_estimators=200)
        if LGBMRegressor:
            models["LightGBM"] = LGBMRegressor(random_state=random_state, n_estimators=200, verbosity=-1)
        if CatBoostRegressor:
            models["CatBoost"] = CatBoostRegressor(random_state=random_state, verbose=False)
        return models

    if task_type == "classification":
        models = {
            "Logistic Regression": LogisticRegression(max_iter=2000),
            "Decision Tree Classifier": DecisionTreeClassifier(random_state=random_state),
            "Random Forest Classifier": RandomForestClassifier(n_estimators=200, random_state=random_state),
            "KNN Classifier": KNeighborsClassifier(),
            "SVM (SVC)": SVC(),
            "Gaussian Naive Bayes": GaussianNB(),
            "Multinomial Naive Bayes": MultinomialNB(),
            "AdaBoost": AdaBoostClassifier(random_state=random_state),
            "Gradient Boosting": GradientBoostingClassifier(random_state=random_state),
        }
        if XGBClassifier:
            models["XGBoost"] = XGBClassifier(random_state=random_state, n_estimators=200)
        if LGBMClassifier:
            models["LightGBM"] = LGBMClassifier(random_state=random_state, n_estimators=200, verbosity=-1)
        if CatBoostClassifier:
            models["CatBoost"] = CatBoostClassifier(random_state=random_state, verbose=False)
        return models

    raise ValueError("task_type must be 'classification' or 'regression'.")
