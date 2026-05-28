import numpy as np 
import pandas as pd 

df = pd.read_csv('loan_dataset.csv')
df.drop(columns=['Loan_ID'], inplace=True)

df['Dependents'] = df['Dependents'].replace('3+', 3)

from sklearn.impute import SimpleImputer
si = SimpleImputer(strategy='mean')
df[['LoanAmount', 'Loan_Amount_Term', 'Credit_History']] = si.fit_transform(
    df[['LoanAmount', 'Loan_Amount_Term', 'Credit_History']]
    )

si_categorical = SimpleImputer(strategy='most_frequent')
df[['Dependents']] = si_categorical.fit_transform(df[['Dependents']])
df[['Dependents']] = df[['Dependents']].astype(int)

from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
df['Gender'] = le.fit_transform(df['Gender'])
df['Married'] = le.fit_transform(df['Married'])
df['Education'] = le.fit_transform(df['Education'])
df['Self_Employed'] = le.fit_transform(df['Self_Employed'])
df['Property_Area'] = le.fit_transform(df['Property_Area'])
df['Loan_Status'] = le.fit_transform(df['Loan_Status'])


from sklearn.model_selection import train_test_split
x = df.drop('Loan_Status', axis=1)
y = df['Loan_Status']
x_train, x_test, y_train, y_test = train_test_split(
    x,
    y,
    test_size=0.2,     
    random_state=42,  
    stratify=y       
)

from imblearn.over_sampling import SMOTENC
smotenc = SMOTENC(
    categorical_features=[0,1,2,3,4,9,10], 
    random_state=42
)
x_train_resampled, y_train_resampled = smotenc.fit_resample(x_train, y_train) 

from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
x_train_scaled = scaler.fit_transform(x_train_resampled)
x_test_scaled = scaler.transform(x_test)

from sklearn.linear_model import LogisticRegression
lr = LogisticRegression(
    class_weight='balanced',
    random_state=42)
lr.fit(x_train_scaled,y_train_resampled)
y_pred = lr.predict(x_test_scaled)
from sklearn.metrics import accuracy_score
print(accuracy_score(y_test, y_pred))

import joblib
joblib.dump(lr, 'lr_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
print("Model saved")
