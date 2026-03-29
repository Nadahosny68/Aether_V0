import pickle
import sklearn
from sklearn.ensemble import RandomForestClassifier

print("sklearn version:", sklearn.__version__)

clf = RandomForestClassifier(n_estimators=2)
clf.fit([[1,2],[3,4],[5,6]], ["a","b","a"])

with open("test_model.pkl", "wb") as f:
    pickle.dump(clf, f)
print("Save: OK")

with open("test_model.pkl", "rb") as f:
    loaded = pickle.load(f)
print("Load: OK")
print("Predict:", loaded.predict([[1,2]]))

model_path = r"ML\models\environmental_risk_model.pkl"
print("\nLoading real model from:", model_path)
with open(model_path, "rb") as f:
    real_model = pickle.load(f)
print("Real model loaded OK")
print("Classes:", real_model.classes_)