"""
Train and evaluate a baseline genre classifier.

Run from the repository root:
    python -m framework.craap.purpose.train_genre_classifier
"""

from pathlib import Path
from urllib.parse import urlparse
import re

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from framework.preprocessing.clean_text import clean_text

OUT = Path(__file__).parent
DATA_PATH = OUT / "genre_data.csv"
MODEL_PATH = OUT / "genre_classifier.joblib"
PROBABILITY_MODEL_PATH = OUT / "genre_probability_classifier.joblib"
RANDOM_STATE = 42


def main():
    data = pd.read_csv(DATA_PATH)

    required = {"text", "url", "genre"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = data.dropna(subset=["text", "url", "genre"])
    data["text"] = data["text"].apply(lambda value: clean_text(value, single_line=True))
    data["title"] = data["title"].apply(lambda value: clean_text(value, single_line=True)) if "title" in data else ""
    data["genre"] = data["genre"].astype(str).str.strip().str.lower()

    def url_features(url):
        parsed = urlparse(str(url))
        host = (parsed.hostname or "").removeprefix("www.")
        host_words = re.sub(r"[^a-z0-9]+", " ", host.lower()).strip()
        path_words = re.sub(r"[^a-z0-9]+", " ", parsed.path.lower()).strip()
        return f"urlhost {host_words} urlpath {path_words}"

    data["model_text"] = (
        data["title"].astype(str).fillna("")
        + " "
        + data["text"].astype(str)
        + " "
        + data["url"].apply(url_features)
    )
    data = data[(data["text"] != "") & (data["genre"] != "")]

    counts = data["genre"].value_counts()
    minimum_count = counts.min()
    if minimum_count < 2:
        raise ValueError("Every genre needs at least two rows for a stratified split")

    train_text, test_text, train_label, test_label = train_test_split(
        data["model_text"],
        data["genre"],
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=data["genre"],
    )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
    )

    models = {
        "logistic_regression": Pipeline([
            ("tfidf", vectorizer),
            ("classifier", LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            )),
        ]),
        "linear_svm": Pipeline([
            ("tfidf", TfidfVectorizer(
                lowercase=True,
                strip_accents="unicode",
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=2,
            )),
            ("classifier", LinearSVC(
                class_weight="balanced",
                random_state=RANDOM_STATE,
            )),
        ]),
    }

    print(f"Rows: {len(data)} | train: {len(train_text)} | test: {len(test_text)}")
    results = {}

    for model_name, classifier in models.items():
        classifier.fit(train_text, train_label)
        predictions = classifier.predict(test_text)
        accuracy = accuracy_score(test_label, predictions)
        macro_f1 = f1_score(test_label, predictions, average="macro")
        results[model_name] = (macro_f1, classifier)

        print(f"\n=== {model_name} ===")
        print(f"Accuracy: {accuracy:.3f}")
        print(f"Macro-F1: {macro_f1:.3f}")
        print("Classification report:")
        print(classification_report(test_label, predictions, digits=3, zero_division=0))

        labels = sorted(data["genre"].unique())
        print("Confusion matrix (rows=true, columns=predicted):")
        print(pd.DataFrame(
            confusion_matrix(test_label, predictions, labels=labels),
            index=labels,
            columns=labels,
        ).to_string())

    best_name = max(results, key=lambda name: results[name][0])
    best_classifier = results[best_name][1]
    joblib.dump(best_classifier, MODEL_PATH)

    probability_classifier = models["logistic_regression"]
    joblib.dump(probability_classifier, PROBABILITY_MODEL_PATH)

    print(f"\nBest model: {best_name}")
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved probability model: {PROBABILITY_MODEL_PATH}")


if __name__ == "__main__":
    main()
