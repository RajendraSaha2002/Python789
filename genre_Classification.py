import os
import numpy as np
import pandas as pd
import librosa
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from imblearn.over_sampling import SMOTE
import matplotlib.pyplot as plt

# 1. Load metadata and audio files
DATASET_PATH = "genres/"  # Update with your dataset path
genres = 'blues classical country disco hiphop jazz metal pop reggae rock'.split()
data = []

# 2. Feature Extraction
def extract_features(file_path):
    y, sr = librosa.load(file_path, duration=30)
    features = []
    features.append(np.mean(librosa.feature.mfcc(y=y, sr=sr).T, axis=0))
    features.append(np.mean(librosa.feature.chroma_stft(y=y, sr=sr).T, axis=0))
    features.append(np.mean(librosa.feature.spectral_contrast(y=y, sr=sr).T, axis=0))
    return np.hstack(features)

for genre in genres:
    genre_dir = os.path.join(DATASET_PATH, genre)
    for filename in os.listdir(genre_dir):
        if filename.endswith('.wav'):
            file_path = os.path.join(genre_dir, filename)
            features = extract_features(file_path)
            data.append([features, genre])

# 3. DataFrame creation
X = np.array([row[0] for row in data])
y = np.array([row[1] for row in data])

# Encode labels
le = LabelEncoder()
y_enc = le.fit_transform(y)

# 4. Handling Imbalanced Data
smote = SMOTE()
X_resampled, y_resampled = smote.fit_resample(X, y_enc)

# 5. Train/test split & scaling
X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 6. Model training
models = {
    "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
    "SVM": SVC(kernel='rbf', probability=True)
}

for name, model in models.items():
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    print(f"--- {name} ---")
    print(classification_report(y_test, y_pred, target_names=le.classes_))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # 7. Cross-validation
    scores = cross_val_score(model, X_resampled, y_resampled, cv=5)
    print(f"CV Accuracy: {np.mean(scores):.2f} (+/- {np.std(scores):.2f})")

# 8. Feature importance plotting (for RandomForest)
feat_imp = models['RandomForest'].feature_importances_
plt.figure(figsize=(12,4))
plt.bar(range(len(feat_imp)), feat_imp)
plt.title("Random Forest Feature Importances")
plt.show()