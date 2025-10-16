import os
import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter

def read_jagged_csv_to_df(file_path, separator=';'):
    """
    Reads a CSV file that may have inconsistent numbers of columns per row.
    It pads shorter rows with None to create a rectangular structure,
    then returns a pandas DataFrame.

    Args:
        file_path (str): The path to the CSV file.
        separator (str): The delimiter used in the file.

    Returns:
        pd.DataFrame: A DataFrame created from the (now uniform) CSV data.
    """
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=separator)
            all_rows = list(reader)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return pd.DataFrame()

    if not all_rows:
        return pd.DataFrame() # Return an empty DataFrame if the file is empty

    # Find the length of the longest row to determine the DataFrame's width
    max_cols = max(len(row) for row in all_rows)

    # The first row is treated as the header
    header = all_rows[0]
    data_rows = all_rows[1:]

    # Pad the header if it's shorter than the longest row
    header_padding = max_cols - len(header)
    if header_padding > 0:
        header.extend([f'Unnamed_Col_{i}' for i in range(len(header), max_cols)])

    # Pad each data row to match the length of the longest row
    padded_data = []
    for row in data_rows:
        row_padding = max_cols - len(row)
        if row_padding > 0:
            row.extend([None] * row_padding) # Use None for missing values
        padded_data.append(row)

    # Create the DataFrame from the padded data and header
    df = pd.DataFrame(padded_data, columns=header)
    return df

# Location of the script
script_folder = os.path.dirname(os.path.abspath(__file__))

# CSVs are one level above in the results folder
results_folder = os.path.join(script_folder, "..", "results")
meta_file = os.path.join(results_folder, "meta_results.csv")
single_file = os.path.join(results_folder, "single_results.csv")

# Read the CSVs using the robust custom function
print("Reading CSV files...")
meta_df = read_jagged_csv_to_df(meta_file, separator=";")
single_df = read_jagged_csv_to_df(single_file, separator=";")
print("CSV files loaded successfully into pandas DataFrames.")


def get_requirement_lengths(df, start_col_index, step):
    """Calculates the average requirement length for each unique interview ID."""
    lengths_by_id = {}

    for _, row in df.iterrows():
        # Ensure the first column exists and get the interview ID
        if len(row) > 0:
            interview_id = row.iloc[0]
        else:
            continue
            
        if pd.isna(interview_id) or str(interview_id).strip() == "":
            continue

        total_chars = 0
        num_fields = 0
        col_index = start_col_index

        while col_index < len(row):
            cell = row.iloc[col_index]
            # Stop when we find the first empty requirement cell in the sequence
            if pd.isna(cell) or str(cell).strip() == "":
                break
            total_chars += len(str(cell))
            num_fields += 1
            col_index += step

        if num_fields > 0:
            avg_len = total_chars / num_fields
            lengths_by_id.setdefault(interview_id, []).append(avg_len)

    # Average the averages for IDs that appear in multiple rows (iterations)
    final_lengths = {iid: np.mean(vals) for iid, vals in lengths_by_id.items()}
    return list(final_lengths.values())

def build_distribution(lengths):
    """Bins lengths into groups of 5 and counts occurrences."""
    rounded = [int(round(l / 5) * 5) for l in lengths]
    counts = Counter(rounded)
    return counts

def plot_combined_bar_distribution(meta_lengths, single_lengths, title, filename):
    """Plots the distribution of requirement lengths as a combined bar chart."""
    meta_counts = build_distribution(meta_lengths)
    single_counts = build_distribution(single_lengths)

    # Combine all bins from both datasets to create a shared x-axis
    all_bins = sorted(set(meta_counts.keys()) | set(single_counts.keys()))

    meta_values = [meta_counts.get(b, 0) for b in all_bins]
    single_values = [single_counts.get(b, 0) for b in all_bins]

    x = np.arange(len(all_bins))
    bar_width = 0.4

    plt.figure(figsize=(12, 7))

    plt.bar(x - bar_width/2, meta_values, width=bar_width, color='blue', alpha=0.7, label='Meta Results')
    plt.bar(x + bar_width/2, single_values, width=bar_width, color='red', alpha=0.7, label='Single Results')

    plt.xticks(x, all_bins, rotation=45)
    plt.xlabel("Average Characters per Requirement (Binned)")
    plt.ylabel("Number of Unique Interview IDs")
    plt.title(title)
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()

    out_path = os.path.join(script_folder, filename)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Saved combined bar chart to {out_path}")
    plt.close()

# --- Main execution ---
# Get data (Column E is index 4 for meta, Column B is index 1 for single)
meta_lengths = get_requirement_lengths(meta_df, 4, 2)
single_lengths = get_requirement_lengths(single_df, 1, 2)

# Plot both distributions as a combined bar chart
plot_combined_bar_distribution(
    meta_lengths,
    single_lengths,
    "Distribution of Average Requirement Lengths per Interview",
    "distribution_graph_average.png"
)