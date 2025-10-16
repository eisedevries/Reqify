# --- Match Percentage Calculation Logic ---
#
# This script compares two datasets to determine the agreement on whether a requirement
# was elicited during an interview. The match percentage is calculated as follows:
#
# 1. Total Comparisons:
#    - A comparison is made for each of the 12 requirements (R1 to R12) for every
#      'Interview ID' that exists in BOTH `dataset_llmrei.csv` and `dataset_new.csv`.
#    - Total Comparisons = (Number of Common Interview IDs) * 12
#
# 2. What Constitutes a "Match":
#    - For each comparison point (e.g., R3 for Interview ID 'xyz'), the script determines
#      the elicitation status in both files according to specific rules. A match occurs
#      if these two statuses are identical.
#    - There are two ways a match can happen:
#      a) POSITIVE MATCH: Both files agree that the requirement WAS ELICITED.
#         - `llmrei` status is 'Elicited'.
#         - `new` status is 'Elicited' (meaning at least one corresponding sub-column has text).
#      b) NEGATIVE MATCH: Both files agree that the requirement WAS NOT ELICITED.
#         - `llmrei` status is 'Not Elicited' (i.e., 'Partially Elicited', 'No', or empty).
#         - `new` status is 'Not Elicited' (meaning all corresponding sub-columns are 'No' or empty).
#
# 3. The Formula:
#    - Match Percentage = (Total Matches / Total Comparisons) * 100
#
# ---
# Date of last update: Monday, October 13, 2025
# Location: Netherlands
# ---

import csv
import os
from collections import defaultdict

def get_llmrei_status(value):
    """
    Determines if a requirement was elicited based on dataset_llmrei criteria.
    "Elicited" is considered elicited.
    "Partially Elicited", "No", or an empty cell are considered not elicited.
    """
    ENABLE_PARTIALLY_ELICITED = False
    if ENABLE_PARTIALLY_ELICITED:
        return value.strip().lower() in ["elicited", "partially elicited"]
    else:   
        return value.strip().lower() == "elicited"

def get_new_status(value):
    """
    Determines if a requirement was elicited based on dataset_new criteria.
    Any text is considered elicited.
    "No" or an empty cell are considered not elicited.
    """
    val_lower = value.strip().lower()
    return val_lower != "no" and val_lower != ""

def load_csv_to_dict(filepath, id_column_name):
    """
    Loads a CSV file into a dictionary, keyed by the specified ID column.
    It tries to open the file with 'latin-1' encoding to avoid common decoding errors.
    """
    data_dict = {}
    try:
        # Changed encoding from 'utf-8' to 'latin-1' to handle potential encoding issues.
        with open(filepath, mode='r', encoding='latin-1') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                interview_id = row.get(id_column_name)
                if interview_id:
                    data_dict[interview_id.strip()] = row
    except FileNotFoundError:
        print(f"Error: The file was not found at {filepath}")
        return None
    except Exception as e:
        print(f"An error occurred while reading {filepath}: {e}")
        return None
    return data_dict

def create_column_mapping():
    """
    Creates a mapping from the 'R' columns in dataset_llmrei to the corresponding
    'R.SA.*' and 'R.SK.*' columns in dataset_new.
    """
    # Columns from dataset_new.csv (F:AE)
    new_cols = [
        "R.SA.1", "R.SA.2", "R.SA.3", "R.SA.4.1", "R.SA.4.2", "R.SA.5.1",
        "R.SA.5.2", "R.SA.6.1", "R.SA.6.2", "R.SA.7", "R.SA.8", "R.SK.1",
        "R.SK.2", "R.SK.3", "R.SK.4", "R.SK.5", "R.SK.6", "R.SK.7", "R.SK.8",
        "R.SK.9", "R.SK.10.1", "R.SK.10.2", "R.SK.11.1", "R.SK.11.2",
        "R.SK.12.1", "R.SK.12.2"
    ]

    mapping = defaultdict(list)
    for new_col in new_cols:
        # Extracts the core number (e.g., '3' from 'R.SA.3', '11' from 'R.SK.11.1')
        parts = new_col.split('.')
        if len(parts) >= 3:
            number_part = parts[2]
            r_col_key = f"R{number_part}"
            mapping[r_col_key].append(new_col)

    return mapping

def main():
    """
    Main function to execute the comparison logic.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go one directory up from the script's location, then into 'ground_truth'
    ground_truth_folder = os.path.join(os.path.dirname(script_dir), 'ground_truth')

    # Define file paths
    llmrei_filepath = os.path.normpath(os.path.join(ground_truth_folder, 'dataset_llmrei.csv'))
    new_filepath = os.path.normpath(os.path.join(ground_truth_folder, 'dataset_new.csv'))
    
    id_column = "Interview ID"

    # Load data
    print("Loading data...")
    llmrei_data = load_csv_to_dict(llmrei_filepath, id_column)
    new_data = load_csv_to_dict(new_filepath, id_column)

    if llmrei_data is None or new_data is None:
        print("Could not proceed due to file loading errors.")
        return

    mapping = create_column_mapping()
    llmrei_cols = [f'R{i}' for i in range(1, 13)]

    # Initialize counters
    matches = 0
    total_comparisons = 0
    llmrei_elicited_count = 0 # Counter for llmrei elicitations
    new_elicited_count = 0    # Counter for new dataset elicitations

    print("Comparing datasets...")
    common_ids = set(llmrei_data.keys()) & set(new_data.keys())
    
    if not common_ids:
        print("No common 'Interview ID's found between the two files.")
        return

    for interview_id in sorted(common_ids):
        llmrei_row = llmrei_data[interview_id]
        new_row = new_data[interview_id]

        for r_col in llmrei_cols:
            total_comparisons += 1

            # 1. Determine and count elicitation status from dataset_llmrei
            llmrei_value = llmrei_row.get(r_col, "")
            llmrei_is_elicited = get_llmrei_status(llmrei_value)
            if llmrei_is_elicited:
                llmrei_elicited_count += 1

            # 2. Determine and count combined elicitation status from dataset_new
            new_is_elicited = False
            corresponding_new_cols = mapping.get(r_col, [])
            for new_col in corresponding_new_cols:
                new_value = new_row.get(new_col, "")
                if get_new_status(new_value):
                    new_is_elicited = True
                    break
            
            if new_is_elicited:
                new_elicited_count += 1

            # 3. Compare the statuses and count matches
            if llmrei_is_elicited == new_is_elicited:
                matches += 1

    # Print the results
    print("\n--- Comparison Results ---")
    if total_comparisons > 0:
        match_percentage = (matches / total_comparisons) * 100
        difference_percentage = 100 - match_percentage
        
        print(f"Total Interview IDs matched: {len(common_ids)}")
        print(f"Total individual requirement points compared: {total_comparisons}")
        
        print("\n--- Elicitation Counts ---")
        print(f"Total Elicitations in 'dataset_llmrei.csv': {llmrei_elicited_count}")
        print(f"Total Elicitations in 'dataset_new.csv':    {new_elicited_count}")

        print("\n--- Match Analysis ---")
        print(f"Total matches found: {matches}")
        print(f"Match percentage: {match_percentage:.2f}%")
        print(f"Difference percentage: {difference_percentage:.2f}%")
    else:
        print("No comparisons could be made.")

if __name__ == "__main__":
    main()

