import trafilatura

url = "https://en.wikipedia.org/wiki/Federated_learning"

html = trafilatura.fetch_url(url)
print("fetched:", html is not None, "| length:", len(html) if html else 0)

if html:
    meta = trafilatura.extract_metadata(html)
    print("description:", meta.description if meta else None)
    text = trafilatura.extract(html)
    print("text start:", (text or "")[:200])