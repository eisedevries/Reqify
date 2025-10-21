import os
import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

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

# Read CSVs using the robust custom function
print("Reading CSV files...")
meta_df = read_jagged_csv_to_df(meta_file, separator=";")
single_df = read_jagged_csv_to_df(single_file, separator=";")
print("CSV files loaded successfully into pandas DataFrames.")

def get_lengths_and_iterations_grouped_by_index(df, start_col_index, step):
    """
    Returns dict: {requirement_index: [(length, iteration_value)]}
    Iteration value is from column B (index 1).
    """
    grouped = {}
    if df.empty:
        return grouped
        
    for _, row in df.iterrows():
        # Safely get iteration value from the second column
        iteration = ""
        if len(row) > 1 and not pd.isna(row.iloc[1]):
            try:
                # Ensure iteration can be converted to int for consistent labeling
                iteration = int(float(row.iloc[1]))
            except (ValueError, TypeError):
                iteration = row.iloc[1]

        col_index = start_col_index
        req_index = 1
        while col_index < len(row):
            cell = row.iloc[col_index]
            if pd.isna(cell) or str(cell).strip() == "":
                break # Stop at the first empty requirement cell
            length = len(str(cell))
            grouped.setdefault(req_index, []).append((length, iteration))
            req_index += 1
            col_index += step
    return grouped

def get_lengths_grouped_by_index(df, start_col_index, step):
    """Returns dict: {requirement_index: [lengths]} (used for single)"""
    grouped = {}
    if df.empty:
        return grouped
        
    for _, row in df.iterrows():
        col_index = start_col_index
        req_index = 1
        while col_index < len(row):
            cell = row.iloc[col_index]
            if pd.isna(cell) or str(cell).strip() == "":
                break # Stop at the first empty requirement cell
            length = len(str(cell))
            grouped.setdefault(req_index, []).append(length)
            req_index += 1
            col_index += step
    return grouped

def plot_combined_boxplot_with_meta_labels(meta_grouped, single_grouped, title, filename):
    all_indexes = sorted(set(meta_grouped.keys()) | set(single_grouped.keys()))
    if not all_indexes:
        print("No data available to plot.")
        return
        
    meta_data = [[val[0] for val in meta_grouped.get(i, [])] for i in all_indexes]
    single_data = [single_grouped.get(i, []) for i in all_indexes]

    positions_meta = np.arange(len(all_indexes)) * 2.0
    positions_single = positions_meta + 0.8

    # Outlier style for single
    flier_single = dict(marker='o', markerfacecolor='red', markeredgecolor='black', markersize=5, alpha=0.7)

    plt.figure(figsize=(16, 8))

    # Meta boxplot (hide default outliers, which we will draw manually)
    bp1 = plt.boxplot(meta_data, positions=positions_meta, widths=0.6,
                      patch_artist=True, flierprops=dict(marker=' ', alpha=0))

    # Single boxplot
    bp2 = plt.boxplot(single_data, positions=positions_single, widths=0.6,
                      patch_artist=True, flierprops=flier_single)

    # Box colors
    for box in bp1['boxes']:
        box.set(facecolor='blue', alpha=0.3)
    for box in bp2['boxes']:
        box.set(facecolor='red', alpha=0.3)

    # Add iteration labels for meta outliers
    for idx, i in enumerate(all_indexes):
        if not meta_data[idx]:
            continue
        data = np.array(meta_data[idx])
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        lower_bound, upper_bound = q1 - 1.5 * iqr, q3 + 1.5 * iqr

        # Add text for meta outliers
        outlier_points = {} # To handle overlapping points
        for length, iteration in meta_grouped.get(i, []):
            if length < lower_bound or length > upper_bound:
                if length not in outlier_points:
                    outlier_points[length] = []
                outlier_points[length].append(str(iteration) if iteration != "" else "?")
        
        for length, labels in outlier_points.items():
            label_text = "/".join(sorted(labels))
            plt.text(
                positions_meta[idx],
                length,
                label_text,
                color='blue',
                fontsize=8,
                ha='center',
                va='bottom',
                fontweight='bold'
            )

    tick_positions = positions_meta + 0.4
    plt.xticks(tick_positions, all_indexes, rotation=45)
    plt.xlabel("Requirement Position Within Interview")
    plt.ylabel("Character Length")
    plt.title(title)
    plt.grid(axis='y', linestyle='--', alpha=0.6)

    # Proper legend handles
    meta_handle = plt.Line2D([], [], color='blue', lw=6, alpha=0.3, label='Meta Results')
    single_handle = plt.Line2D([], [], color='red', lw=6, alpha=0.3, label='Single Results')
    single_outlier = plt.Line2D([], [], color='red', marker='o', markerfacecolor='red',
                                markeredgecolor='black', linestyle='None', label='Single Outliers')
    meta_outlier_text = plt.Line2D([], [], color='blue', linestyle='None', marker=None, label='Meta Outliers (Label=Iteration)')

    plt.legend(handles=[meta_handle, single_handle, single_outlier, meta_outlier_text])

    plt.tight_layout()
    out_path = os.path.join(script_folder, filename)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Saved boxplot with iteration labels on Meta outliers to {out_path}")
    plt.close()

# --- Main execution ---
# Group data (Column E is index 4 for meta, Column B is index 1 for single)
meta_grouped = get_lengths_and_iterations_grouped_by_index(meta_df, 4, 2)
single_grouped = get_lengths_grouped_by_index(single_df, 1, 2)

# Plot with iteration labels for meta outliers
plot_combined_boxplot_with_meta_labels(
    meta_grouped,
    single_grouped,
    "Boxplot of Requirement Lengths by Position (Meta vs Single)",
    "requirements_length_boxplot_per_position.png"
)