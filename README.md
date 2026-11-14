# NLP-Framework

Setup on each laptop:

python -m venv .venv, then activate it.
pip install -r requirements.txt
python -m spacy download en_core_web_sm
Copy .env.example to .env and paste in your own keys. Each person can use their own Tavily and Semantic Scholar keys, or share one over chat. Never commit them.
Crossref needs no key, only a real email in CROSSREF_MAILTO.
