import csv
import os

#### CONFIG ####
PRINT_FULL_RESULTS = False  # Set to True to print all individual TP, FP, FN, TN entries


def load_and_clean_csv(file_path: str) -> dict:
    """
    Robustly loads a CSV file. It automatically detects the delimiter (comma or semicolon),
    handles 'latin-1' encoding, cleans a potential Byte Order Mark (BOM), and returns
    the data as a dictionary.

    If an 'Iteration' column is present, it keys data by (ID, Scenario, Iteration).
    If not, it keys data by (ID, Scenario).
    """
    data_map = {}
    print(f"Loading file: {os.path.basename(file_path)}")
    
    with open(file_path, mode='r', encoding='latin-1') as infile:
        try:
            first_line = infile.readline()
            infile.seek(0)
        except StopIteration:
            return {}

        delimiter = ';' if ';' in first_line else ','
        reader = csv.reader(infile, delimiter=delimiter)
        
        try:
            header = next(reader)
        except StopIteration:
            return {}
        
        header[0] = header[0].lstrip('\ufeff')
        clean_header = [h.strip() for h in header]

        # Check for required columns
        try:
            clean_header.index('Interview ID')
            clean_header.index('Scenario')
        except ValueError as e:
            raise KeyError(f"Column not found in {os.path.basename(file_path)}: {e}")

        # --- KEY CHANGE: Check for optional 'Iteration' column ---
        has_iteration_column = 'Iteration' in clean_header
        if has_iteration_column:
            print(f" -> Found 'Iteration' column. Using (ID, Scenario, Iteration) key.")
        else:
            print(f" -> No 'Iteration' column found. Using (ID, Scenario) key.")

        # Process the rest of the file
        for row in reader:
            if not row or len(row) < len(clean_header):
                continue
            
            row_dict = {clean_header[i]: value for i, value in enumerate(row)}
            
            # Create a unique key based on whether 'Iteration' column exists
            try:
                if has_iteration_column:
                    key = (
                        row_dict['Interview ID'], 
                        row_dict['Scenario'], 
                        row_dict['Iteration'].strip()
                    )
                else:
                    key = (
                        row_dict['Interview ID'], 
                        row_dict['Scenario']
                    )
                
                data_map[key] = row_dict
                
            except KeyError:
                print(f"Warning: Skipping row with missing data: {row}")
            
    return data_map


def print_performance_metrics(tp, fp, fn, tn, iteration_num=None, output_file=None):
    """
    Calculates and prints the standard performance metrics.
    Optionally prints an iteration number in the title.
    Writes the same output to the provided file object if one is given.
    """
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    total_cases = tp + tn + fp + fn
    accuracy = (tp + tn) / total_cases if total_cases > 0 else 0

    title = "--- Performance Metrics ---"
    if iteration_num:
        title = f"--- Performance Metrics (Iteration {iteration_num}) ---"

    # Build the output string
    lines = [
        title,
        f"Sum True Positives:  {tp}",
        f"Sum False Positives: {fp}",
        f"Sum False Negatives: {fn}",
        f"Sum True Negatives:  {tn}",
        "-" * 25,
        f"Accuracy:  {accuracy:.2%}",
        f"Precision: {precision:.2%}",
        f"Recall:    {recall:.2%}",
        f"F1 Score:  {f1_score:.2%}",
        "\n" + "="*60 + "\n"
    ]
    
    output_string = "\n".join(lines)
    
    # Print to console
    print(output_string)
    
    # Write to file
    if output_file:
        output_file.write(output_string + "\n") # Add extra newline for spacing in file


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
            print(f" {i + 1}: {filename}")
        print(" 0: All files")

        selected_files = []
        while not selected_files:
            try:
                choice_raw = input(f"\nEnter the number of the file 1 to {len(analysis_files)} or 0 for all: ").strip().lower()
                if choice_raw in {"0", "a", "all", "*"}:
                    selected_files = analysis_files
                else:
                    choice = int(choice_raw)
                    if 1 <= choice <= len(analysis_files):
                        selected_files = [analysis_files[choice - 1]]
                    else:
                        print("Invalid number. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number or 0 for all.")


        
        # CHANGE FIXED DATA LENGTH HERE
        requirement_columns = [
            'R.SA.1', 'R.SA.2', 'R.SA.3', 'R.SA.4.1', 'R.SA.4.2', 'R.SA.5.1', 'R.SA.5.2',
            'R.SA.6.1', 'R.SA.6.2', 'R.SA.7', 'R.SA.8', 'R.SK.1', 'R.SK.2', 'R.SK.3',
            'R.SK.4', 'R.SK.5', 'R.SK.6', 'R.SK.7', 'R.SK.8', 'R.SK.9', 'R.SK.10.1',
            'R.SK.10.2', 'R.SK.11.1', 'R.SK.11.2', 'R.SK.12.1', 'R.SK.12.2'
        ]


        ground_truth_path = os.path.join('ground_truth', 'dataset_new.csv')

        print("Loading ground truth with robust method...")
        ground_truth_data = load_and_clean_csv(ground_truth_path)
        print("Ground truth loaded.\n")

        for selection in selected_files:
            human_analysis_path = os.path.join(results_folder, selection)
            print(f"\nSelected file: {human_analysis_path}\n")
            
            base_name, _ = os.path.splitext(selection)
            output_filename = f"confusion_{base_name}.txt"
            output_path = os.path.join(results_folder, output_filename)

            print("Loading analysis file with robust method...")
            human_analysis_data = load_and_clean_csv(human_analysis_path)
            print("Data loaded successfully.\n")

            is_meta_file = 'meta' in selection.lower()

            with open(output_path, 'w', encoding='utf-8') as f_out:
                print(f"Saving confusion matrix results to: {output_path}\n")
                
                if is_meta_file:
                    print("Meta file detected. Running analysis for iterations 1, 2, and 3.")
                    for iter_to_check in ['1', '2', '3']:
                        results = {
                            "True Positives": [], "False Positives": [],
                            "False Negatives": [], "True Negatives": []
                        }
                        print(f"--- Comparing data for Iteration {iter_to_check} ---")

                        for human_key, human_row in human_analysis_data.items():
                            try:
                                interview_id, scenario, iteration = human_key
                            except ValueError:
                                print(f"Error: 'meta' file '{selection}' seems to be missing iteration data. Aborting.")
                                break

                            if iteration != iter_to_check:
                                continue
                            
                            gt_key = (interview_id, scenario)

                            if gt_key in ground_truth_data:
                                gt_row = ground_truth_data[gt_key]
                                for col in requirement_columns:
                                    if col not in gt_row or col not in human_row:
                                        continue
                                    
                                    gt_val = gt_row.get(col, '').strip().lower()
                                    human_val = human_row.get(col, '').strip()
                                    gt_is_elicited = gt_val != 'no'
                                    human_is_elicited = human_val != ''
                                    message = f"ID: {interview_id}, Scen: {scenario}, Iter: {iteration}, Req: {col}"

                                    if gt_is_elicited and human_is_elicited:
                                        results["True Positives"].append(message)
                                    elif not gt_is_elicited and human_is_elicited:
                                        results["False Positives"].append(message)
                                    elif gt_is_elicited and not human_is_elicited:
                                        results["False Negatives"].append(message)
                                    elif not gt_is_elicited and not human_is_elicited:
                                        results["True Negatives"].append(message)
                            else:
                                print(f"Warning: Entry for {gt_key} not in ground truth. Skipping.")

                        print("Comparison complete.\n")
                        
                        if PRINT_FULL_RESULTS:
                            for category, items in results.items():
                                print(f"--- {category} (Total: {len(items)}) ---")
                                if not items:
                                    print("None Found")
                                else:
                                    for item in items:
                                        print(item)
                            print("\n" + "="*60 + "\n")

                        tp = len(results["True Positives"])
                        fp = len(results["False Positives"])
                        fn = len(results["False Negatives"])
                        tn = len(results["True Negatives"])
                        
                        print_performance_metrics(tp, fp, fn, tn, iteration_num=iter_to_check, output_file=f_out)

                else:
                    print("Single analysis file detected. Running combined analysis.")
                    results = {
                        "True Positives": [], "False Positives": [],
                        "False Negatives": [], "True Negatives": []
                    }

                    print("Comparing data...")
                    for key, human_row in human_analysis_data.items():
                        try:
                            interview_id, scenario = key
                        except ValueError:
                            print(f"Error: File '{selection}' has unexpected key structure. Expected (ID, Scenario). Aborting.")
                            break

                        if key in ground_truth_data:
                            gt_row = ground_truth_data[key]
                            
                            for col in requirement_columns:
                                if col not in gt_row or col not in human_row:
                                    continue
                                
                                gt_val = gt_row.get(col, '').strip().lower()
                                human_val = human_row.get(col, '').strip()
                                gt_is_elicited = gt_val != 'no'
                                human_is_elicited = human_val != ''
                                message = f"ID: {interview_id}, Scenario: {scenario}, Requirement: {col}"

                                if gt_is_elicited and human_is_elicited:
                                    results["True Positives"].append(message)
                                elif not gt_is_elicited and human_is_elicited:
                                    results["False Positives"].append(message)
                                elif gt_is_elicited and not human_is_elicited:
                                    results["False Negatives"].append(message)
                                elif not gt_is_elicited and not human_is_elicited:
                                    results["True Negatives"].append(message)
                        else:
                            print(f"Warning: Entry for {key} found in human analysis but not in ground truth. Skipping.")

                    print("Comparison complete.\n")

                    if PRINT_FULL_RESULTS:
                        for category, items in results.items():
                            print(f"--- {category} (Total: {len(items)}) ---")
                            if not items:
                                print("None Found")
                            else:
                                for item in items:
                                    print(item)
                        print("\n" + "="*60 + "\n")

                    tp = len(results["True Positives"])
                    fp = len(results["False Positives"])
                    fn = len(results["False Negatives"])
                    tn = len(results["True Negatives"])
                    
                    print_performance_metrics(tp, fp, fn, tn, iteration_num=None, output_file=f_out)

                



    except FileNotFoundError as e:
        print(f"Error: A file was not found. Please check your file paths. Details: {e}")
    except KeyError as e:
        print(f"Error: A required column was not found. Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    analyze_requirement_data()


if __name__ == "__main__":
    main()