# Project Proposal: Advanced Search Engine for arXiv Computer Science Papers

- **Course:** CS-250 Data Structures and Algorithms
- **Class:** BESE-2025
- **Instructor:** Prof. Dr. Faisal Shafait
- **Submission Date:** 15 November 2026

## 1. Group Members

| # | Name | CMS ID |
|---|------|--------|
| 1 | Hashir Saleem | 549261 |
| 2 | Haroon Ahmed | 553116 |
| 3 | Jawad Iqbal | 572633 |

## 2. Selected Dataset

- **Source:** [Cornell University arXiv Dataset (Kaggle)](https://www.kaggle.com/datasets/Cornell-University/arxiv), the arXiv metadata snapshot (`arxiv-metadata-oai-snapshot.json`), one JSON record per line. This dataset is not on the list of disallowed datasets, and no Semantic Scholar, S2ORC, or CORD-19 data is mixed in.
- **License:** The Kaggle dataset page lists the metadata under the **CC0 1.0 (Public Domain)** license. We use only the metadata and abstracts, do not redistribute the original papers, and credit arXiv and Cornell University as the source. Individual papers on arXiv carry their own licenses; we do not use their full text.
- **Subset Used:** A random sample of 75,000 papers, extracted by streaming the 5.5 GB file with reservoir sampling (fixed seed for reproducibility), under these criteria:
  - Primary or secondary category begins with `cs.` (Computer Science)
  - First version created between 2010 and 2025
  - Abstract of at least 80 words
  - Non-empty title; withdrawn papers and duplicates removed

### Subset Statistics

| Measure | Value |
|---------|-------|
| Number of documents | 75,000 |
| Median abstract length | 170.0 words |
| Year range / distribution | 2010–2025 |
| Number of distinct categories | 40 `cs.*` categories (155 total including cross-lists) |

### Fields Available per Record
`id`, `title`, `abstract`, `authors`, `categories`, `versions` (with creation dates), `update_date`, `journal-ref`, `doi`, `comments`.

### Metadata Used in Ranking
- **Recency:** First-version creation date and `update_date`
- **Categories:** Match between query terms and the paper's primary and secondary categories
- **Revision Count:** Number of versions, as a proxy for maintained work
- **Publication Status:** Presence of `journal-ref` or `doi`
- **Term Frequency & Position:** Title matches weighted above abstract matches

## 3. Languages and Frameworks

| Area | Technology |
|------|------------|
| Core language | Python 3 |
| Indexing and search | Python standard library, NumPy; index data stored as binary and JSON files |
| Autocomplete | Trie built from the lexicon, with frequency-ranked suggestions |
| Semantic search | Pre-trained GloVe vectors (loaded only for the lexicon vocabulary to save RAM); custom query-expansion and similarity logic using cosine similarity |
| Backend API | FastAPI |
| Frontend | React (Vite) with a responsive layout and an autocomplete dropdown |
| Deployment | Cloud platform (Render, Railway, or Fly.io) |
| Version control | Git and GitHub (private repository) |
