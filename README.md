# NLP-Framework

Setup on each laptop:

python -m venv .venv, then activate it.
pip install -r requirements.txt
python -m spacy download en_core_web_sm
Copy .env.example to .env and paste in your own keys. Each person can use their own Tavily and Semantic Scholar keys, or share one over chat. Never commit them.
Crossref needs no key, only a real email in CROSSREF_MAILTO.

## Authority (Journals)
SJR 2025 edition (all three laptops should use the same file)

## Topics Split (tba)
Tuning topics are for choosing α, the currency half-life, and the quartile mapping.
Validation topics are for comparing configurations and picking the final one.
Test topics are touched once, at the end, for the reported results. No tuning of any kind on them, including peeking at scores to adjust a setting.
Pilot topics are for debugging the pipeline and checking annotator agreement only. They never appear in the reported results.


## Project structure

Run every command from the project root.

```
NLP-Framework/
├── framework/                  The system itself, in pipeline order
│   ├── retrieval/              1. Get candidate sources (Crossref, Semantic Scholar, Tavily) + remove duplicates
│   ├── preprocessing/          2. Clean text, extract publication dates and publisher info
│   ├── craap/                  3. The four CRAAP signals
│   │   ├── currency/           Up-to-date score (publication date, half-life decay)
│   │   ├── relevance/          Relevance score (semantic encoder)
│   │   ├── authority/          Authority score (SJR journal rank, paper, web domain)
│   │   └── purpose/            Purpose score (genre classifier + trained models)
│   └── fusion/                 4. Weighted sum of the signals -> Source Suitability Score
├── experiments/                Offline work: building the ground truth, choosing models, evaluating
│   ├── data_prep/              Topic split, candidate retrieval, labeling sheets, collecting labels
│   ├── model_selection/        Encoder comparison and benchmarks
│   └── evaluation/             NDCG@k, Precision@k, Recall@k, MAP
├── data/                       All data files, grouped by purpose
│   ├── topics/                 Research topics and the tuning/validation/test split
│   ├── retrieval/              Raw API responses (raw/) and candidate source lists
│   ├── sources/                Pilot source lists
│   ├── labeling/               Human labeling sheets (pilot/)
│   ├── reference/              Lookup tables: SJR 2025 journal ranks, news domains
│   ├── signals/                Computed signal scores (currency, relevance, authority, purpose, combined)
│   └── benchmarks/             Encoder benchmark and ranking results
├── tests/                      Unit tests  (python -m pytest tests)
├── app/                        Streamlit interface  (streamlit run app/streamlit_app.py)
├── assets/                     Logos and images used by the app
└── docs/                       Annotation guidelines and design decisions
```

Python modules are imported by their folder path, for example
`from framework.preprocessing.clean_text import clean_text` or
`python -m framework.retrieval.check_keys`.
