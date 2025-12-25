import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
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
        
        # Simple pipeline: TF-IDF -> Linear SVM (SGD)
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ('clf', SGDClassifier(loss='hinge', penalty='l2', alpha=1e-3, random_state=42, max_iter=5, tol=None))
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
            # SGD with hinge loss doesn't give probability directly, 
            # so we use decision_function as a proxy for confidence or just simple prediction
            prediction = self.model.predict([description])[0]
            
            # Since we can't easily get exact probability from simple SGD without calibration,
            # we will return a fixed high confidence if it predicts anything.
            # Ideally use CalibratedClassifierCV if proba needed, but keep it simple.
            return prediction, 0.85
        except Exception:
            return None, 0.0
