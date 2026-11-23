# CS-250: Project Requirements & Specification

- **Course:** CS-250 Data Structures and Algorithms
- **Class:** BESE-2025
- **Instructor:** Prof. Dr. Faisal Shafait

## Dataset Requirements

- At least **45,000** items (45,000–150,000 recommended).
- Text-rich items: median item must contain at least **100 words** of text.
- At least **2 metadata fields** (e.g., dates, categories, scores, citations) must be used in ranking.
- Must comply with the dataset's license and state it in the proposal.
- Disallowed datasets (and their subsets/derivatives) must not be used.

## Functional & Technical Requirements

1. **Lexicon:** Maps all unique words in the dataset to distinct word IDs, stored in files.
2. **Forward Index:** Stores the list of words per document in files, used to build the inverted index.
3. **Inverted Index:** Stores the list of documents per word in files. *(Databases are not allowed for storing indexing data.)*
4. **Single-Word Search:** Returns relevant ranked results for a single-word query.
5. **Multi-Word Search:** Returns relevant results for multi-word queries (words need not be adjacent).
6. **Semantic Search:** Understands synonyms and conceptually similar queries. Pre-trained word embeddings (Word2Vec, GloVe, FastText) are allowed, but semantic matching logic must be self-implemented. *(LLMs and transformer-based embeddings are not allowed.)*
7. **Word Autocomplete:** Real-time query suggestions (3–5 suggestions) within **100 ms** per keystroke (Trie recommended).
8. **Ranking:** Ranks results using term frequency, position, and metadata criteria (PageRank not required).
9. **Barrels:** Divides the inverted index into smaller chunks (barrels) so the entire index does not need to be loaded into RAM at once.
10. **Dynamic Content Addition:** Automatically indexes newly added content without blocking search, supporting:
    - JSON file (following dataset format)
    - Plain text file
    - Manual entry through the UI
11. **Scalability & Performance Targets:**
    - Single-word query: **< 500 ms**
    - 5-word query: **< 1.5 s**
    - No significant slowdown as query length increases (2–5 words) or dataset size > 45,000 documents
    - RAM usage: **≤ 2 GB** for < 100,000 documents (including word embeddings); **≤ 4 GB** for ≥ 100,000 documents
    - New document indexing: **< 1 minute**, non-blocking
12. **User Interface:** Clean, modern, responsive web or desktop GUI with search, real-time autocomplete dropdown, pagination, and a UI to add new content.
13. **Deployment:** Deployed online with a publicly accessible URL (demo subset allowed online if full-scale performance is demonstrated locally during the viva).
14. **Git Collaboration:**
    - Minimum **20 meaningful commits** throughout the project
    - Commits from all team members with proper commit messages and regular pushes

## Timeline

| Deliverable | Deadline |
|---|---|
| 1. Project Proposal | 15 November 2026 |
| 2. Lexicon, Forward and Inverted Index (with sample test data) | 29 November 2026 |
| 3. Barrels Implementation | 6 December 2026 |
| 4. Complete Submission (code + documentation) | 16 December 2026 |
| 5. Presentation and Viva | 18 December 2026 |

## Grading Criteria (25 Points)

| Criteria | Points |
|---|---|
| Single-word search query works | 3 |
| Multiple-word search query works | 3 |
| Lexicon, forward index, and inverted index correctly implemented | 2 |
| Barrels efficiently divide and load inverted index | 2 |
| Ranking criteria returns relevant results | 2 |
| Document addition through multiple formats (JSON, text, manual) | 2 |
| Semantic search implemented and functional | 1.5 |
| Autocomplete works in real-time (< 100 ms) | 1.5 |
| User interface follows professional design standards | 1.5 |
| Query performance meets targets | 1 |
| Memory usage within limits | 1 |
| New document indexing completes within 1 minute | 1 |
| Deployment follows professional practices | 1 |
| Git used effectively for collaboration | 1.5 |
| Code quality (style, comments, modularity) | 1 |
| **Total** | **25** (+2 bonus for field visit data) |
