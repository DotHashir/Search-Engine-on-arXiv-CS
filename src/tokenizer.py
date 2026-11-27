import json
import re
import unicodedata
from pathlib import Path
from typing import List, NamedTuple

# Small, CS-safe English stopword list (~75 words).
# Intentionally preserves CS/math terms like: set, map, tree, state, order,
# not, all, any, while, case, class, type, value, true, false.
STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "once", "here", "there", "where", "why", "how",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "we", "our", "ours", "you", "your", "he", "him", "his", "she", "her",
    "it", "its", "they", "them", "their", "this", "that", "these", "those",
    "which", "who", "whom", "whose", "what", "as", "of", "than", "too",
    "very", "just", "also", "such", "so", "can", "will", "would", "should",
    "could", "may", "might", "must", "shall", "however", "thus", "therefore",
})

UNICODE_FOLD_TABLE = str.maketrans({
    "ß": "ss", "ł": "l", "Ł": "l", "ø": "o", "Ø": "o",
    "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "đ": "d", "Đ": "d",
})

# Raw URLs (http://..., https://..., www....)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s}<>)\]]+")

# Structural LaTeX commands whose {arguments} are metadata, not prose (e.g., \begin{itemize}, \cite{grover06}, \ref{eq:1}, \url{...})
LATEX_STRUCT_RE = re.compile(r"\\(?:begin|end|cite[a-zA-Z]*|ref|eqref|label|url|href)\*?(?:\[[^\]]*\])*\{[^}]*\}")

# Symbol-based LaTeX accents: \"o, \"{o}, {\"o}, \'e, na\"{\i}ve -> base letter
LATEX_ACCENT_SYMBOL_RE = re.compile(r"\{?\\[\"'`^~=.](?:\{\\?([a-zA-Z])\}|([a-zA-Z]))\}?")

# Letter-based LaTeX accents: \H{o}, {\H{o}}, \c{c}, \v{s} -> base letter
LATEX_ACCENT_LETTER_RE = re.compile(r"\{?\\[Hcuvkdb](?:\{\\?([a-zA-Z])\}|\s+([a-zA-Z]))\}?")

# General LaTeX commands: \mathcal, \alpha, \textbf -> space
LATEX_CMD_RE = re.compile(r"\\[a-zA-Z]+")

# Special CS languages
CPP_RE = re.compile(r"\bc\+\+(?![a-z+])")
CSHARP_RE = re.compile(r"\bc#(?![a-z0-9#])")

# Possessives (dijkstra's -> dijkstra) & contractions (don't -> dont, we've -> weve)
POSSESSIVE_RE = re.compile(r"'s\b")
CONTRACTION_RE = re.compile(r"(?<=[a-z])'(?=[a-z])")

# Single-char inline math & single-letter hyphenated CS prefixes ($k$-means -> kmeans, $3$D -> 3d)
SINGLE_CHAR_MATH_RE = re.compile(r"\$([a-z0-9])\$")
SINGLE_PREFIX_HYPHEN_RE = re.compile(r"\b([a-z])-([a-z]{2,})\b")

# Lowercase alphanumeric tokens
TOKEN_RE = re.compile(r"[a-z0-9]+")

class Token(NamedTuple):
    word: str
    position: int
    is_title: bool

def clean_text(text: str) -> str:
    # Folds Unicode accents to ASCII, unwraps LaTeX accents, strips LaTeX commands, and lowercases.
    if not text:
        return ""
    # Decompose accented chars (é -> e + accent) & ligatures (ﬁ -> fi), then drop accent marks
    text = unicodedata.normalize("NFKD", text.translate(UNICODE_FOLD_TABLE)).encode("ascii", "ignore").decode("ascii")
    text = LATEX_STRUCT_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    # Unwrap LaTeX accents into their base letters (no spaces inserted)
    text = LATEX_ACCENT_SYMBOL_RE.sub(r"\1\2", text)
    text = LATEX_ACCENT_LETTER_RE.sub(r"\1\2", text)
    # Strip remaining LaTeX commands (e.g., \mathcal, \log)
    text = LATEX_CMD_RE.sub(" ", text)
    text = text.lower()
    text = SINGLE_CHAR_MATH_RE.sub(r"\1", text)
    text = CPP_RE.sub("cpp", text)
    text = CSHARP_RE.sub("csharp", text)
    text = POSSESSIVE_RE.sub("", text)
    text = CONTRACTION_RE.sub("", text)
    text = SINGLE_PREFIX_HYPHEN_RE.sub(r"\1\2", text)
    return text

def _is_valid_token(word: str) -> bool:
    # Filters out 1-character noise (e.g., math variables x, n, k) and arbitrary numbers, while keeping 4-digit years and alphanumeric CS terms.
    if len(word) < 2 or len(word) > 40:
        return False
    if word.isdigit():
        # Keep plausible publication/model years (e.g., 2017, 2024); drop random numbers
        return len(word) == 4 and 1900 <= int(word) <= 2099
    return True

def tokenize(text: str, remove_stopwords: bool = False) -> List[str]:
    """
    Converts raw text (such as a user search query) into a clean, ordered list of lowercase tokens.
    Stopwords are kept by default for indexing and multi-word queries;
    pass remove_stopwords=True for semantic query expansion or Trie filtering
    """
    cleaned = clean_text(text)
    tokens = [tok for tok in TOKEN_RE.findall(cleaned) if _is_valid_token(tok)]
    if remove_stopwords:
        return [tok for tok in tokens if tok not in STOPWORDS]
    return tokens

def tokenize_document(title: str, abstract: str, authors: str = "") -> List[Token]:
    """
    Tokenizes a paper's title, abstract, and optional authors into a single ordered stream of Token(word, position, is_title) entries.

    Title tokens occupy positions 0..(T-1) with is_title=True.
    Abstract (and optional author) tokens continue from T onward with is_title=False.
    """
    tokens: List[Token] = []
    pos = 0

    for word in tokenize(title):
        tokens.append(Token(word=word, position=pos, is_title=True))
        pos += 1

    for word in tokenize(abstract):
        tokens.append(Token(word=word, position=pos, is_title=False))
        pos += 1

    if authors:
        for word in tokenize(authors):
            tokens.append(Token(word=word, position=pos, is_title=False))
            pos += 1

    return tokens

if __name__ == "__main__":
    # 1. Synthetic test covering LaTeX, hyphens, alphanumeric terms, and stopwords
    sample_title = "Self-Attention in 3D Graph Neural Networks (2024)"
    sample_abstract = (
        r"We propose an end-to-end method with $\mathcal{0}(n \log n)$ complexity "
        r"for Data structures and Algorithms using L2 regularization."
    )

    doc_tokens = tokenize_document(sample_title, sample_abstract)
    print(f"Total tokens: {len(doc_tokens)}")
    for t in doc_tokens[:12]:
        field = "TITLE" if t.is_title else "ABSTRACT"
        print(f"  pos={t.position:<2} [{field:<8}] {t.word}")

    accent_test = (
        r'Schr\"odinger Schrödinger R\'enyi Fr\'echet B\"uchi Poincaré '
        r'Gr\"obner H\"older Cram\'er Lov\'asz B\'ezier Erd\H{o}s na\"ive na\"{\i}ve'
    )
    print("\nAccent test:", tokenize(accent_test))

    # 2. Query consistency check
    query = "Data structures and Algorithms"
    print(f"\nQuery tokens for {query!r}: {tokenize(query)}")

    # 3. Quick check on DocID 0 from your generated index/doc_info.jsonl
    project_root = Path(__file__).resolve().parent.parent
    doc_info_path = project_root / "index" / "doc_info.jsonl"
    if doc_info_path.exists():
        with open(doc_info_path, "r", encoding="utf-8") as f:
            first_doc = json.loads(f.readline())
        real_tokens = tokenize_document(first_doc["title"], first_doc["abstract"])
        print(f"\nReal DocID 0 ({first_doc['id']}): {len(real_tokens)} tokens")
        print("First 10 tokens:", [t.word for t in real_tokens[:10]])