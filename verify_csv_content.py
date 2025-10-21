# ====================================================================================
# This script verifies and validates the content of single_results.csv and meta_results.csv.
# It checks whether specific cells in each row meet defined quality rules for:
#   - Role content
#   - Analysis length
#   - Requirement presence
#   - Quote presence
# It also detects and reports mismatches between requirement and quote cells.
#
# CHECK CRITERIA FOR single_results.csv AND meta_results.csv
#
# Identifier:
#   Column A
#
# Iterations:
#   Column B for meta files means iteration count field
#   The script counts occurrences per identifier
#
# Prompt Check only for meta_results.csv column C:
#   Must contain the text "system role" case insensitive
#
# Analysis length column D:
#   Must contain more than 20 characters after normalization
#   If the cell equals "N/A" case insensitive then it is ignored
#
# Req length and Quote length pairs:
#   For single_results.csv pairs start at B C then E F then G H and so on
#   For meta_results.csv pairs start at E F then G H and so on
#   A requirement cell is valid if it has any value after normalization
#   A quote cell is valid if it has any value after normalization
#
# Strict missing quote rule:
#   If a requirement has any value and its paired quote is empty
#   then this is a failure and it is listed in Quote differences
#   Tail emptiness does not override this rule
#
# Tail allowance for empty sequences:
#   If a requirement cell is empty and all later requirement cells are empty
#   then requirements pass for that row
#   If a quote cell is empty and its paired requirement is empty and all later quote cells are empty
#   then quotes pass for that row
#
# At the end, the script:
#   - Prints a summary table for each file
#   - Shows the total number of requirement and quote entries
#   - Displays the difference between them
#   - Lists the exact cells where quotes are missing
# ====================================================================================


import csv
import os
import string
import html
from tabulate import tabulate

def main():
    def normalize_cell(cell: str) -> str:
        if not cell:
            return ""
        s = html.unescape(cell)
        s = s.replace("\r", "").replace("\n", "").replace("\u00A0", " ").strip()
        quote_pairs = [('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"), ("«", "»")]
        changed = True
        while changed and len(s) >= 2:
            changed = False
            for left, right in quote_pairs:
                if s.startswith(left) and s.endswith(right):
                    s = s[1:-1].strip()
                    changed = True
        return s

    # Build Excel style column letters
    columns = list(string.ascii_uppercase)
    for first in string.ascii_uppercase:
        for second in string.ascii_uppercase:
            columns.append(first + second)

    def idx_from_letter(letter: str) -> int:
        return columns.index(letter)

    def compute_indices(start_letter: str, header_len: int):
        """Return paired requirement and quote indices starting at start_letter and start_letter+1 stepping by 2."""
        start_idx = idx_from_letter(start_letter)
        max_idx = header_len - 1
        req_indices = []
        quote_indices = []
        i = start_idx
        while i + 1 <= max_idx:
            req_indices.append(i)
            quote_indices.append(i + 1)
            i += 2
        return req_indices, quote_indices

    def process_csv(file_path: str, check_role: bool, req_start_letter: str):
        data = {}
        total_requirements = 0
        total_quotes = 0
        failed_cells = []
        missing_quotes = []

        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = list(csv.reader(file, delimiter=";"))
            if not reader:
                return data, 0, 0, [], []

            header_len = max(len(r) for r in reader)
            req_indices, quote_indices = compute_indices(req_start_letter, header_len)

            for row_idx, row in enumerate(reader[1:], start=2):
                identifier = row[0].strip() if len(row) > 0 else ""
                iteration = row[1].strip() if len(row) > 1 else ""

                role_result = "CHECK" if check_role else ""
                analysis_result = "CHECK"
                req_result = "CHECK"
                quote_result = "CHECK"

                if identifier not in data:
                    data[identifier] = {
                        "count": 0,
                        "role_check": "",
                        "analysis_length": "",
                        "requirement_check": "",
                        "quote_check": ""
                    }

                if identifier and iteration:
                    data[identifier]["count"] += 1

                # System Prompt Check for meta only at column C
                if check_role:
                    c_val = row[2] if len(row) > 2 else ""
                    if "system role" not in normalize_cell(c_val).lower():
                        role_result = "FAIL"
                        failed_cells.append(("System Prompt Check", identifier, row_idx, c_val))

                # Analysis length at column D
                d_val = row[3] if len(row) > 3 else ""
                d_clean = normalize_cell(d_val)
                if d_clean.lower() != "n/a" and len(d_clean) <= 20:
                    analysis_result = "FAIL"
                    failed_cells.append(("Analysis length", identifier, row_idx, d_val))

                # Walk paired requirement and quote indices
                requirement_ok = True
                requirement_empty_tail = False
                quote_ok = True
                quote_empty_tail = False

                for pair_i in range(len(req_indices)):
                    r_idx = req_indices[pair_i]
                    q_idx = quote_indices[pair_i]

                    req_raw = row[r_idx] if r_idx < len(row) else ""
                    quote_raw = row[q_idx] if q_idx < len(row) else ""

                    req_val = normalize_cell(req_raw)
                    quote_val = normalize_cell(quote_raw)

                    if req_val:
                        total_requirements += 1
                    if quote_val:
                        total_quotes += 1

                    # Strict missing quote rule
                    if req_val and not quote_val:
                        missing_quotes.append((
                            identifier,
                            row_idx,
                            columns[r_idx],
                            columns[q_idx],
                            req_val
                        ))
                        quote_ok = False
                        failed_cells.append(("Quote length", identifier, row_idx, quote_raw))
                        # Do not break here so we can catch multiple per row if present
                        continue

                    # Requirement empty handling when no value
                    if not req_val:
                        later_req_empty = True
                        for later_r in req_indices[pair_i:]:
                            cell = normalize_cell(row[later_r]) if later_r < len(row) else ""
                            if cell:
                                later_req_empty = False
                                break
                        if later_req_empty:
                            requirement_empty_tail = True
                            break
                        else:
                            requirement_ok = False
                            failed_cells.append(("Req length", identifier, row_idx, req_raw))
                            break

                    # Quote empty handling only when requirement is also empty
                    if not quote_val and not req_val:
                        later_quote_empty = True
                        for later_q in quote_indices[pair_i:]:
                            cell = normalize_cell(row[later_q]) if later_q < len(row) else ""
                            if cell:
                                later_quote_empty = False
                                break
                        if later_quote_empty:
                            quote_empty_tail = True
                            break
                        else:
                            quote_ok = False
                            failed_cells.append(("Quote length", identifier, row_idx, quote_raw))
                            break

                req_result = "CHECK" if (requirement_ok or requirement_empty_tail) else "FAIL"
                # Note: quote_result already set to FAIL if any strict missing quote happened
                if quote_ok or quote_empty_tail:
                    # keep existing state unless already FAIL
                    if quote_result != "FAIL":
                        quote_result = "CHECK"
                else:
                    quote_result = "FAIL"

                data[identifier]["role_check"] = role_result
                data[identifier]["analysis_length"] = analysis_result
                data[identifier]["requirement_check"] = req_result
                data[identifier]["quote_check"] = quote_result

        return data, total_requirements, total_quotes, failed_cells, missing_quotes

    def print_missing_quotes(label, missing_quotes):
        if missing_quotes:
            print(f"\nQuote differences {label}:")
            for identifier, row_num, req_col, quote_col, req_val in missing_quotes:
                print(f" - Identifier: {identifier} | Row: {row_num} | Req {req_col} to Quote {quote_col} missing | Req value: {repr(req_val)}")
        else:
            print(f"\nQuote differences {label}: None")

    # Paths
    base = os.getcwd()
    single_file_path = os.path.join(base, "results", "single_results.csv")
    meta_file_path = os.path.join(base, "results", "meta_results.csv")

    # Single results uses requirement pairs starting at B C and no System Prompt Check
    # CHANGE FIXED DATA LENGTH HERE
    single_data, single_total_requirements, single_total_quotes, single_failed, single_missing_quotes = process_csv(
        single_file_path, check_role=False, req_start_letter="B"
    )

    single_table = []
    for identifier, info in single_data.items():
        single_table.append([
            identifier,
            info['count'],
            info['analysis_length'],
            info['requirement_check'],
            info['quote_check']
        ])

    print("\n")
    print("<>" * 50)
    print("              NOTE: read the top of this script for details on the checks performed.")
    print("<>" * 50)

    print("\n\nCheck for single_results.csv")
    print(tabulate(single_table, headers=["Identifier", "Iterations", "Analysis length", "Req length", "Quote length"], tablefmt="simple"))
    print(f"\nTotal unique identifiers: {len(single_data)}")
    print(f"Total requirement entries: {single_total_requirements}")
    print(f"Total quote entries: {single_total_quotes}")
    single_diff = single_total_requirements - single_total_quotes
    print(f"Difference between requirement and quote entries: {single_diff}")

    if single_failed:
        print("\nFailed Cell Contents single_results.csv:")
        for check_type, identifier, row_num, value in single_failed:
            print(f" - {check_type} | Identifier: {identifier} | Row: {row_num} | Value: {repr(value)}")

    print_missing_quotes("single_results.csv", single_missing_quotes)

    # Meta results uses requirement pairs starting at E F and System Prompt Check enabled
    # CHANGE FIXED DATA LENGTH HERE
    meta_data, meta_total_requirements, meta_total_quotes, meta_failed, meta_missing_quotes = process_csv(
        meta_file_path, check_role=True, req_start_letter="E"
    )

    meta_table = []
    for identifier, info in meta_data.items():
        meta_table.append([
            identifier,
            info['count'],
            info['role_check'],
            info['analysis_length'],
            info['requirement_check'],
            info['quote_check']
        ])

    print("_" * 100)
    print("\n\nCheck for meta_results.csv")
    print(tabulate(meta_table, headers=["Identifier", "Iterations", "System Prompt Check", "Analysis length", "Req length", "Quote length"], tablefmt="simple"))
    print(f"\nTotal unique identifiers: {len(meta_data)}")
    print(f"Total requirement entries: {meta_total_requirements}")
    print(f"Total quote entries: {meta_total_quotes}")
    meta_diff = meta_total_requirements - meta_total_quotes
    print(f"Difference between requirement and quote entries: {meta_diff}")

    if meta_failed:
        print("\nFailed Cell Contents meta_results.csv:")
        for check_type, identifier, row_num, value in meta_failed:
            print(f" - {check_type} | Identifier: {identifier} | Row: {row_num} | Value: {repr(value)}")

    print_missing_quotes("meta_results.csv", meta_missing_quotes)


if __name__ == "__main__":
    main()