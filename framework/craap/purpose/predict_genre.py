"""
Apply the pretrained genre classifier to a CSV starter set.

Run from the repository root:
    python -m framework.craap.purpose.predict_genre
"""

import argparse
from pathlib import Path
from urllib.parse import urlparse
import re

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from framework.preprocessing.clean_text import clean_text

OUT = Path(__file__).parent
DEFAULT_INPUT = OUT / "genre_data.csv"
DEFAULT_MODEL = OUT / "genre_classifier.joblib"
DEFAULT_PROBABILITY_MODEL = OUT / "genre_probability_classifier.joblib"
DEFAULT_OUTPUT = OUT / "genre_predictions.csv"
NON_ACADEMIC_GENRES = {"blog", "forum", "opinion", "commercial"}


def url_features(url):
    parsed = urlparse(str(url))
    host = (parsed.hostname or "").removeprefix("www.")
    host_words = re.sub(r"[^a-z0-9]+", " ", host.lower()).strip()
    path_words = re.sub(r"[^a-z0-9]+", " ", parsed.path.lower()).strip()
    return f"urlhost {host_words} urlpath {path_words}"


def prepare_rows(data):
    required = {"text", "url"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = data.copy()
    data["text"] = data["text"].apply(lambda value: clean_text(value, single_line=True))
    data["title"] = (
        data["title"].apply(lambda value: clean_text(value, single_line=True))
        if "title" in data
        else ""
    )
    data["model_text"] = (
        data["title"].fillna("").astype(str)
        + " "
        + data["text"].fillna("").astype(str)
        + " "
        + data["url"].apply(url_features)
    )
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--probability-model", type=Path, default=DEFAULT_PROBABILITY_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = prepare_rows(pd.read_csv(args.input))
    classifier = joblib.load(args.model)

    data["predicted_genre"] = classifier.predict(data["model_text"])

    probability_classifier = joblib.load(args.probability_model)
    probability_columns = probability_classifier.predict_proba(data["model_text"])
    for genre, probabilities in zip(probability_classifier.classes_, probability_columns.T):
        data[f"probability_{genre}"] = probabilities

    non_academic_columns = [
        f"probability_{genre}" for genre in NON_ACADEMIC_GENRES
        if f"probability_{genre}" in data
    ]
    data["non_academic_probability"] = data[non_academic_columns].sum(axis=1)
    data["academic_probability"] = 1 - data["non_academic_probability"]

    if "genre" in data:
        actual = data["genre"].astype(str).str.strip().str.lower()
        valid = actual.ne("")
        if valid.any():
            print(f"Accuracy: {accuracy_score(actual[valid], data.loc[valid, 'predicted_genre']):.3f}")
            print("\nClassification report:")
            print(classification_report(
                actual[valid],
                data.loc[valid, "predicted_genre"],
                digits=3,
                zero_division=0,
            ))

            labels = sorted(set(actual[valid]) | set(data.loc[valid, "predicted_genre"]))
            print("Confusion matrix (rows=true, columns=predicted):")
            print(pd.DataFrame(
                confusion_matrix(actual[valid], data.loc[valid, "predicted_genre"], labels=labels),
                index=labels,
                columns=labels,
            ).to_string())

    data.to_csv(args.output, index=False)
    print(f"\nPredicted {len(data)} rows")
    print("Prediction counts:")
    print(data["predicted_genre"].value_counts())
    print(f"Mean academic probability: {data['academic_probability'].mean():.3f}")
    print(f"Mean non-academic probability: {data['non_academic_probability'].mean():.3f}")
    print(f"Saved predictions: {args.output}")


if __name__ == "__main__":
    main()
