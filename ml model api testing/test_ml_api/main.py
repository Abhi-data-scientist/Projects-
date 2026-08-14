from flask import Flask, request, jsonify
import joblib
import pandas as pd


app = Flask(__name__)


model = joblib.load("best_model.pkl")
sex_encoder = joblib.load("le_sex.pkl")
smoker_encoder = joblib.load("le_smoker.pkl")
time_encoder = joblib.load("le_time.pkl")


@app.route("/predict", methods=["POST"])
def predict():

    try:
        data = request.get_json()

        total_bill = float(data["total_bill"])
        tip = float(data["tip"])
        sex = data["sex"]
        time = data["time"]
        size = int(data["size"])




        sex_encoded = sex_encoder.transform([sex])[0]
        time_encoded = time_encoder.transform([time])[0]



        input_data = pd.DataFrame([{
            "total_bill": total_bill,
            "tip": tip,
            "sex": sex_encoded,
            "time": time_encoded,
            "size": size
        }])

        prediction = model.predict(input_data)[0]
        predicted_smoker = smoker_encoder.inverse_transform([prediction])[0]


        return jsonify({
            "predicted_smoker": predicted_smoker
        })


    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 400

if __name__ == "__main__":
    app.run(debug=True)
