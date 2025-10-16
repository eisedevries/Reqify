import os
import csv
from collections import Counter
import math

# --- Configuration ---
RESULTS_DIR = 'results'
TARGET_FILENAME = 'analysis_single_human.csv'
OUTPUT_FILENAME = 'combined_analysis_single_human.csv'
RESEARCHER_PREFIX = 'researcher'

def load_and_clean_csv(file_path: str) -> dict:
    """
    Robustly loads a CSV file. It automatically detects the delimiter,
    handles 'latin-1' encoding, cleans a Byte Order Mark (BOM), and returns
    the data as a dictionary keyed by (Interview ID, Scenario).
    """
    data_map = {}
    try:
        with open(file_path, mode='r', encoding='latin-1', newline='') as infile:
            first_line = infile.readline()
            infile.seek(0)
            if not first_line:
                return {} # File is empty

            delimiter = ';' if ';' in first_line else ','
            reader = csv.reader(infile, delimiter=delimiter)
            
            header = next(reader)
            header[0] = header[0].lstrip('\ufeff')
            clean_header = [h.strip() for h in header]

            # Ensure essential columns exist
            id_col_index = clean_header.index('Interview ID')
            scenario_col_index = clean_header.index('Scenario')

            for row in reader:
                if len(row) < len(clean_header):
                    continue
                
                row_dict = {clean_header[i]: value.strip() for i, value in enumerate(row)}
                key = (row_dict['Interview ID'], row_dict['Scenario'])
                data_map[key] = row_dict
                
    except (FileNotFoundError, StopIteration, ValueError) as e:
        print(f"Warning: Could not read or process {file_path}. Error: {e}")
        return {}
        
    return data_map

def normalize_cell_value(value: str) -> str:
    """
    Normalizes a comma-separated string value for consistent comparison.
    Example: "B33, A12 " -> "A12,B33"
    """
    if not value or not value.strip():
        return ""
    # Split, strip whitespace from each part, filter out empty parts, sort, and rejoin.
    parts = sorted([part.strip() for part in value.split(',') if part.strip()])
    return ",".join(parts)

def create_combined_analysis():
    """
    Finds all researcher analysis files, aggregates them based on a two-thirds
    majority agreement, and writes a combined CSV file.
    """
    print("Starting analysis combination process...\n")

    # --- 1. Find all researcher analysis files ---
    researcher_files = []
    if not os.path.isdir(RESULTS_DIR):
        print(f"Error: Directory '{RESULTS_DIR}' not found. Please run this script from the parent directory.")
        return

    for dir_name in os.listdir(RESULTS_DIR):
        if dir_name.startswith(RESEARCHER_PREFIX):
            file_path = os.path.join(RESULTS_DIR, dir_name, TARGET_FILENAME)
            if os.path.isfile(file_path):
                researcher_files.append(file_path)

    # --- 2. Validate the number of researcher files ---
    num_researchers = len(researcher_files)
    if num_researchers < 3:
        print(f"Error: A two-thirds majority analysis requires at least 3 researcher files.")
        print(f"Only found {num_researchers} file(s). Aborting process.")
        return

    print(f"Found {num_researchers} researcher files to process:")
    for f in researcher_files:
        print(f" - {f}")
    print("-" * 40)

    # --- 3. Load data from all found files ---
    all_data = {file_path: load_and_clean_csv(file_path) for file_path in researcher_files}
    
    # --- 4. [UPDATED] Determine agreement threshold and gather all keys/headers ---
    # This now correctly calculates the threshold for a two-thirds majority.
    agreement_threshold = math.ceil((num_researchers * 2) / 3)
    
    print(f"Using a 2/3 majority rule.")
    print(f"Agreement threshold set to {agreement_threshold} out of {num_researchers} researchers.\n")
    
    all_keys = set()
    all_headers = set()
    key_cols = ['Interview ID', 'Scenario']

    for data_map in all_data.values():
        all_keys.update(data_map.keys())
        if data_map:
            first_row = next(iter(data_map.values()))
            all_headers.update(first_row.keys())

    if not all_keys:
        print("Error: No data found in any of the analysis files.")
        return

    sorted_headers = sorted(list(all_headers), key=lambda x: (x not in key_cols, x))

    # --- 5. Process and aggregate data ---
    mismatches_count = 0
    removed_entries_count = 0
    combined_rows = []

    for key in sorted(list(all_keys)):
        new_row = {'Interview ID': key[0], 'Scenario': key[1]}
        
        for header in sorted_headers:
            if header in key_cols:
                continue

            cell_values = []
            for f in researcher_files:
                researcher_data = all_data.get(f, {})
                row = researcher_data.get(key)
                value = row.get(header, '') if row else ''
                cell_values.append(normalize_cell_value(value))

            value_counts = Counter(cell_values)
            most_common = value_counts.most_common(1)
            
            consensus_value, count = most_common[0] if most_common else ("", 0)

            if count >= agreement_threshold:
                new_row[header] = consensus_value
                consensus_set = set(consensus_value.split(',')) if consensus_value else set()
                for researcher_val in cell_values:
                    researcher_set = set(researcher_val.split(',')) if researcher_val else set()
                    removed = researcher_set - consensus_set
                    removed_entries_count += len(removed)
            else:
                new_row[header] = ""
                mismatches_count += 1
        
        combined_rows.append(new_row)

    # --- 6. Write the combined data to a new CSV file ---
    output_path = os.path.join(RESULTS_DIR, OUTPUT_FILENAME)
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=sorted_headers)
            writer.writeheader()
            writer.writerows(combined_rows)
    except IOError as e:
        print(f"\nError: Could not write to output file '{output_path}'. Details: {e}")
        return

    # --- 7. Print final summary ---
    print("Processing complete!\n")
    print("="*60)
    print("--- Summary ---")
    print(f"Combined analysis file created at: {output_path}")
    print(f"Total mismatches (cells with no majority): {mismatches_count}")
    print(f"Total individual entries removed (due to non-consensus): {removed_entries_count}")
    print("="*60)


if __name__ == "__main__":
    create_combined_analysis()