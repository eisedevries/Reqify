import os
import csv
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt

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

# Current folder of the script
script_folder = os.path.dirname(os.path.abspath(__file__))

# CSVs are one level above in the 'results' folder
results_folder = os.path.join(script_folder, "..", "results")
meta_file = os.path.join(results_folder, "meta_results.csv")
single_file = os.path.join(results_folder, "single_results.csv")

# Load CSV files using the robust custom function
print("Reading CSV files...")
meta_df = read_jagged_csv_to_df(meta_file, separator=";")
single_df = read_jagged_csv_to_df(single_file, separator=";")
print("CSV files loaded successfully into pandas DataFrames.")

def collect_words(df, start_col_index, step):
    """Collects all words from specified columns in a DataFrame."""
    words = []
    if df.empty:
        return words
        
    max_col = df.shape[1]
    col_index = start_col_index

    while col_index < max_col:
        # Check if the column exists before trying to access it
        if col_index < len(df.columns):
            col_data = df.iloc[:, col_index]
            # Stop if all values in the column are null/empty
            if col_data.isnull().all() or (col_data.astype(str).str.strip() == "").all():
                break
            # Process each non-empty cell
            for cell in col_data.dropna():
                text = str(cell).strip()
                if text:
                    words.extend(text.split())
        else:
            # This case shouldn't be hit with the new reader, but is safe to have
            break 
        col_index += step
    return words

# Column E is index 4 (0-based)
meta_words = collect_words(meta_df, 4, 2)

# Column B is index 1 (0-based)
single_words = collect_words(single_df, 1, 2)

def make_wordcloud(words, title, filename):
    """Generates and saves a word cloud from a list of words."""
    text = " ".join(words)
    if not text.strip():
        print(f"No words found to generate word cloud for: {title}")
        return
        
    wc = WordCloud(width=800, height=400, background_color="white").generate(text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.title(title)
    
    out_path = os.path.join(script_folder, filename)
    wc.to_file(out_path)
    print(f"Saved word cloud for '{title}' to {out_path}")
    # plt.show() # Commented out to prevent blocking script execution

# Generate the word clouds
make_wordcloud(meta_words, "Word Cloud for Meta Results", "wordcloud_meta.png")
make_wordcloud(single_words, "Word Cloud for Single Results", "wordcloud_single.png")
