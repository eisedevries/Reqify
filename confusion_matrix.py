import csv
import os

#### CONFIG ####
PRINT_FULL_RESULTS = False  # Set to True to print all individual TP, FP, FN, TN entries



def load_and_clean_csv(file_path: str) -> dict:
    """
    Robustly loads a CSV file. It automatically detects the delimiter (comma or semicolon),
    handles 'latin-1' encoding, cleans a potential Byte Order Mark (BOM), and returns
    the data as a dictionary.
    """
    data_map = {}
    with open(file_path, mode='r', encoding='latin-1') as infile:
        # Read the first line to intelligently determine the delimiter.
        try:
            first_line = infile.readline()
            infile.seek(0) # Reset the file reader to the beginning
        except StopIteration:
            return {} # File is empty

        delimiter = ';' if ';' in first_line else ','

        reader = csv.reader(infile, delimiter=delimiter)
        
        try:
            header = next(reader)
        except StopIteration:
            return {}
        
        # Clean the BOM from the first header, which is a common issue.
        header[0] = header[0].lstrip('\ufeff')
        clean_header = [h.strip() for h in header]

        try:
            # Verify that essential columns exist after cleaning.
            clean_header.index('Interview ID')
            clean_header.index('Scenario')
        except ValueError as e:
            raise KeyError(f"Column not found in {os.path.basename(file_path)}: {e}")

        # Process the rest of the file using the cleaned header.
        for row in reader:
            if not row or len(row) < len(clean_header):
                continue
            
            # Create a dictionary for the current row
            row_dict = {clean_header[i]: value for i, value in enumerate(row)}
            
            # Create a unique key for the data_map
            key = (row_dict['Interview ID'], row_dict['Scenario'])
            data_map[key] = row_dict
            
    return data_map


def analyze_requirement_data():
    """
    Compares requirement elicitation data from a ground truth CSV with a human-analyzed CSV.
    """
    try:
        # --- Ask the user to select an analysis file ---
        results_folder = 'results'
        try:
            analysis_files = [f for f in os.listdir(results_folder) if 'analysis' in f and f.endswith('.csv')]
        except FileNotFoundError:
            print(f"Error: The directory '{results_folder}' was not found.")
            return
            
        if not analysis_files:
            print(f"Error: No CSV files containing 'analysis' found in the '{results_folder}' folder.")
            return

        print("Please select a file to analyze:")
        for i, filename in enumerate(analysis_files):
            print(f"  {i + 1}: {filename}")

        selection = None
        while selection is None:
            try:
                choice = int(input(f"\nEnter the number of the file (1-{len(analysis_files)}): "))
                if 1 <= choice <= len(analysis_files):
                    selection = analysis_files[choice - 1]
                else:
                    print("Invalid number. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        human_analysis_path = os.path.join(results_folder, selection)
        print(f"\nSelected file: {human_analysis_path}\n")
        # --- End of file selection ---

        ground_truth_path = os.path.join('ground_truth', 'dataset_new.csv')
        
        requirement_columns = [
            'R.SA.1', 'R.SA.2', 'R.SA.3', 'R.SA.4.1', 'R.SA.4.2', 'R.SA.5.1', 'R.SA.5.2',
            'R.SA.6.1', 'R.SA.6.2', 'R.SA.7', 'R.SA.8', 'R.SK.1', 'R.SK.2', 'R.SK.3',
            'R.SK.4', 'R.SK.5', 'R.SK.6', 'R.SK.7', 'R.SK.8', 'R.SK.9', 'R.SK.10.1',
            'R.SK.10.2', 'R.SK.11.1', 'R.SK.11.2', 'R.SK.12.1', 'R.SK.12.2'
        ]

        print("Loading data files with robust method...")
        ground_truth_data = load_and_clean_csv(ground_truth_path)
        human_analysis_data = load_and_clean_csv(human_analysis_path)
        print("Data loaded successfully.\n")

        results = {
            "True Positives": [], "False Positives": [],
            "False Negatives": [], "True Negatives": []
        }

        print("Comparing data...")
        for key, human_row in human_analysis_data.items():
            if key in ground_truth_data:
                gt_row = ground_truth_data[key]
                interview_id, scenario = key

                for col in requirement_columns:
                    if col not in gt_row or col not in human_row: continue
                    
                    gt_val = gt_row.get(col, '').strip().lower()
                    human_val = human_row.get(col, '').strip()

                    gt_is_elicited = gt_val != 'no'
                    human_is_elicited = human_val != ''

                    message = f"ID: {interview_id}, Scenario: {scenario}, Requirement: {col}"

                    if gt_is_elicited and human_is_elicited: results["True Positives"].append(message)
                    elif not gt_is_elicited and human_is_elicited: results["False Positives"].append(message)
                    elif gt_is_elicited and not human_is_elicited: results["False Negatives"].append(message)
                    elif not gt_is_elicited and not human_is_elicited: results["True Negatives"].append(message)
            else:
                print(f"Warning: Entry for {key} found in human analysis but not in ground truth. Skipping.")

        print("Comparison complete.\n")

        # --- 6. Print Results ---
        if PRINT_FULL_RESULTS:
            for category, items in results.items():
                print(f"--- {category} (Total: {len(items)}) ---")
                if not items: print("None Found")
                else:
                    for item in items: print(item)
            print("\n" + "="*60 + "\n")

        # --- 7. Calculate and Print Performance Metrics ---
        tp = len(results["True Positives"])
        fp = len(results["False Positives"])
        fn = len(results["False Negatives"])
        tn = len(results["True Negatives"])

        # Calculate metrics, handling division by zero
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        total_cases = tp + tn + fp + fn
        accuracy = (tp + tn) / total_cases if total_cases > 0 else 0

        print("--- Performance Metrics ---")
        print(f"Sum True Positives:  {tp}")
        print(f"Sum False Positives: {fp}")
        print(f"Sum False Negatives: {fn}")
        print(f"Sum True Negatives:  {tn}")
        print("-" * 25)
        print(f"Accuracy:  {accuracy:.2%}")
        print(f"Precision: {precision:.2%}")
        print(f"Recall:    {recall:.2%}")
        print(f"F1 Score:  {f1_score:.2%}")
        print("\n" + "="*60 + "\n")


    except FileNotFoundError as e:
        print(f"Error: A file was not found. Please check your file paths. Details: {e}")
    except KeyError as e:
        print(f"Error: A required column was not found. Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    analyze_requirement_data()