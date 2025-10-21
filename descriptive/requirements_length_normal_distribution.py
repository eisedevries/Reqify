import os
import csv
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ===================== helpers =====================

def read_jagged_csv_to_df(file_path, separator=";"):
    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=separator)
            all_rows = list(reader)
    except FileNotFoundError:
        print(f"[WARN] File not found: {file_path}")
        return pd.DataFrame()

    if not all_rows:
        return pd.DataFrame()

    max_cols = max(len(row) for row in all_rows)
    header = all_rows[0]
    data_rows = all_rows[1:]

    if max_cols > len(header):
        header.extend([f"Unnamed_Col_{i}" for i in range(len(header), max_cols)])

    padded = []
    for row in data_rows:
        if len(row) < max_cols:
            row = row + [None] * (max_cols - len(row))
        padded.append(row)

    return pd.DataFrame(padded, columns=header)

def get_single_prompt_texts(df, start_col_index=1, step=2):
    out = []
    if df.empty:
        return out
    for _, row in df.iterrows():
        c = start_col_index
        while c < len(row):
            cell = row.iloc[c]
            if pd.isna(cell) or str(cell).strip() == "":
                break
            out.append(str(cell))
            c += step
    return out

def get_meta_prompt_texts(df, start_col_index=4, step=2):
    all_texts = []
    if df.empty:
        return all_texts
    for _, row in df.iterrows():
        c = start_col_index
        while c < len(row):
            cell = row.iloc[c]
            if pd.isna(cell) or str(cell).strip() == "":
                break
            all_texts.append(str(cell))
            c += step
    return all_texts

def excess_kurtosis(x):
    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 2:
        return np.nan
    m = x.mean()
    s = x.std(ddof=1)
    if s == 0:
        return np.nan
    z = (x - m) / s
    return np.mean(z**4) - 3.0

def kde_line(x, xs, bw=None):
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return np.zeros_like(xs)
    if bw is None:
        s = np.std(x, ddof=1) if x.size > 1 else 1.0
        bw = 1.06 * s * (x.size ** (-1.0 / 5.0)) if s > 0 else 1.0
    if bw <= 0:
        bw = 1.0
    diffs = (xs[:, None] - x[None, :]) / bw
    vals = np.exp(-0.5 * diffs**2) / math.sqrt(2.0 * math.pi)
    dens = vals.mean(axis=1) / bw
    return dens

def normal_pdf(xs, mu, sd):
    if sd <= 0:
        return np.zeros_like(xs)
    return (1.0 / (sd * math.sqrt(2.0 * math.pi))) * np.exp(-0.5 * ((xs - mu) / sd) ** 2)

# ===================== main =====================

def main():
    # choose what to plot: "chars" or "words"
    plot_kind = "chars"  # change to "words" if you prefer the word view

    try:
        script_folder = os.path.dirname(os.path.abspath(__file__))
        results_folder = os.path.join(script_folder, "..", "results")
    except NameError:
        results_folder = "results"
        script_folder = os.getcwd()

    meta_file = os.path.join(results_folder, "meta_results.csv")
    single_file = os.path.join(results_folder, "single_results.csv")

    print("Reading CSV files...")
    meta_df = read_jagged_csv_to_df(meta_file, separator=";")
    single_df = read_jagged_csv_to_df(single_file, separator=";")
    print("CSV files loaded.")

    single_texts = get_single_prompt_texts(single_df, start_col_index=1, step=2)
    meta_texts = get_meta_prompt_texts(meta_df, start_col_index=4, step=2)

    if plot_kind == "chars":
        single_vals = np.array([len(t) for t in single_texts], dtype=float)
        meta_vals = np.array([len(t) for t in meta_texts], dtype=float)
        x_label = "character count"
        title = "Character length distributions with normal fits"
        legend_emp_single = "Single chars empirical"
        legend_norm_single = "Single chars normal"
        legend_emp_meta = "Meta chars empirical"
        legend_norm_meta = "Meta chars normal"
    else:
        single_vals = np.array([len(t.split()) for t in single_texts], dtype=float)
        meta_vals = np.array([len(t.split()) for t in meta_texts], dtype=float)
        x_label = "word count"
        title = "Word count distributions with normal fits"
        legend_emp_single = "Single words empirical"
        legend_norm_single = "Single words normal"
        legend_emp_meta = "Meta words empirical"
        legend_norm_meta = "Meta words normal"

    datasets = []
    if single_vals.size > 1:
        datasets.append((legend_emp_single, single_vals, "empirical"))
        datasets.append((legend_norm_single, single_vals, "normal"))
    if meta_vals.size > 1:
        datasets.append((legend_emp_meta, meta_vals, "empirical"))
        datasets.append((legend_norm_meta, meta_vals, "normal"))

    if not datasets:
        print("[INFO] Not enough data to plot.")
        return

    global_min = min(d[1].min() for d in datasets)
    global_max = max(d[1].max() for d in datasets)
    if global_min == global_max:
        global_min -= 1.0
        global_max += 1.0
    xs = np.linspace(global_min, global_max, 600)

    # color mapping: meta blue, single red
    def pick_color(label_text):
        return "blue" if "Meta" in label_text else "red"

    plt.figure(figsize=(12, 7))
    for label, arr, kind in datasets:
        mu = arr.mean()
        sd = arr.std(ddof=1) if arr.size > 1 else 0.0
        k = excess_kurtosis(arr)
        color = pick_color(label)
        if kind == "empirical":
            ys = kde_line(arr, xs)
            leg = f"{label} mean {mu:.2f} sd {sd:.2f} k {k:.4f}"
            plt.plot(xs, ys, linewidth=1.8, label=leg, color=color)
        else:
            ys = normal_pdf(xs, mu, sd)
            leg = f"{label} mean {mu:.2f} sd {sd:.2f}"
            plt.plot(xs, ys, linewidth=1.8, linestyle="--", label=leg, color=color)

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("density")
    plt.legend(fontsize=9)

    plt.tight_layout()

    # save next to this script
    out_path = os.path.join(script_folder, "requirements_length_normal_distribution.png")
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    print(f"Saved figure to {out_path}")

    plt.show()

if __name__ == "__main__":
    main()
