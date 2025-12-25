import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
import pickle
import os

class TransactionClassifier:
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.min_samples = 5  # Minimum samples to trigger training
        
    def train(self, transactions):
        """
        Train parameters:
        transactions: list of dicts with 'description' and 'category' keys
        """
        if not transactions or len(transactions) < self.min_samples:
            print("⚠️ Not enough data to train AI model.")
            return False
            
        df = pd.DataFrame(transactions)
        
        # Pipeline with Calibration to get probabilities
        sgd = SGDClassifier(loss='hinge', penalty='l2', alpha=1e-3, random_state=42, max_iter=5, tol=None)
        calibrated_clf = CalibratedClassifierCV(sgd, method='sigmoid', cv='prefit') 
        # Note: cv='prefit' is WRONG if we haven't fit sgd yet. 
        # Actually CalibratedClassifierCV(cv=2) handles internal splitting.
        
        # Better approach for small data: Use SGD with 'log_loss' (Logistic Regression equivalent)
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ('clf', SGDClassifier(loss='log_loss', penalty='l2', alpha=1e-3, random_state=42, max_iter=10, tol=None))
        ])
        
        try:
            self.model.fit(df['description'], df['category'])
            self.is_trained = True
            print(f"🧠 AI Model trained on {len(df)} transactions.")
            return True
        except Exception as e:
            print(f"❌ Error training model: {e}")
            return False

    def predict(self, description):
        """
        Predict category for a description.
        Returns: (category, confidence)
        """
        if not self.is_trained or not self.model:
            return None, 0.0
            
        try:
            # Get probability
            probs = self.model.predict_proba([description])[0]
            max_prob = np.max(probs)
            prediction = self.model.classes_[np.argmax(probs)]
            
            return prediction, max_prob
        except Exception:
            return None, 0.0
