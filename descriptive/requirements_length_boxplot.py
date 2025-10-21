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
    """
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=separator)
            all_rows = list(reader)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
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
        iteration = ""
        if len(row) > 1 and not pd.isna(row.iloc[1]):
            try:
                iteration = int(float(row.iloc[1]))
            except (ValueError, TypeError):
                iteration = row.iloc[1]

        col_index = start_col_index
        req_index = 1
        while col_index < len(row):
            cell = row.iloc[col_index]
            if pd.isna(cell) or str(cell).strip() == "":
                break
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
                break
            length = len(str(cell))
            grouped.setdefault(req_index, []).append(length)
            req_index += 1
            col_index += step
    return grouped

def compute_average_per_position_single(single_grouped):
    """
    Given {pos: [lengths]} return a list of averages ordered by position.
    """
    positions = sorted(single_grouped.keys())
    avgs = []
    for p in positions:
        vals = single_grouped[p]
        if len(vals) > 0:
            avgs.append(np.mean(vals))
    return positions, avgs

def compute_average_per_position_meta(meta_grouped, iteration_filter=None):
    """
    Given {pos: [(length, iteration)]} return a list of averages by position.
    If iteration_filter is None use all iterations.
    If iteration_filter is an int keep only that iteration.
    """
    positions = sorted(meta_grouped.keys())
    avgs = []
    for p in positions:
        pairs = meta_grouped[p]
        if iteration_filter is None:
            vals = [length for length, it in pairs]
        else:
            vals = [length for length, it in pairs if str(it) == str(iteration_filter)]
        if len(vals) > 0:
            avgs.append(np.mean(vals))
    return positions, avgs

def plot_averages_boxplots(meta_grouped, single_grouped, filename):
    """
    Build five boxplots where each box receives the per position averages
    for its group. Groups
      1 average for all single
      2 average for all meta
      3 average for all meta iteration 1
      4 average for all meta iteration 2
      5 average for all meta iteration 3
    """
    # Compute averages per position for each group
    pos_s, avg_s = compute_average_per_position_single(single_grouped)
    pos_m_all, avg_m_all = compute_average_per_position_meta(meta_grouped, iteration_filter=None)
    pos_m1, avg_m1 = compute_average_per_position_meta(meta_grouped, iteration_filter=1)
    pos_m2, avg_m2 = compute_average_per_position_meta(meta_grouped, iteration_filter=2)
    pos_m3, avg_m3 = compute_average_per_position_meta(meta_grouped, iteration_filter=3)

    # Collect data for boxplot
    data = [
        avg_s if len(avg_s) > 0 else [],
        avg_m_all if len(avg_m_all) > 0 else [],
        avg_m1 if len(avg_m1) > 0 else [],
        avg_m2 if len(avg_m2) > 0 else [],
        avg_m3 if len(avg_m3) > 0 else [],
    ]

    labels = [
        "All single",
        "All meta",
        "Meta iteration 1",
        "Meta iteration 2",
        "Meta iteration 3",
    ]

    # Filter out empty groups to avoid empty boxes
    filtered = [(d, l) for d, l in zip(data, labels) if len(d) > 0]
    if not filtered:
        print("No data available to plot.")
        return

    data, labels = zip(*filtered)

    plt.figure(figsize=(12, 8))
    bp = plt.boxplot(list(data), patch_artist=True, showfliers=False)

    # Simple colors
    facecolors = ["#8da0cb", "#fc8d62", "#66c2a5", "#e78ac3", "#a6d854"]
    for box, fc in zip(bp["boxes"], facecolors[:len(bp["boxes"])]):
        box.set_facecolor(fc)
        box.set_alpha(0.6)

    plt.xticks(range(1, len(labels) + 1), labels, rotation=0)
    plt.ylabel("Average character length per position")
    plt.title("Averages per position grouped into boxplots")
    plt.grid(True, axis='y')
    plt.tight_layout()

    out_path = os.path.join(script_folder, filename)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"Saved averages boxplots to {out_path}")
    plt.close()

# --- Main execution ---
# Group data  Column E is index 4 for meta  Column B is index 1 for single
meta_grouped = get_lengths_and_iterations_grouped_by_index(meta_df, 4, 2)
single_grouped = get_lengths_grouped_by_index(single_df, 1, 2)

# Plot averages as requested
plot_averages_boxplots(
    meta_grouped=meta_grouped,
    single_grouped=single_grouped,
    filename="requirements_length_boxplot.png"
)
