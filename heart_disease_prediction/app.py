from flask import Flask, render_template, request
import numpy as np
import joblib

# Load model
model = joblib.load('model.pkl')

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():

    # Get all form values together
    features = [float(x) for x in request.form.values()]

    # Convert into numpy array
    final_features = np.array([features])

    # Prediction
    prediction = model.predict(final_features)

    # Result
    if prediction[0] == 1:
        result = "🔴 High Risk of Heart Disease"
    else:
        result = "🟢 Low Risk of Heart Disease"

    return render_template(
        'index.html',
        result=result
    )


if __name__ == '__main__':
    app.run(debug=True)