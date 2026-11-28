# Search Engine on arXiv Computer Science Papers

An advanced search engine built over a curated Computer Science (`cs.*`) subset of the arXiv research paper dataset, developed as the semester project for **CS-250: Data Structures and Algorithms** at NUST (SEECS).

## Team Members (BESE-2025)

| Name | CMS ID |
|------|--------|
| Hashir Saleem | 549261 |
| Haroon Ahmed | 553116 |
| Jawad Iqbal | 572633 |

## Current Project State

The repository currently contains the project proposal, requirements, curated 75,000-paper arXiv Computer Science dataset subset, binary document index, LaTeX-aware text tokenizer, and corpus lexicon:

```text
.
├── data/
│   ├── arxiv_cs_sample.jsonl      # 1,000-paper sample for quick testing & Milestone 2 evaluation (~1.9 MB)
│   ├── arxiv_cs_subset.jsonl.gz   # Compressed full 75,000-paper CS subset tracked in Git (~46 MB)
│   └── arxiv_cs_subset.jsonl      # Uncompressed full 75,000-paper subset (~138 MB, gitignored)
├── docs/
│   ├── proposal.md                # Submitted project proposal
│   └── requirements.md            # Course project specification & grading criteria
├── index/                         # Generated index & metadata files (gitignored)
├── src/
│   ├── doc_index.py               # Fixed-width binary DocumentIndex (doc_index.bin + doc_info.jsonl)
│   ├── lexicon.py                 # Thread-safe Lexicon mapping unique terms to word_ids with df/cf stats
│   └── tokenizer.py               # LaTeX/Unicode-aware CS paper & query tokenizer
├── .gitignore
└── README.md
```

### Building the Document Index & Lexicon

Run the document indexer and lexicon builder on the 1,000-paper sample dataset (generates `doc_index.bin`, `doc_info.jsonl`, `arxiv_id_map.json`, and `lexicon.jsonl` inside `index/`):

```bash
python3 src/doc_index.py
python3 src/lexicon.py
```

### Extracting the Full Dataset After Cloning

Because GitHub enforces a 100 MB single-file limit, the full 75,000-paper dataset is committed as `data/arxiv_cs_subset.jsonl.gz` (~46 MB), while the uncompressed `.jsonl` file is ignored by Git. After cloning, decompress it with:

```bash
gzip -dk data/arxiv_cs_subset.jsonl.gz
```

## Dataset Details

- **Source:** [Cornell University arXiv Dataset (Kaggle)](https://www.kaggle.com/datasets/Cornell-University/arxiv) (`arxiv-metadata-oai-snapshot.json`)
- **Format:** JSON Lines (`data/arxiv_cs_subset.jsonl`), 1 record per line
- **Records:** 75,000 papers
- **Median Abstract Length:** 170 words (minimum 80 words)
- **Year Range:** 2010–2025
- **Categories:** 40 `cs.*` categories (155 total including cross-listed categories)

### Record Schema

Each line in `data/arxiv_cs_subset.jsonl` is a JSON object containing:

- `id`: arXiv identifier (e.g., `"2503.16286"`)
- `title`: Paper title
- `abstract`: Full paper abstract
- `authors` & `authors_parsed`: Author names
- `categories`: Space-separated arXiv category tags (e.g., `"cs.LG"`)
- `versions`: List of version objects with `version` and `created` timestamps
- `update_date`: Last updated date (`YYYY-MM-DD`)
- `journal-ref`, `doi`, `comments`, `report-no`, `submitter`, `license`

### Dataset License & Attribution

The arXiv metadata snapshot is provided by **arXiv** and **Cornell University** under the [CC0 1.0 Universal (Public Domain Dedication)](https://creativecommons.org/publicdomain/zero/1.0/) license. Only paper metadata and abstracts are used in this project.
