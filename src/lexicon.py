import json
import os
import time
import threading
import math
from array import array
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try: # Makes imports work regardless of how you run the script—whether from the project root (python -m src.lexicon or via FastAPI) or directly (python src/lexicon.py)
    from src.tokenizer import Token, tokenize_document
except ImportError:
    from tokenizer import Token, tokenize_document

class Lexicon:
    """
    Maps every unique term in the corpus to a sequential integer word_id (0..V-1)
    and stores corpus-wide document frequency (df) and collection frequency (cf).
    Stored on disk as index/lexicon.jsonl (one JSON object per line, ordered by word_id).
    """

    def __init__(self, index_dir: str = "index"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.lexicon_path = self.index_dir / "lexicon.jsonl"

        self.word_to_id: Dict[str, int] = {}
        self.id_to_word: List[str] = []
        # Unsigned 32-bit integer arrays use 4 bytes/entry (far less RAM than Python lists of int)
        self.df: array = array("I")
        self.cf: array = array("I")
        self.total_tokens: int = 0
        self._lock = threading.RLock()

    def __len__(self) -> int:
        return len(self.id_to_word)

    def __contains__(self, word: str) -> bool:
        return word in self.word_to_id

    def build_from_doc_info(self, doc_info_path: str, include_authors: bool = True) -> int:
        # Streams index/doc_info.jsonl one paper at a time, counts df and cf for every unique token, assigns alphabetically sorted word_ids, and writes index/lexicon.jsonl to disk.
        df_counts: Dict[str, int] = {}
        cf_counts: Dict[str, int] = {}

        with open(doc_info_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                authors = doc.get("authors", "") if include_authors else ""
                tokens = tokenize_document(
                    doc.get("title", ""),
                    doc.get("abstract", ""),
                    authors
                )

                seen_in_doc = set() # Creates an unordered collection of unique elements
                for tok in tokens:
                    w = tok.word
                    cf_counts[w] = cf_counts.get(w, 0) + 1 # Increments total occurrences every time w appears (Looks up jey w in the dict. If exists returns count else 0 instead of failing)
                    if w not in seen_in_doc:
                        seen_in_doc.add(w)
                        df_counts[w] = df_counts.get(w, 0) + 1 # Increments df_counts[w] only once per paper

        # Resets structures and assigns alphabetically ordered word_ids
        self.word_to_id.clear()
        self.id_to_word.clear()
        self.df = array("I")
        self.cf = array("I")
        self.total_tokens = 0

        for word_id, word in enumerate(sorted(cf_counts.keys())): # Sorts all unique words alphabetically and assigns sequential word_ids
            cf_val = cf_counts[word]
            self.word_to_id[word] = word_id
            self.id_to_word.append(word)
            self.df.append(df_counts[word])
            self.cf.append(cf_val)
            self.total_tokens += cf_val

        self.save()
        return len(self.id_to_word)

    def save(self) -> None:
        # Automatically writes the lexicon to index/lexicon.jsonl.
        with self._lock:
            tmp_path = self.lexicon_path.with_suffix(".jsonl.tmp") # Writes to a temporary file first instead of overwriting lexicon.jsonl directly.
            with open(tmp_path, "w", encoding="utf-8") as f:
                for word_id, word in enumerate(self.id_to_word):
                    record = {
                        "word_id": word_id,
                        "word": word,
                        "df": self.df[word_id],
                        "cf": self.cf[word_id]
                    }
                    f.write(json.dumps(record, ensure_ascii=True) + "\n")
            os.replace(tmp_path, self.lexicon_path) # Atomically renames the temporary file over the real lexicon.jsonl

    def load(self) -> int:
        # Loads index/lexicon.jsonl into memory.
        if not self.lexicon_path.exists():
            raise FileNotFoundError(f"Lexicon file not found: {self.lexicon_path}")

        self.word_to_id.clear()
        self.id_to_word.clear()
        self.df = array("I")
        self.cf = array("I")
        self.total_tokens = 0

        with open(self.lexicon_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                word_id = rec["word_id"]
                if word_id != len(self.id_to_word):
                    raise ValueError(f"Non-contiguous word_id {word_id} at line {len(self.id_to_word)} in {self.lexicon_path}")
                word = rec["word"]
                self.word_to_id[word] = word_id
                self.id_to_word.append(word)
                cf_value = rec["cf"]
                self.df.append(rec["df"])
                self.cf.append(cf_value)
                self.total_tokens += cf_value

        return len(self.id_to_word)

    def update_from_tokens(self, tokens: List[Token], save: bool = True) -> int:
        # Dynamically updates the lexicon for a newly added document without rebuilding, shifting existing word_ids, or blocking live search reads. Returns the count of new words added.
        with self._lock:
            new_words = 0
            seen_in_doc = set()

            for tok in tokens:
                w = tok.word
                word_id = self.word_to_id.get(w)
                if word_id is None:
                    word_id = len(self.id_to_word)
                    self.id_to_word.append(w)
                    self.df.append(0)
                    self.cf.append(0)
                    self.word_to_id[w] = word_id
                    new_words += 1

                self.cf[word_id] += 1
                self.total_tokens += 1
                if w not in seen_in_doc:
                    seen_in_doc.add(w)
                    self.df[word_id] += 1

            if save:
                self.save()
            return new_words

    def update_from_documents(self, token_batches: List[List[Token]], save: bool = True) -> int:
        """
        Thread-safely updates the lexicon for a batch of newly uploaded documents (e.g., a multi-document JSON upload) and writes to disk only once.
        Returns the total count of new words added across the batch.
        """

        with self._lock:
            total_new_words = 0
            for tokens in token_batches:
                total_new_words += self.update_from_tokens(tokens, save=False)
            if save:
                self.save()
            return total_new_words

    def get_word_id(self, word: str) -> Optional[int]:
        return self.word_to_id.get(word)

    def get_word(self, word_id: int) -> str:
        if word_id < 0 or word_id >= len(self.id_to_word):
            raise IndexError(f"word_id {word_id} out of range (0..{len(self.id_to_word) - 1})")
        return self.id_to_word[word_id]

    def get_stats(self, word_id: int) -> Tuple[int, int]:
        # Returns (df, cf) for the given word_id.
        if word_id < 0 or word_id >= len(self.id_to_word):
            raise IndexError(f"word_id {word_id} out of range (0..{len(self.id_to_word) - 1})")
        return self.df[word_id], self.cf[word_id]

    def idf(self, word_id: int, num_docs: int) -> float:
        """
        Returns smoothed BM25 IDF for word_id given total corpus document count N.
        Smoothed BM25 IDF is a formula that measures how rare—and therefore how informative—a search term is across your corpus, adjusted so that very common words never receive a negative score.
        """
        if word_id < 0 or word_id >= len(self.id_to_word):
            raise IndexError(f"word_id {word_id} out of range (0..{len(self.id_to_word) - 1})")
        if num_docs <= 0:
            return 0.0
        df = min(self.df[word_id], num_docs)
        return math.log(1.0 + (num_docs - df + 0.5) / (df + 0.5))

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    index_dir = project_root / "index"
    doc_info_path = index_dir / "doc_info.jsonl"

    if not doc_info_path.exists():
        print(f"Missing {doc_info_path}. Run src/doc_index.py first.")
    else:
        lex = Lexicon(index_dir=str(index_dir))
        t0 = time.perf_counter()
        vocab_size = lex.build_from_doc_info(str(doc_info_path), include_authors=True)
        elapsed = time.perf_counter() - t0

        file_mb = lex.lexicon_path.stat().st_size / (1024 * 1024)
        print(f"Built lexicon: {vocab_size:,} unique words in {elapsed:.2f}s ({file_mb:.2f} MB)")

        # Top 10 most frequent words by document frequency
        top_ids = sorted(range(vocab_size), key=lambda wid: lex.df[wid], reverse=True)[:10]
        print("\nTop 10 words by df:")
        for wid in top_ids:
            print(f"  word_id={wid:<7} word={lex.id_to_word[wid]:<15} df={lex.df[wid]:<6} cf={lex.cf[wid]}")

        # Spot-check CS and accented terms
        print("\nSpot-check lookups:")
        for term in ("graph", "neural", "cpp", "kmeans", "schrodinger", "and"):
            wid = lex.get_word_id(term)
            if wid is not None:
                df, cf = lex.get_stats(wid)
                print(f"  {term:<12} -> word_id={wid:<7} df={df:<6} cf={cf}")
            else:
                print(f"  {term:<12} -> NOT FOUND")

        # Verify load() round-trip
        lex2 = Lexicon(index_dir=str(index_dir))
        t1 = time.perf_counter()
        loaded = lex2.load()
        print(f"\nReloaded {loaded:,} words in {time.perf_counter() - t1:.2f}s")
