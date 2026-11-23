import json
import os
import struct
import zlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Fixed-width binary format (38 bytes total, Little-Endian):
# Q: info_offset  (uint64, 8 bytes) - byte offset in doc_info.jsonl
# I: info_length  (uint32, 4 bytes) - byte length in doc_info.jsonl
# I: created_ts   (uint32, 4 bytes) - first version Unix timestamp
# I: updated_ts   (uint32, 4 bytes) - update_date Unix timestamp
# H: num_versions (uint16, 2 bytes) - count of versions
# H: doc_len      (uint16, 2 bytes) - total word count (capped at 65,535)
# Q: cat_mask     (uint64, 8 bytes) - 64-bit bitmask for the 40 cs.* categories
# B: pub_flag     (uint8,  1 byte)  - bit 0: has_doi, bit 1: has_journal_ref
# B: status       (uint8,  1 byte)  - 1: active, 0: deleted/withdrawn
# I: checksum     (uint32, 4 bytes) - deterministic CRC32 of arxiv_id

RECORD_FORMAT = "<QIIIHHQBBI"
RECORD_SIZE = struct.calcsize(RECORD_FORMAT) # Strictly 38 bytes

CS_CATEGORIES = [
    "cs.AI", "cs.AR", "cs.CC", "cs.CE", "cs.CG", "cs.CL", "cs.CR", "cs.CV",
    "cs.CY", "cs.DB", "cs.DC", "cs.DL", "cs.DM", "cs.DS", "cs.ET", "cs.FL",
    "cs.GL", "cs.GR", "cs.GT", "cs.HC", "cs.IR", "cs.IT", "cs.LG", "cs.LO",
    "cs.MA", "cs.MM", "cs.MS", "cs.NA", "cs.NE", "cs.NI", "cs.OH", "cs.OS",
    "cs.PF", "cs.PL", "cs.RO", "cs.SC", "cs.SD", "cs.SE", "cs.SI", "cs.SY",
]
CAT_TO_BIT = {cat: idx for idx, cat in enumerate(CS_CATEGORIES)} # Creates a dictionary that maps each item in CS_CATEGORIES to a unique integer index (starting from 0)

def parse_created_date(versions: List[Dict[str, Any]]) -> int:
    # Extracts Unix timestamp from the first version's RFC 2822 created date.
    if not versions or not isinstance(versions, list):
        return 0
    first_created = versions[0].get("created", "")
    if not first_created:
        return 0
    try:
        dt = parsedate_to_datetime(first_created)
        return max(0, int(dt.timestamp()))
    except Exception:
        return 0

def parse_update_date(update_date_str: str) -> int:
    #Extracts Unix timestamp from YYYY-MM-DD update_date.
    if not update_date_str:
        return 0
    try:
        dt = datetime.strptime(update_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc) # Keeps the update time consistent (UTC) with creation time
        return max(0, int(dt.timestamp()))
    except Exception:
        return 0

def encode_category_mask(categories_str: str) -> int:
    # Packs all matching cs.* categories into a 64-bit integer bitmask.
    mask = 0
    for cat in categories_str.split():
        bit = CAT_TO_BIT.get(cat)
        if bit is not None:
            mask |= (1 << bit)
    return mask

class DocumentIndex:
    def __init__(self, index_dir: str = "index"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True) # safely create the directory stored in self.index_dir along with any missing parent directories, without throwing an error if it already exists

        self.bin_path = self.index_dir / "doc_index.bin" # The fixed-width 38-bye binary ISAM index
        self.info_path = self.index_dir / "doc_info.jsonl" # The variable-width file holding titles, authors, categories and abstracts
        self.map_path = self.index_dir / "arxiv_id_map.json" # The dictionary mapping string arXiv IDs to sequential integer docIDs

        self._bin_file = None

        # Maps string arxiv_id -> integer docID
        self.arxiv_to_docid: Dict[str, int] = {}
        self.num_docs: int = 0

        if self.map_path.exists() and self.bin_path.exists():
            self._load_existing_state()

    def _load_existing_state(self) -> None:
        #Loads ID map and verifies record count from disk.
        with open(self.map_path, "r", encoding="utf-8") as f:
            self.arxiv_to_docid = json.load(f)
        self.num_docs = os.path.getsize(self.bin_path) // RECORD_SIZE # Calculates the total number of indexed documents by dividing the total byte size of doc_index.bin by byte size of one record

    def build_from_jsonl(self, jsonl_path: str) -> int:
        # Streams the dataset JSONL file and build doc_index.bin, doc_info_josnl, and arxiv_id_map.json from scratch.
        self.arxiv_to_docid.clear()
        self.num_docs = 0

        with open(jsonl_path, "r", encoding="utf-8") as src_file, \
                open(self.bin_path, "wb") as bin_file, \
                open(self.info_path, "wb") as info_file:

            for line in src_file:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                self._write_record(record, bin_file, info_file)

        self.save_id_map()
        self.close()
        return self.num_docs

    def _write_record(self, record: Dict[str, Any], bin_file, info_file) -> Optional[int]:
        # Writes a single document record to optn binary and info file streams.
        arxiv_id = str(record.get("id", "")).strip()
        if not arxiv_id or arxiv_id in self.arxiv_to_docid: # Checks if the paper has a valid id and isn't already indexed
            return None

        doc_id = self.num_docs #  Assigns the next sequential integer as this document's docID
        title = " ".join(str(record.get("title", "")).split()) # Safely looks up title key in the dictionary and returns an emppty string "" if it doesnt exist. Splits the string into list of words automatically stripping leadin/trailes whitespace and tabs and join sthe list of words back together with a single space between them
        abstract = " ".join(str(record.get("abstract", "")).split())
        categories = str(record.get("categories", "")).strip()
        authors = str(record.get("authors", "")).strip()

        # Extract ranking metadata fields
        versions = record.get("versions", [])
        num_versions = min(65535, len(versions) if isinstance(versions, list) else 1) # Caps the version count at 65535 to store it as 16-bit integer
        created_ts = parse_created_date(versions)
        updated_ts = parse_update_date(str(record.get("update_date", "")))
        if created_ts == 0 and updated_ts > 0:
            created_ts = updated_ts # If created_ts couldn't be parsed, it falls back to updated_ts

        has_doi = 1 if record.get("doi") else 0
        has_journal = 1 if record.get("journal-ref") else 0
        pub_flag = (has_doi & 1) | ((has_journal & 1) << 1) # Bitwise packing into 1 byte

        doc_len = min(65535, len(title.split()) + len(abstract.split()))
        cat_mask = encode_category_mask(categories)
        status = 1
        checksum = zlib.crc32(arxiv_id.encode("utf-8")) & 0xFFFFFFFF

        # Write variable-width disply data to doc_info.jsonl
        info_payload = {
            "doc_id": doc_id,
            "id": arxiv_id,
            "title": title,
            "authors": authors,
            "categories": categories,
            "abstract": abstract,
            "update_date": record.get("update_date", ""),
            "doi": record.get("doi"),
            "journal-ref": record.get("journal-ref")
        }
        info_bytes = (json.dumps(info_payload, ensure_ascii=False) + "\n").encode("utf-8")
        info_offset = info_file.tell() # Returns the exact current byte position in doc_info.jsonl right before writing.
        info_length = len(info_bytes)
        info_file.write(info_bytes)

        # Pack and write fixed-width 38-byte record to doc_index.bin
        packed_entry = struct.pack(
            RECORD_FORMAT,
            info_offset,
            info_length,
            created_ts,
            updated_ts,
            num_versions,
            doc_len,
            cat_mask,
            pub_flag,
            status,
            checksum
        )
        bin_file.write(packed_entry)

        self.arxiv_to_docid[arxiv_id] = doc_id
        self.num_docs += 1
        return doc_id

    def add_document(self, record: Dict[str, Any]) -> Optional[int]:
        # Dynamically appends a single new document in O(1) time without rebuilding the index
        with open(self.bin_path, "ab") as bin_file, \
             open(self.info_path, "ab") as info_file:
            info_file.seek(0, os.SEEK_END)
            doc_id = self._write_record(record, bin_file, info_file)

        if doc_id is not None:
            self.save_id_map()
        self.close()
        return doc_id

    def get_ranking_metadata(self, doc_id: int) -> Dict[str, Any]:
        # Fetches fixed-width numeridc metadata in 1 disk seek for fast scoring during query evaluation
        if doc_id < 0 or doc_id >= self.num_docs:
            raise IndexError(f"doc_id {doc_id} out of range (0...{self.num_docs - 1})")

        if self._bin_file is None:
            self._bin_file = open(self.bin_path, "rb")
            
        self._bin_file.seek(doc_id * RECORD_SIZE)
        raw = self._bin_file.read(RECORD_SIZE)

        (
            info_offset,
            info_length,
            created_ts,
            updated_ts,
            num_versions,
            doc_len,
            cat_mask,
            pub_flag,
            status,
            checksum
        ) = struct.unpack(RECORD_FORMAT, raw)

        return {
            "doc_id": doc_id,
            "info_offset": info_offset,
            "info_length": info_length,
            "created_ts": created_ts,
            "updated_ts": updated_ts,
            "num_versions": num_versions,
            "doc_len": doc_len,
            "cat_mask": cat_mask,
            "has_doi": bool(pub_flag & 1),
            "has_journal_ref": bool(pub_flag & 2),
            "status": status,
            "checksum": checksum
        }

    def get_document_info(self, doc_id: int) -> Dict[str, Any]:
        # Uses the pointer in doc_index.bin to fetch the full title, authors, categories, and abstract from doc_info in 1 seek.
        meta = self.get_ranking_metadata(doc_id)
        with open(self.info_path, "rb") as info_file:
            info_file.seek(meta["info_offset"])
            raw_json = info_file.read(meta["info_length"]).decode("utf-8")

        doc_info = json.loads(raw_json)
        doc_info["ranking_meta"] = meta
        return doc_info

    def save_id_map(self) -> None:
        # Saves the in-memory arxiv_id -> doc_id dictionary to disk
        with open(self.map_path, "w", encoding="utf-8") as f:
            json.dump(self.arxiv_to_docid, f)

    def close(self) -> None:
        if self._bin_file is not None:
            self._bin_file.close()
            self._bin_file = None

if __name__ == "__main__":
    # Quick test on sample dataset (This block will be ignored if another file runs this script)
    doc_idx = DocumentIndex(index_dir="index")
    sample_file = "data/arxiv_cs_sample.jsonl"

    if os.path.exists(sample_file):
        count = doc_idx.build_from_jsonl(sample_file)
        print(f"Indexed {count} documents into 'index/'.")
        if count > 0:
            sample_doc = doc_idx.get_document_info(0)
            print(f"DocID 0 Title: {sample_doc['title']}")
            print(f"DocID 0 Metadata: {sample_doc['ranking_meta']}")