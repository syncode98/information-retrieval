# Homework #2 » Boolean Retrieval

## Commands:

### Run indexing
```
    python3 index.py -i nltk_data/corpora/reuters/training/ -d dictionary.txt -p postings.txt
```

### Run searching
```
    python3 search.py -d dictionary.txt -p postings.txt -q queries.txt -o search_results.txt
```