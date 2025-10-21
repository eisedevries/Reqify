# Reqify
This repository was created for the course [Software production](https://osiris-student.uu.nl/#/onderwijscatalogus/extern/cursus?cursuscode=INFOMSPR&taal=en&collegejaar=huidig) at Utrecht University. It was developed by Eise de Vries, Liza Lausberg and Laurens Sebel.

The repository contains a pipeline for automated requirements elicitation from interview transcripts and requirements mapping with a companion workflow for validation and human review. For concrete commands, usage and exact script names, see `usage_demo.ipynb`.

## What is contained
* A pipeline that extracts candidate requirements from transcripts
* Integrity and traceability checks for requirement–quote pairs
* Matching of elicited items to a ground truth list
* A human-in-the-loop interface to confirm or reject matches
* Summary metrics including precision recall and F1

For details on inputs and outputs as well as example runs open `usage_demo.ipynb`.

## Data preparation
The dataset used in this project originates from the paper *[LLMREI: Automating Requirements Elicitation Interviews with LLMs](https://arxiv.org/abs/2507.02564)* by Korn et al. The dataset is available [here](https://zenodo.org/records/15016930). For this project we specifically focus on dataset `RQ2_data.csv` which contains a ground truth list of requirements which can be elicited from the transcripts available in `interviews_json.zip`. Note that we recreated `RQ2_data.csv`. In this repository `RQ2_data.csv` is available under `ground_truth/dataset_llmrei.csv` and our recreated ground truth dataset is available under `ground_truth/dataset_new.csv`.

In order to run the pipeline you need to have the following files:
- `ground_truth/dataset_new.csv`
- `requirements_list.csv`
- `scenarios_list.csv`

Also you will need to create a `.env` file in order to communicate with the Azure OpenAI API.

Please note that one of the limitations of this repository is that the code is, to some extent, tailored to the specific data we have. This occurs because certain parts of the code reference a fixed data length. For example, if your dataset includes additional requirements, you will need to adjust the code accordingly; otherwise, the extra columns in your CSV files may not be processed correctly. Some parts that need to be changed are marked using the comment `# CHANGE FIXED DATA LENGTH HERE` in the codebase.

## How to run
### Activate virtual environment
The code was written for Python 3.13, but may work on earlier releases.

1. Navigate to your project folder:
   - `cd path/to/your/project`

2. Create a virtual environment:
   - `python3.13 -m venv venv` or `py -3.13 -m venv venv`

3. Activate the virtual environment
   - Linux / macOS: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`

4. Install dependencies
   - `pip install -r requirements.txt`

5. You should now be able to run Python scripts:
   - Linux / macOS: `python3 verify_human.py`
   - Windows: `python verify_human.py` or `py verify_human.py`

### Order of scripts
For more details see `usage_demo.ipynb`

1. Run the extraction script using `llm-call_retrieve-requirements.py` to produce `results/single_results.csv` and `results/meta_results.csv`.  
   The exact command sequence lives in `usage_demo.ipynb`.
2. Run the CSV verification using `verify_csv_content.py` and the quote traceability checks using `verify_quotes.py`.  
   `usage_demo.ipynb` shows how to interpret a FAILED message for each test.
3. Run the requirement to ground truth matching step using `llm-call_match-requirements.py`.  
   Check `progress.log` for any LLM calls that were not auto recovered.
4. Launch the human verification UI using `verify_human_GUI.py` and go through the on-screen steps.
5. After each reviewer completes their pass move `analysis_meta_human.csv`, `analysis_single_human.csv` and `human_verification_state.json` into `results/researcherX` where X is the reviewer number.
6. Combine human assessments into consensus files using `combine_human_assessments.py`.
7. Generate confusion matrices for the LLM only files and the human confirmed files using `confusion_matrix.py`.

Every command and filename you need appears in `usage_demo.ipynb`.

### Other scripts
The folder `descriptive` contains various other Python scripts that can be used for analyses.
The folder `ground_truth` contains the script `agreement_assessment.py` which can be used to test the agreement between two datasets regarding the elicited requirements.

## Recreation checklist
1. Confirm all transcripts are in `transcripts`
2. Produce `single_results.csv` and `meta_results.csv`
3. Verify CSV content and fix any reported issues
4. Verify quotes and review failed ones in the results CSVs
5. Run the requirement checking script and review `progress.log`
6. Run the human verification UI
7. Organize reviewer outputs into `results/researcher1`, `results/researcher2`, `results/researcher3`, `results/researcherX`
8. Combine human assessments
9. Build confusion matrices

## Human verification tool
The human verification tool has various keyboard shortcuts:
  y marks a match  
  n marks not a match
  arrow keys to go up and down a requirement match and move to the next and previous ground truth requirement

## Prompts
In total there are 3 prompts used in the pipeline. These can be configured in `llm-call_retrieve-requirements.py` under variable `SYSTEM_ANALYST_PROMPT` and `METACOGNITIVE_PROMPT_ENGINEER_PROMPT` and in `llm-call_match-requirements.py` under variable `MATCH_PROMPT`

## Limitations
There are various limitations the project currently has. Two notable ones:
* Some CSV files use comma as a delimiter while others use semicolon. Because of this some code expects commas whereas in other cases semicolons are expected
* The number of requirements and requirement identifiers for example `R.SA.4.1` are configured in code as they directly refer to various CSV files. Therefore, to run the pipeline using a different ground truth dataset various code snippets have to be changed. See section *Data preparation*.


## To start over
Delete the results folder to reset the project.