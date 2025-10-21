# ====================================================================================
# This script performs advanced fuzzy matching to verify quotes, including those
# containing ellipses (...) representing non-contiguous text.
#
# The script performs the following actions:
#   1. For standard quotes, it uses a partial fuzzy match against the transcript.
#   2. For quotes with ellipses (e.g., "Part A ... Part B"), it splits the quote
#      and performs a sequential search: it finds Part A, then searches for
#      Part B only in the text that follows the match for Part A.
#   3. A quote is considered a match if its similarity score is 90% or higher. For
#      quotes with ellipses, this is the average score of all parts.
#   4. It compiles and prints a report listing all quotes that fall below the
#      90% similarity threshold, along with their calculated score.
#
# NOTE: This script requires the 'thefuzz' and 'python-Levenshtein' libraries.
# You can install them by running:
#   pip install thefuzz
#   pip install python-Levenshtein
# ====================================================================================

import csv
import os
import string
import html
import json
from tabulate import tabulate
from thefuzz import fuzz

# --- CONFIGURATION ---
# The minimum similarity score (out of 100) for a quote to be considered a match.
SIMILARITY_THRESHOLD = 80

def find_best_substring_match(query: str, text: str) -> tuple[int, int, int]:
    """
    Finds the best fuzzy match of a query string within a larger text string.
    This is a helper for sequential searching. Note: This can be slow on very long texts.

    Returns:
        A tuple containing (best_score, start_index_of_match, end_index_of_match).
    """
    if not query or not text or len(query) > len(text):
        return 0, -1, -1

    best_score = 0
    best_index = -1
    query_len = len(query)

    # Slide a window of the query's length across the text
    for i in range(len(text) - query_len + 1):
        substring = text[i:i + query_len]
        score = fuzz.ratio(query, substring)
        if score > best_score:
            best_score = score
            best_index = i

    return best_score, best_index, best_index + query_len

def calculate_fuzzy_score(quote: str, transcript: str) -> int:
    """
    Calculates the similarity score, handling quotes with ellipses (...) for
    non-contiguous, ordered matching.
    """
    if "..." not in quote:
        # Standard case: no ellipses, use partial ratio for a single best match.
        return fuzz.partial_ratio(quote, transcript)
    
    # Ellipsis case: perform sequential matching.
    parts = [p.strip() for p in quote.split("...") if p.strip()]
    
    if not parts:
        return 0
    
    # If after splitting, there's only one part (e.g., "...text..." or "text..."),
    # revert to the standard partial ratio search.
    if len(parts) == 1:
        return fuzz.partial_ratio(parts[0], transcript)

    part_scores = []
    search_start_index = 0
    
    for part in parts:
        search_area = transcript[search_start_index:]
        score, match_start_in_slice, match_end_in_slice = find_best_substring_match(part, search_area)
        
        if score < SIMILARITY_THRESHOLD:
            # If any part fails to meet the threshold, the entire quote fails.
            # Return this part's score to indicate the point of failure.
            return score
        
        part_scores.append(score)
        # Update the master index to search after the current match
        search_start_index += match_end_in_slice

    # If all parts are found in order, return their average score.
    return int(sum(part_scores) / len(part_scores))

# (The rest of the helper functions: normalize_text, extract_text_from_json, etc., remain unchanged)
def normalize_text(cell: str) -> str:
    if not cell: return ""
    s = html.unescape(cell); s = s.replace("\r", "").replace("\n", " ").replace("\u00A0", " ").strip()
    quote_pairs = [('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"), ("«", "»")]
    changed = True
    while changed and len(s) >= 2:
        changed = False
        for left, right in quote_pairs:
            if s.startswith(left) and s.endswith(right): s = s[1:-1].strip(); changed = True
    s = s.replace("”", '"').replace("“", '"').replace("’", "'").replace("‘", "'")
    return s

def extract_text_from_json(data) -> str:
    text_parts = []
    if isinstance(data, dict):
        for key, value in data.items(): text_parts.append(extract_text_from_json(value))
    elif isinstance(data, list):
        for item in data: text_parts.append(extract_text_from_json(item))
    elif isinstance(data, str): text_parts.append(data)
    return " ".join(text_parts)

columns = list(string.ascii_uppercase); [columns.append(f+s) for f in string.ascii_uppercase for s in string.ascii_uppercase]

def compute_quote_indices(start_letter: str, header_len: int) -> list[int]:
    start_idx = columns.index(start_letter) + 1; quote_indices = []; i = start_idx
    while i < header_len: quote_indices.append(i); i += 2
    return quote_indices
# (End of unchanged helper functions)

def verify_quotes_in_transcripts(csv_file_path: str, transcripts_dir: str, req_start_letter: str):
    """
    Processes a CSV file to fuzzy-verify its quotes against JSON transcripts.
    This version includes advanced handling for quotes with ellipses.
    """
    failed_quotes = []
    if not os.path.exists(csv_file_path):
        print(f"Warning: CSV file not found at {csv_file_path}")
        return []

    with open(csv_file_path, mode="r", newline="", encoding="utf-8") as file:
        reader = list(csv.reader(file, delimiter=";"))
        if not reader:
            return []

        header_len = max(len(r) for r in reader) if reader else 0
        quote_indices = compute_quote_indices(req_start_letter, header_len)

        for row_idx, row in enumerate(reader[1:], start=2):
            if not row: continue
            identifier = row[0].strip()
            if not identifier: continue

            transcript_path = os.path.join(transcripts_dir, f"{identifier}.json")
            normalized_transcript = ""

            # Handle missing or invalid transcript files
            if not os.path.exists(transcript_path):
                for q_idx in quote_indices:
                    if q_idx < len(row) and row[q_idx].strip():
                        failed_quotes.append((identifier, row_idx, columns[q_idx], "N/A", f"TRANSCRIPT_MISSING: {row[q_idx]}"))
                continue
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                full_transcript_text = extract_text_from_json(transcript_data)
                normalized_transcript = normalize_text(full_transcript_text)
            except Exception as e:
                # Catch invalid JSON or other reading errors
                for q_idx in quote_indices:
                    if q_idx < len(row) and row[q_idx].strip():
                        failed_quotes.append((identifier, row_idx, columns[q_idx], "N/A", f"ERROR_READING_JSON ({e.__class__.__name__}): {row[q_idx]}"))
                continue

            # Perform advanced fuzzy matching for each quote in the row
            for q_idx in quote_indices:
                if q_idx < len(row):
                    quote_raw = row[q_idx]
                    if not quote_raw or not quote_raw.strip(): continue

                    normalized_quote = normalize_text(quote_raw)
                    if not normalized_quote: continue
                        
                    # Use the new advanced scoring function
                    score = calculate_fuzzy_score(normalized_quote, normalized_transcript)

                    if score < SIMILARITY_THRESHOLD:
                        failed_quotes.append((identifier, row_idx, columns[q_idx], score, quote_raw))

    return failed_quotes

def print_failed_quotes_report(file_label: str, failed_quotes: list):
    """Generates and prints a formatted report for quotes that failed verification."""
    print("_" * 100)
    print(f"\nVerification of Quotes for: {file_label}\n")
    if not failed_quotes:
        print(f"Result: No discrepancies found. All quotes met the {SIMILARITY_THRESHOLD}% similarity threshold.")
    else:
        print(f"Result: Found {len(failed_quotes)} quotes that failed the {SIMILARITY_THRESHOLD}% similarity threshold.\n")
        headers = ["Identifier", "Row", "Column", "Match Score", "Quote"]
        # Prepare data for tabulate, formatting the score
        table_data = []
        for item in failed_quotes:
            score_str = f"{item[3]}%" if isinstance(item[3], int) else item[3]
            table_data.append([item[0], item[1], item[2], score_str, repr(item[4])])
        
        print(tabulate(table_data, headers=headers, tablefmt="simple"))


def main():
    base_dir = os.getcwd()
    results_dir = os.path.join(base_dir, "results")
    transcripts_dir = os.path.join(base_dir, "transcripts")

    single_file_path = os.path.join(results_dir, "single_results.csv")
    meta_file_path = os.path.join(results_dir, "meta_results.csv")

    failed_single = verify_quotes_in_transcripts(
        single_file_path, transcripts_dir, req_start_letter="B"
    )
    print_failed_quotes_report("single_results.csv", failed_single)

    failed_meta = verify_quotes_in_transcripts(
        meta_file_path, transcripts_dir, req_start_letter="E"
    )
    print_failed_quotes_report("meta_results.csv", failed_meta)


if __name__ == "__main__":
    main()