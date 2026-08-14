from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import joblib
import numpy as np
import os
 
app = Flask(__name__, static_folder='.')
CORS(app)
 
# ── Load model ────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.pkl')
 
try:
    model = joblib.load(MODEL_PATH)
    print(f"✓ Model loaded from {MODEL_PATH}")
except FileNotFoundError:
    model = None
    print(f"✗ model.pkl not found at {MODEL_PATH}. Place it in the same folder.")
 
 
# ── Serve HTML pages ───────────────────────────────────────────────────────────
@app.route('/')
def index():
    """Serve the loan application form."""
    return send_from_directory('.', 'loan_prediction_form.html')
 
 
@app.route('/result')
def result():
    """Serve the result page."""
    return send_from_directory('.', 'loan_result.html')
 
 
# ── Prediction endpoint ────────────────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    """
    Accepts JSON body:
        { "input": [gender, married, education, self_employed,
                    applicantIncome, coapplicantIncome, loanAmount,
                    loanAmountTerm, creditHistory, propertyArea] }
 
    Returns:
        { "prediction": 0 | 1 }   (1 = Approved, 0 = Rejected)
    """
    if model is None:
        return jsonify({'error': 'Model not loaded. Ensure model.pkl exists.'}), 500
 
    try:
        body = request.get_json(force=True)
 
        if not body or 'input' not in body:
            return jsonify({'error': "Request body must contain an 'input' key."}), 400
 
        raw = body['input']
 
        if len(raw) != 10:
            return jsonify({
                'error': f"Expected 10 features, got {len(raw)}. "
                         f"Order: gender, married, education, self_employed, "
                         f"applicantIncome, coapplicantIncome, loanAmount, "
                         f"loanAmountTerm, creditHistory, propertyArea"
            }), 400
 
        features = np.array(raw, dtype=float).reshape(1, -1)
        prediction = int(model.predict(features)[0])
 
        # Optional: probability scores if model supports it
        response = {'prediction': prediction}
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(features)[0]
            response['probability'] = {
                'rejected': round(float(proba[0]), 4),
                'approved': round(float(proba[1]), 4),
            }
 
        return jsonify(response)
 
    except ValueError as e:
        return jsonify({'error': f'Invalid input values: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500
 
 
# ── Health check ───────────────────────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'model_loaded': model is not None,
    })
 
 
# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n  Loan Prediction API")
    print("  ───────────────────────────────────")
    print("  Form   →  http://127.0.0.1:5000/")
    print("  Result →  http://127.0.0.1:5000/result")
    print("  API    →  POST http://127.0.0.1:5000/predict")
    print("  Health →  http://127.0.0.1:5000/health\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
 