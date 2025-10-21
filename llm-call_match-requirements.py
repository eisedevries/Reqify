import os
import csv
import json
import logging
import string
import time
from collections import defaultdict
from typing import Dict, List, Any

# Third-party libraries
import pandas as pd
from dotenv import load_dotenv
from openai import AzureOpenAI, APIError
from tqdm import tqdm # Import tqdm for progress bars

# --- CONFIGURATION ---
# Edit these filenames if they change
REQUIREMENTS_FILE = 'requirements_list.csv'
SCENARIOS_FILE = 'scenarios_list.csv'
SINGLE_RESULTS_FILE = os.path.join('results', 'single_results.csv')
META_RESULTS_FILE = os.path.join('results', 'meta_results.csv')
ANALYSIS_SINGLE_OUTPUT = os.path.join('results', 'analysis_single.csv')
ANALYSIS_META_OUTPUT = os.path.join('results', 'analysis_meta.csv')
TRANSCRIPTS_DIR = 'transcripts'
RESULTS_DIR = 'results'
LOG_FILE = 'progress.log'

# --- LOGGING SETUP ---
# Configure logging to write to a file and the console
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicate logs
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create a formatter
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create a file handler to append logs to a file
file_handler = logging.FileHandler(LOG_FILE, mode='a')
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)

# Create a stream handler to log to the console
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)


# --- LLM & API FUNCTIONS ---
def load_env_and_create_client():
    """Loads environment variables and creates an Azure OpenAI client."""
    load_dotenv()
    try:
        client = AzureOpenAI(
            api_version=os.getenv("api_version"),
            azure_endpoint=os.getenv("azure_endpoint"),
            api_key=os.getenv("api_key"),
        )
        client.models.list()  # Test connection
        logging.info("Azure OpenAI client created and credentials verified.")
        return client
    except Exception as e:
        logging.error(f"Failed to create Azure OpenAI client. Check .env file and credentials. Error: {e}")
        return None

def create_llm_prompt(transcript: str, official_reqs: List[Dict], elicited_batch: List[Dict]) -> List[Dict]:
    """Constructs the messages payload for the LLM API call."""
    
    # --- PROMPT REWRITTEN FOR STRICTER MATCHING ---
    MATCH_PROMPT = """You are a meticulous and exacting expert requirements analyst. Your work is defined by precision and a strict adherence to rules. Your primary task is to analyze a list of "Elicited Requirements" against an "Official Requirements List" and an "Interview Transcript".

You will perform two sequential tasks for each Elicited Requirement.

**TASK 1: STRICT REQUIREMENT MATCHING**

You will compare each Elicited Requirement against the Official Requirements List. To declare a match, the following rules MUST be met without exception:

* **Rule of Full Equivalence**: The content, intent, and scope of the Elicited Requirement and the Official Requirement must FULLY match. They must mean the exact same thing.
* **No Partial Matches**: A partial match is not a match. If an Elicited Requirement covers only a part of an Official Requirement, or vice-versa, it is NOT a match. If it contains additional details or constraints, it is NOT a match.
* **Limited Interpretation**: Do not infer or interpret beyond the explicit text. While direct synonyms (e.g., "user" vs. "client", "display" vs. "show") are acceptable, the fundamental concepts and constraints must be identical.
* **Guiding Principle**: Your core directive is: **It is far better to return "NONE" than to select an incorrect or partial match.** When in any doubt, you MUST default to "NONE".

For this task, you will find the single matching requirement ID from the Official List. If a match that satisfies all the above rules exists, provide its ID (e.g., "R.SA.1"). If no such match exists, you MUST use "NONE".

**TASK 2: HALLUCINATION CHECK**

This check is performed ONLY on requirements for which you assigned `match_id: "NONE"` in Task 1.

For these unmatched requirements, you must determine if they are factually supported by the provided "Interview Transcript". If the substance of the unmatched Elicited Requirement cannot be found in the transcript, it is a "hallucination".

**OUTPUT FORMAT**

You MUST return your complete analysis as a single JSON array of objects. Each object in the array corresponds to one of the Elicited Requirements and MUST contain these three fields:

* "location": The original cell location of the elicited requirement (e.g., "AX31").
* "match_id": The ID of the exactly matching official requirement (e.g., "R.SA.1") or "NONE" if no perfect match is found.
* "is_hallucination": A boolean. This MUST be set to `true` ONLY IF `match_id` is "NONE" AND the requirement is NOT supported by the interview transcript. In all other cases, it must be `false`.

**Example Output:**
[
  {"location": "G31", "match_id": "R.SA.1", "is_hallucination": false},
  {"location": "I31", "match_id": "NONE", "is_hallucination": true},
  {"location": "K31", "match_id": "NONE", "is_hallucination": false}
]
"""

    official_reqs_text = "\n".join([f"- {req['Interview ID']}: {req['Requirement']}" for req in official_reqs])
    elicited_reqs_text = json.dumps(elicited_batch, indent=2)

    user_prompt = f"""
    Here is the data for your analysis:
    --- INTERVIEW TRANSCRIPT ---
    {transcript}
    --- END TRANSCRIPT ---
    --- OFFICIAL REQUIREMENTS LIST ---
    {official_reqs_text}
    --- END OFFICIAL REQUIREMENTS LIST ---
    --- ELICITED REQUIREMENTS TO ANALYZE (BATCH) ---
    {elicited_reqs_text}
    --- END ELICITED REQUIREMENTS TO ANALYZE ---
    Please provide your analysis in the specified JSON format.
    """

    return [{"role": "system", "content": MATCH_PROMPT}, {"role": "user", "content": user_prompt}]

def get_llm_analysis(client: AzureOpenAI, messages: List[Dict], retries=3, delay=5) -> List[Dict]:
    """Makes an API call to the LLM, parses the JSON response, and handles retries."""
    deployment_name = os.getenv("deployment")
    if not deployment_name:
        logging.error("'deployment' not set in .env file.")
        return []

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=deployment_name, messages=messages, response_format={"type": "json_object"}, temperature=0.0)
            content = response.choices[0].message.content
            json_start, json_end = content.find('['), content.rfind(']') + 1
            if json_start != -1:
                return json.loads(content[json_start:json_end])
            else:
                raise json.JSONDecodeError("No JSON array found in response", content, 0)
        except Exception as e:
            logging.warning(f"Error on attempt {attempt + 1}: {e}. Retrying...")
            time.sleep(delay)
    logging.error(f"Failed to get valid analysis from LLM after {retries} attempts.")
    return []

# --- HELPER FUNCTIONS ---
def get_excel_column_letters():
    """Generates a list of Excel-style column letters (A, B, ..., ZZ)."""
    letters = list(string.ascii_uppercase)
    extended_letters = letters[:]
    for first in letters:
        for second in letters:
            extended_letters.append(first + second)
    return extended_letters

def load_csv_data(filepath: str) -> List[Dict]:
    """Loads a CSV file with fallback encoding."""
    if not os.path.exists(filepath):
        logging.error(f"File not found: {filepath}")
        return []
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            return list(csv.DictReader(file))
    except UnicodeDecodeError:
        logging.warning(f"UTF-8 failed for {filepath}. Retrying with 'latin-1'.")
        with open(filepath, mode='r', encoding='latin-1') as file:
            return list(csv.DictReader(file))
    except Exception as e:
        logging.error(f"Error reading {filepath}: {e}")
        return []

def load_transcript(base_path: str, interview_id: str) -> str:
    """Loads transcript text from a JSON file."""
    filepath = os.path.join(base_path, f"{interview_id}.json")
    if not os.path.exists(filepath):
        logging.warning(f"Transcript not found: {filepath}")
        return "Transcript not available."
    with open(filepath, mode='r', encoding='utf-8') as file:
        try:
            return json.dumps(json.load(file))
        except json.JSONDecodeError:
            logging.warning(f"Could not parse JSON for transcript: {filepath}")
            return "Transcript file is not valid JSON."

# --- MAIN PROCESSING LOGIC ---
def process_results_file(
    input_filepath: str, output_filepath: str, is_meta_file: bool,
    master_reqs: List[Dict], ground_truth: Dict[str, str], llm_client: AzureOpenAI
):
    """
    Main function to read a results file, analyze it, and write the analysis CSV progressively.
    """
    if not os.path.exists(input_filepath):
        logging.warning(f"Input file not found, skipping: {input_filepath}")
        return

    logging.info(f"--- Starting processing for {os.path.basename(input_filepath)} ---")

    # 1. EXTRACT ALL REQUIREMENTS
    interviews_data = defaultdict(list)
    column_letters = get_excel_column_letters()

    with open(input_filepath, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile, delimiter=';')
        header = next(reader, None)
        if not header: return

        req_start_idx = 4 if is_meta_file else 1 # CHANGE FIXED DATA LENGTH HERE
        req_indices = [i for i in range(req_start_idx, len(header), 2)] # CHANGE FIXED DATA LENGTH HERE

        for row_idx, row in enumerate(reader, start=2):
            if not row or not row[0].strip(): continue
            interview_id = row[0].strip()
            key = (interview_id, row[1].strip()) if is_meta_file else interview_id
            for col_idx in req_indices:
                if col_idx < len(row) and row[col_idx].strip():
                    interviews_data[key].append({"location": f"{column_letters[col_idx]}{row_idx}", "text": row[col_idx].strip()})
    
    logging.info(f"Extracted requirements for {len(interviews_data)} unique interviews/iterations.")
    if not interviews_data: return

    # 2. CREATE THE INITIAL CSV FILE WITH CORRECTLY ORDERED HEADERS
    all_req_ids = [req['Interview ID'] for req in master_reqs]
    
    base_headers = ['Interview ID', 'Scenario']
    if is_meta_file:
        base_headers.append('Iteration')
    
    df = pd.DataFrame(columns=base_headers + all_req_ids)
    
    unique_keys = sorted(list(interviews_data.keys()))
    initial_data = []
    for key in unique_keys:
        interview_id = key[0] if is_meta_file else key
        row = {'Interview ID': interview_id, 'Scenario': ground_truth.get(interview_id, 'N/A')}
        if is_meta_file: row['Iteration'] = key[1]
        initial_data.append(row)
    
    df = pd.concat([df, pd.DataFrame(initial_data)], ignore_index=True)
    df.to_csv(output_filepath, sep=';', index=False)
    logging.info(f"Initial empty analysis file created: {output_filepath}")

    # 3. LLM ANALYSIS (BATCHED) AND PROGRESSIVE WRITING WITH PROGRESS BAR
    for key in tqdm(unique_keys, desc=f"Processing {os.path.basename(input_filepath)}"):
        elicited_reqs = interviews_data[key]
        interview_id = key[0] if is_meta_file else key

        scenario = ground_truth.get(interview_id)
        if not scenario: continue

        transcript = load_transcript(TRANSCRIPTS_DIR, interview_id)
        official_reqs = [req for req in master_reqs if req['Interview ID'].startswith(f"R.{scenario[:2].upper()}.")]

        for i in range(0, len(elicited_reqs), 10):
            batch = elicited_reqs[i:i+10]
            
            messages = create_llm_prompt(transcript, official_reqs, batch)
            analysis_result = get_llm_analysis(llm_client, messages)

            if analysis_result:
                df = pd.read_csv(output_filepath, sep=';', dtype=str).fillna('')
                
                index_cols = ['Interview ID', 'Scenario', 'Iteration'] if is_meta_file else ['Interview ID', 'Scenario']
                df.set_index(index_cols, inplace=True)
                
                update_key = (interview_id, scenario, key[1]) if is_meta_file else (interview_id, scenario)

                for result in analysis_result:
                    loc, match_id, is_hal = result.get("location"), result.get("match_id"), result.get("is_hallucination", False)
                    
                    if is_hal:
                        hal_col_num = 1
                        while f'HAL_{hal_col_num}' in df.columns:
                            if pd.isna(df.loc[update_key, f'HAL_{hal_col_num}']) or df.loc[update_key, f'HAL_{hal_col_num}'] == '': break
                            hal_col_num += 1
                        hal_col = f'HAL_{hal_col_num}'
                        if hal_col not in df.columns: df[hal_col] = ''
                        df.loc[update_key, hal_col] = loc
                    elif match_id and match_id != "NONE":
                        current_val = df.loc[update_key, match_id]
                        new_val = f"{current_val},{loc}" if current_val else loc
                        df.loc[update_key, match_id] = new_val

                df.reset_index().to_csv(output_filepath, sep=';', index=False)
        
        # After processing all batches for this key, log the completion.
        if is_meta_file:
            # key is a tuple: (interview_id, iteration)
            _, iteration = key
            logging.info(f"Saved results for {interview_id} - Iteration {iteration}")
        else:
            # key is just the interview_id
            logging.info(f"Saved results for {interview_id}")

    # 4. FINAL SORT AND SAVE
    logging.info("Sorting final output file...")
    final_df = pd.read_csv(output_filepath, sep=';', dtype=str).fillna('')
    
    # NEW FEATURE: Define sorting columns based on file type
    sort_columns = ['Scenario', 'Interview ID']
    if is_meta_file:
        sort_columns.append('Iteration')
        
    final_df.sort_values(by=sort_columns, inplace=True)
    final_df.to_csv(output_filepath, sep=';', index=False)
    
    logging.info(f"Successfully finished processing for {os.path.basename(input_filepath)}.")


# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    logging.info("Starting analysis script.")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    master_requirements = load_csv_data(REQUIREMENTS_FILE)
    scenarios_list = load_csv_data(SCENARIOS_FILE) 
    ground_truth_map = {item['Interview ID']: item['Scenario'] for item in scenarios_list}

    if not master_requirements or not ground_truth_map:
        logging.error(f"Could not load foundational data. Exiting.")
    else:
        llm_client = load_env_and_create_client()
        if llm_client:
            choice = ''
            while choice not in ['1', '2', '3']:
                choice = input("Select an option:\n[1] Run for single_results.csv\n[2] Run for meta_results.csv\n[3] Run for both\nEnter choice (1, 2, or 3): ")

            if choice == '1' or choice == '3':
                process_results_file(SINGLE_RESULTS_FILE, ANALYSIS_SINGLE_OUTPUT, False, master_requirements, ground_truth_map, llm_client)
            
            if choice == '2' or choice == '3':
                process_results_file(META_RESULTS_FILE, ANALYSIS_META_OUTPUT, True, master_requirements, ground_truth_map, llm_client)

            logging.info("Script finished.")
        else:
            logging.error("LLM client could not be initialized. Exiting.")