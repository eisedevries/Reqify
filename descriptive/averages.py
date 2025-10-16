import os
import csv
import pandas as pd
import numpy as np

def read_jagged_csv_to_df(file_path, separator=';'):
    """
    Reads a CSV file with a potentially inconsistent number of columns per row,
    pads shorter rows with None to create a uniform structure, and returns
    a pandas DataFrame.

    Args:
        file_path (str): The path to the CSV file.
        separator (str): The delimiter used in the file.

    Returns:
        pd.DataFrame: A DataFrame created from the CSV data.
    """
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=separator)
            all_rows = list(reader)
    except FileNotFoundError:
        print(f"Error: The file was not found at {file_path}")
        return pd.DataFrame()

    if not all_rows:
        return pd.DataFrame()

    max_cols = max(len(row) for row in all_rows)
    header = all_rows[0]
    data_rows = all_rows[1:]
    header_padding = max_cols - len(header)
    if header_padding > 0:
        header.extend([f'Unnamed_Col_{i}' for i in range(len(header), max_cols)])

    padded_data = []
    for row in data_rows:
        row_padding = max_cols - len(row)
        if row_padding > 0:
            row.extend([None] * row_padding)
        padded_data.append(row)

    return pd.DataFrame(padded_data, columns=header)

def get_single_prompt_data(df, start_col_index, step):
    """
    Extracts all requirement texts from the single-prompt DataFrame.

    Returns:
        list: A list of all requirement texts found.
    """
    requirements = []
    if df.empty:
        return requirements

    for _, row in df.iterrows():
        col_index = start_col_index
        while col_index < len(row):
            cell = row.iloc[col_index]
            if pd.isna(cell) or str(cell).strip() == "":
                break
            requirements.append(str(cell))
            col_index += step
    return requirements

def get_meta_prompt_data(df, start_col_index, step):
    """
    Extracts requirements and their corresponding iteration numbers from the
    meta-prompt DataFrame.

    Returns:
        tuple: A tuple containing:
            - list: All requirement texts.
            - dict: A dictionary mapping each iteration to a list of character lengths.
    """
    requirements = []
    lengths_per_iteration = {}
    if df.empty:
        return requirements, lengths_per_iteration

    for _, row in df.iterrows():
        iteration = "Unknown"
        if len(row) > 1 and not pd.isna(row.iloc[1]):
            try:
                iteration = int(float(row.iloc[1]))
            except (ValueError, TypeError):
                iteration = str(row.iloc[1])

        col_index = start_col_index
        while col_index < len(row):
            cell = row.iloc[col_index]
            if pd.isna(cell) or str(cell).strip() == "":
                break

            req_text = str(cell)
            requirements.append(req_text)

            if iteration not in lengths_per_iteration:
                lengths_per_iteration[iteration] = []
            lengths_per_iteration[iteration].append(len(req_text))

            col_index += step

    return requirements, lengths_per_iteration

# --- Main execution ---
try:
    script_folder = os.path.dirname(os.path.abspath(__file__))
    results_folder = os.path.join(script_folder, "..", "results")
except NameError:
    results_folder = "results"
    print("Warning: Could not determine script path. Assuming 'results' folder is in the current directory.")

meta_file = os.path.join(results_folder, "meta_results.csv")
single_file = os.path.join(results_folder, "single_results.csv")

# Read CSVs
print("Reading CSV files...")
meta_df = read_jagged_csv_to_df(meta_file, separator=";")
single_df = read_jagged_csv_to_df(single_file, separator=";")
print("CSV files loaded.")

# --- Process Data ---
single_requirements = get_single_prompt_data(single_df, start_col_index=1, step=2)
meta_requirements, meta_lengths_per_iter = get_meta_prompt_data(meta_df, start_col_index=4, step=2)

# --- Perform Calculations ---
# Single-prompt
num_single = len(single_requirements)
if num_single > 1: # Kurtosis needs more than 1 data point
    single_char_lengths = pd.Series([len(req) for req in single_requirements])
    single_word_counts = pd.Series([len(req.split()) for req in single_requirements])
    avg_char_single = single_char_lengths.mean()
    std_char_single = single_char_lengths.std()
    kurt_char_single = single_char_lengths.kurtosis()
    avg_word_single = single_word_counts.mean()
    std_word_single = single_word_counts.std()
    kurt_word_single = single_word_counts.kurtosis()
else:
    avg_char_single, std_char_single, kurt_char_single, avg_word_single, std_word_single, kurt_word_single = 0, 0, 0, 0, 0, 0

# Meta-prompting
num_meta = len(meta_requirements)
if num_meta > 1: # Kurtosis needs more than 1 data point
    meta_char_lengths = pd.Series([len(req) for req in meta_requirements])
    meta_word_counts = pd.Series([len(req.split()) for req in meta_requirements])
    avg_char_meta = meta_char_lengths.mean()
    std_char_meta = meta_char_lengths.std()
    kurt_char_meta = meta_char_lengths.kurtosis()
    avg_word_meta = meta_word_counts.mean()
    std_word_meta = meta_word_counts.std()
    kurt_word_meta = meta_word_counts.kurtosis()
else:
    avg_char_meta, std_char_meta, kurt_char_meta, avg_word_meta, std_word_meta, kurt_word_meta = 0, 0, 0, 0, 0, 0

# --- Display Summary ---
print("\n" + "--- Text length summary ---")
print(f"Number of single-prompt requirements measured: {num_single}")
print(f"Number of meta-prompting requirements measured: {num_meta}")
print("\n--- Single-Prompt Stats ---")
print(f"Characters: Avg={avg_char_single:.1f}, Std={std_char_single:.1f}, Kurtosis={kurt_char_single:.4f}")
print(f"Words:      Avg={avg_word_single:.1f}, Std={std_word_single:.1f}, Kurtosis={kurt_word_single:.4f}")
print("\n--- Meta-Prompting Stats ---")
print(f"Characters: Avg={avg_char_meta:.1f}, Std={std_char_meta:.1f}, Kurtosis={kurt_char_meta:.4f}")
print(f"Words:      Avg={avg_word_meta:.1f}, Std={std_word_meta:.1f}, Kurtosis={kurt_word_meta:.4f}")


# Display meta averages per iteration
if meta_lengths_per_iter:
    print("\n--- Meta-prompting stats per iteration ---")
    sorted_iterations = sorted(meta_lengths_per_iter.keys())
    for iteration in sorted_iterations:
        lengths = pd.Series(meta_lengths_per_iter[iteration])
        num_reqs = len(lengths)
        if num_reqs > 1:
            avg_len = lengths.mean()
            std_len = lengths.std()
            kurt_len = lengths.kurtosis()
            print(f"Iteration {iteration} ({num_reqs} reqs): Avg={avg_len:.1f}, Std={std_len:.1f}, Kurtosis={kurt_len:.4f}")
        else:
            avg_len = lengths.mean() if num_reqs > 0 else 0
            print(f"Iteration {iteration} ({num_reqs} reqs): Avg={avg_len:.1f} (not enough data for Std/Kurtosis)")