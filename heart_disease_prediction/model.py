import numpy as np
import pandas as pd

# Load dataset
df = pd.read_csv('heart_disease_dataset.csv')

# Convert target into binary
df['num'] = df['num'].apply(lambda x: 1 if x > 0 else 0)

# Drop unwanted columns
df.drop(columns=['ca', 'thal'], inplace=True)

# Fill missing values
df['trestbps'] = df['trestbps'].fillna(df['trestbps'].mean())
df['chol'] = df['chol'].fillna(df['chol'].mean())
df['thalch'] = df['thalch'].fillna(df['thalch'].mean())

# Label Encoding
from sklearn.preprocessing import LabelEncoder

encoder = LabelEncoder()

cat_cols = ['sex', 'cp', 'fbs', 'restecg']

for col in cat_cols:
    df[col] = encoder.fit_transform(df[col])

# Features and target
x = df.drop(columns=['num'])
y = df['num']

# Train Test Split
from sklearn.model_selection import train_test_split

x_train, x_test, y_train, y_test = train_test_split(
    x,
    y,
    test_size=0.2,
    random_state=42
)

# Model
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

model = RandomForestClassifier()

model.fit(x_train, y_train)

# Prediction
y_pred = model.predict(x_test)

# Accuracy
accuracy = accuracy_score(y_test, y_pred)

print("Accuracy :", accuracy)

# Save Model
import joblib

joblib.dump(model, 'model.pkl')

print("Model Saved")