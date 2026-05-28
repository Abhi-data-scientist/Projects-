from flask import Flask, render_template, request
import numpy as np
import joblib

# -----------------------------------
# Load Trained Model & Scaler
# -----------------------------------

model = joblib.load('lr_model.pkl')
scaler = joblib.load('scaler.pkl')

# -----------------------------------
# Initialize Flask App
# -----------------------------------

app = Flask(__name__)

# -----------------------------------
# Home Route
# -----------------------------------

@app.route('/')
def home():
    return render_template('index.html')

# -----------------------------------
# Prediction Route
# -----------------------------------

@app.route('/predict', methods=['POST'])
def predict():

    # Get all form values
    features = [x for x in request.form.values()]

    # Handle Dependents
    if features[2] == '3+':
        features[2] = 3

    # Convert all values to float
    final_features = np.array([[float(x) for x in features]])

    # Scale Input
    final_features_scaled = scaler.transform(final_features)

    # Prediction
    prediction = model.predict(final_features_scaled)

    # Result
    if prediction[0] == 1:
        result = "✅ Loan Approved"
    else:
        result = "❌ Loan Rejected"

    return render_template(
        'index.html',
        result=result
    )

# -----------------------------------
# Run Flask App
# -----------------------------------

if __name__ == '__main__':
    app.run(debug=True)