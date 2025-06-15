import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from catboost import CatBoostClassifier
import os

MODEL_PATH = 'model/catboost_model.cbm'
INPUT_PATH = 'input/test_processed.csv'
OUTPUT_SUB = 'output/sample_submission.csv'
OUTPUT_FEATIMP = 'output/feature_importances.json'
OUTPUT_DENSITY = 'output/density_plot.png'

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file {MODEL_PATH} not found!")
if not os.path.exists(INPUT_PATH):
    raise FileNotFoundError(f"Preprocessed test file {INPUT_PATH} not found! Run preprocess.py first.")

model = CatBoostClassifier()
model.load_model(MODEL_PATH)

test = pd.read_csv(INPUT_PATH)
features = [c for c in test.columns if c not in ['index', 'transaction_time']]
cat_features = [c for c in features if test[c].dtype == 'object']

print("Используемые признаки:", features)
print("Категориальные признаки:", cat_features)

preds_proba = model.predict_proba(test[features])[:, 1]
preds = (preds_proba > 0.5).astype(int)

submission = pd.DataFrame({'target': preds}, index=test.index)
submission.index.name = 'index'
submission.to_csv(OUTPUT_SUB)
print(f"Saved predictions to {OUTPUT_SUB}")

importances = model.get_feature_importance(prettified=True)
importances = importances.sort_values('Importances', ascending=False).head(5)
featimp_dict = dict(zip(importances['Feature Id'], importances['Importances']))
with open(OUTPUT_FEATIMP, 'w') as f:
    json.dump(featimp_dict, f, indent=2)
print(f"Saved top-5 feature importances to {OUTPUT_FEATIMP}")

plt.figure(figsize=(8, 5))
plt.hist(preds_proba, bins=30, density=True, alpha=0.7)
plt.title('Density of predicted scores')
plt.xlabel('Predicted probability')
plt.ylabel('Density')
plt.savefig(OUTPUT_DENSITY)
print(f"Saved density plot to {OUTPUT_DENSITY}") 