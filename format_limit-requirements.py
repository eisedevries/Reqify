import csv
import os
import sys

def trim_csv_file(file_path: str, last_column_to_keep: str):
    """
    Reads a CSV file, removes all columns after a specified column header,
    and overwrites the original file with the trimmed data.

    Args:
        file_path (str): The full path to the CSV file.
        last_column_to_keep (str): The header name of the last column to retain.
    """
    # Use the same encoding and delimiter as in your example script
    encoding = 'utf-8'
    delimiter = ';'

    # --- Step 1: Check if the file exists before proceeding ---
    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'. Skipping.")
        return

    print(f"Processing file: {os.path.basename(file_path)}...")

    # --- Step 2: Read the entire file into memory ---
    try:
        with open(file_path, mode='r', newline='', encoding=encoding) as file:
            reader = csv.reader(file, delimiter=delimiter)
            all_rows = list(reader)
    except Exception as e:
        print(f"Error reading '{file_path}': {e}")
        return

    if not all_rows:
        print("File is empty. No changes made.")
        return

    # --- Step 3: Find the index of the last column to keep ---
    header = all_rows[0]
    try:
        # Find the column index (0-based) of the target header
        cut_off_index = header.index(last_column_to_keep)
    except ValueError:
        print(f"Error: Column '{last_column_to_keep}' not found in the header of '{file_path}'.")
        print("No changes have been made.")
        return

    # --- Step 4: Create the new, trimmed dataset ---
    # The new number of columns will be the index + 1
    num_cols_to_keep = cut_off_index + 1
    
    # Ensure the new header has the correct number of columns
    original_header_length = len(header)
    if original_header_length <= num_cols_to_keep:
        print(f"No columns to remove. The file already has {original_header_length} or fewer columns.")
        return

    trimmed_data = []
    for row in all_rows:
        # Slice each row to keep columns from the beginning up to our target
        trimmed_row = row[:num_cols_to_keep]
        trimmed_data.append(trimmed_row)

    # --- Step 5: Write the trimmed data back to the original file ---
    try:
        with open(file_path, mode='w', newline='', encoding=encoding) as file:
            writer = csv.writer(file, delimiter=delimiter)
            writer.writerows(trimmed_data)
        
        cols_removed = original_header_length - num_cols_to_keep
        print(f"Success! Removed {cols_removed} columns after '{last_column_to_keep}'.")
        print(f"File '{os.path.basename(file_path)}' has been updated.")

    except Exception as e:
        print(f"Error writing back to '{file_path}': {e}")
        print("The original file may not have been modified.")



def main():
    """Main entry point for running the script directly or via import."""
    TARGET_COLUMN = "R30_QT"

    try:
        base_directory = os.getcwd()
        results_directory = os.path.join(base_directory, "results")
        single_file_path = os.path.join(results_directory, "single_results.csv")
        meta_file_path = os.path.join(results_directory, "meta_results.csv")

        trim_csv_file(single_file_path, TARGET_COLUMN)
        print("-" * 50)
        trim_csv_file(meta_file_path, TARGET_COLUMN)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()