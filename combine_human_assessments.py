import os
import csv
from collections import Counter
import math

# --- Configuration ---
RESULTS_DIR = 'results'
RESEARCHER_PREFIX = 'researcher'

def load_and_clean_csv(file_path: str, target_filename: str):
    """
    Robustly loads a CSV file. It automatically detects the delimiter,
    handles 'latin-1' encoding, cleans a Byte Order Mark (BOM), and returns
    the data as a dictionary keyed appropriately.
    
    Returns:
        (dict): A dictionary of the data, e.g. { (key1, key2): {row_data} }
        (list): A list of the cleaned header column names in their original order.
    """
    data_map = {}
    
    # Determine key columns based on the target filename
    is_meta_human = 'meta_human' in target_filename
    key_cols_names = ['Interview ID', 'Scenario']
    if is_meta_human:
        key_cols_names.append('Iteration') # Add 'Iteration' for meta_human

    try:
        with open(file_path, mode='r', encoding='latin-1', newline='') as infile:
            first_line = infile.readline()
            infile.seek(0)
            if not first_line:
                return {}, [] # File is empty

            delimiter = ';' if ';' in first_line else ','
            reader = csv.reader(infile, delimiter=delimiter)
            
            header = next(reader)
            header[0] = header[0].lstrip('\ufeff')
            clean_header = [h.strip() for h in header] # This is the ordered list

            # Ensure essential key columns exist
            key_col_indices = {col: clean_header.index(col) for col in key_cols_names}

            for row in reader:
                if len(row) < len(clean_header):
                    continue
                
                row_dict = {clean_header[i]: value.strip() for i, value in enumerate(row)}
                
                # Build the dynamic key
                key_parts = []
                for col in key_cols_names:
                    key_parts.append(row_dict[col])
                key = tuple(key_parts)
                
                data_map[key] = row_dict
                
    except (FileNotFoundError, StopIteration, ValueError, IndexError, KeyError) as e:
        print(f"Warning: Could not read or process {file_path}. Error: {e}. Required columns: {key_cols_names}")
        return {}, [] # Return empty dict and empty list
        
    return data_map, clean_header # Return both

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

def create_combined_analysis(target_filename: str, output_filename: str):
    """
    Finds all researcher analysis files (matching target_filename), 
    aggregates them based on a two-thirds majority agreement, 
    and writes a combined CSV file (to output_filename).
    """
    print(f"\n--- Starting analysis for: {target_filename} ---")

    # --- 1. Find all researcher analysis files ---
    researcher_files = []
    if not os.path.isdir(RESULTS_DIR):
        print(f"Error: Directory '{RESULTS_DIR}' not found. Please run this script from the parent directory.")
        return

    for dir_name in os.listdir(RESULTS_DIR):
        if dir_name.startswith(RESEARCHER_PREFIX):
            file_path = os.path.join(RESULTS_DIR, dir_name, target_filename) 
            if os.path.isfile(file_path):
                researcher_files.append(file_path)

    # --- 2. Validate the number of researcher files ---
    num_researchers = len(researcher_files)
    if num_researchers < 3:
        print(f"Error: A two-thirds majority analysis requires at least 3 researcher files.")
        print(f"Only found {num_researchers} file(s) named '{target_filename}'. Aborting this analysis.")
        return

    print(f"Found {num_researchers} researcher files to process:")
    for f in researcher_files:
        print(f" - {f}")
    print("-" * 40)

    # --- 3. Load data and capture master header order ---
    all_data = {}
    all_headers_set = set() # Use a set to collect all unique headers
    all_keys = set()
    master_header_list = [] # This will hold the order from the first *valid* file

    for file_path in researcher_files:
        data_map, header_list = load_and_clean_csv(file_path, target_filename)
        
        # If we don't have a master list yet AND this file provided one
        if not master_header_list and header_list: 
            master_header_list = header_list
            
        all_data[file_path] = data_map
        all_headers_set.update(header_list) # Add all headers from this file to the set
        all_keys.update(data_map.keys())

    # --- 4. Determine agreement threshold and final headers ---
    agreement_threshold = math.ceil((num_researchers * 2) / 3)
    
    print(f"Using a 2/3 majority rule.")
    print(f"Agreement threshold set to {agreement_threshold} out of {num_researchers} researchers.\n")
    
    if not all_keys:
        print(f"Error: No data found in any of the '{target_filename}' files.")
        return

    # Define key columns (needed for fallback and row processing)
    is_meta_human = 'meta_human' in target_filename
    key_cols = ['Interview ID', 'Scenario']
    if is_meta_human:
        key_cols.append('Iteration')

    # --- Header Ordering ---
    if not master_header_list:
        # Fallback in case all files were empty or failed to load headers
        print("Warning: Could not determine master header order. Falling back to sorted order.")
        final_ordered_headers = sorted(
            list(all_headers_set), 
            key=lambda x: (x not in key_cols, key_cols.index(x) if x in key_cols else x)
        )
    else:
        # Normal case: Start with the master list
        final_ordered_headers = list(master_header_list)
        # Add any headers that were in other files but not the first one
        for header in all_headers_set:
            if header not in final_ordered_headers:
                final_ordered_headers.append(header)
    
    # --- 5. Process and aggregate data ---
    mismatches_count = 0
    removed_entries_count = 0
    total_entries_count = 0
    combined_rows = []

    # --- Define SORTING KEY FOR ROWS ---
    # The key tuple is (Interview ID, Scenario) or (Interview ID, Scenario, Iteration)
    # key[0]=Interview ID, key[1]=Scenario, key[2]=Iteration
    
    if is_meta_human:
        # [FIXED] Sort by Scenario (key[1]), then Interview ID (key[0]), then Iteration (key[2])
        sort_key_func = lambda key: (key[1], key[0], key[2])
    else:
        # Sort by Scenario (key[1]), then Interview ID (key[0])
        sort_key_func = lambda key: (key[1], key[0])
    
    sorted_keys = sorted(list(all_keys), key=sort_key_func)
    # --- [END ROW SORTING] ---

    for key in sorted_keys: 
        # Dynamically build the new row's key columns
        new_row = {}
        for i, col_name in enumerate(key_cols):
            new_row[col_name] = key[i]
        
        for header in final_ordered_headers: # Use the new final_ordered_headers
            if header in key_cols: # Skip key columns, as they are already set
                continue

            cell_values = []
            for f in researcher_files:
                researcher_data = all_data.get(f, {})
                row = researcher_data.get(key)
                value = row.get(header, '') if row else ''
                cell_values.append(normalize_cell_value(value))
            
            for val in cell_values:
                if val:
                    total_entries_count += len(val.split(','))

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
                for researcher_val in cell_values:
                    researcher_set = set(researcher_val.split(',')) if researcher_val else set()
                    removed_entries_count += len(researcher_set)
        
        combined_rows.append(new_row)

    # --- 6. Write the combined data to a new CSV file ---
    output_path = os.path.join(RESULTS_DIR, output_filename) 
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
            # Use final_ordered_headers for the fieldnames
            writer = csv.DictWriter(outfile, fieldnames=final_ordered_headers) 
            writer.writeheader()
            writer.writerows(combined_rows)
    except IOError as e:
        print(f"\nError: Could not write to output file '{output_path}'. Details: {e}")
        return

    # --- 7. Print final summary ---
    kept_entries_count = total_entries_count - removed_entries_count
    
    print("Processing complete!\n")
    print("="*60)
    print(f"--- Summary for {output_filename} ---")
    print(f"Combined analysis file created at: {output_path}")
    print(f"Total mismatches (cells with no majority): {mismatches_count}")
    print(f"Total individual entries removed (due to non-consensus): {removed_entries_count}")
    print(f"Total individual entries kept (consensus): {kept_entries_count}")
    print("="*60)

def main():
    # --- Run for single_human ---
    create_combined_analysis(
        target_filename='analysis_single_human.csv',
        output_filename='combined_analysis_single_human.csv'
    )
    
    # --- Run for meta_human ---
    create_combined_analysis(
        target_filename='analysis_meta_human.csv',
        output_filename='combined_analysis_meta_human.csv'
    )

if __name__ == "__main__":
    main()