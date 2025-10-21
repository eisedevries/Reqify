Note this codebase is not yet well documented and described, this will be done in the future!


Limitations of code:
- some csv have a , as delimiter others have ;
- amount of requirements and requirement names (e.g. R.SA.4.1) are hardcoded in code





Recreation:
1. make sure all transcripts are in `transcripts` folder
2. run `llm-call_retrieve-requirements.py`, check `progress.log` for any LLM calls that were not automatically fixed. This creates `single_results.csv` and `meta_results.csv` in `results` folder
3. run `verify_csv_content.py` to check for any issues in the csv files created. Check the python file for instructions on what FAILED means for a specific test
4. run `verify_quotes.py` to check failed quotes. Check this file for the conditions. Most likely some quotes fail. Check these in `single_results.csv` or `meta_results.csv`
5. run `llm-call_check-requirements.py`, again check `progress.log` for any failed LLM calls that were not succesfully retried
6. run `verify_human.py` and go through the on-screen steps in the GUI
7. open folder results. Move `analysis_meta_human.csv`, `analysis_single_human.csv` and `human_verification_state.json` into a folder inside `results` folde which you name _researcherx_ where the x is the number of the researcher. In our case 3 researchers conducted the human-in-the-loop intervention so we have `researcher1`, `researcher2` and `researcher3` folders
8. run `combine_human_assessments.py`
9. run `confusion_matrix.py`



# Human Verification Tool Setup Guide

## 1. Create a Python Virtual Environment

Python 3.13 is preferred but Python 3.11 or 3.12 may also work. Check your version:

`python --version`  
or  
`python3 --version`

Navigate to your project folder:

`cd path/to/your/project`

Create the virtual environment:

`python3.13 -m venv venv`

If Python 3.13 is not available, use:

`python3.12 -m venv venv`  
or  
`python3.11 -m venv venv`

On some Windows setups:

`py -3.13 -m venv venv`

## 2. Activate the Virtual Environment

Windows:  
`venv\Scripts\activate`

macOS:  
`source venv/bin/activate`

Visual Studio Code:  
1. Open the project folder in VS Code  
2. Open the terminal (View → Terminal)  
3. Run the activation command for your system  
4. Select the interpreter from the venv folder if prompted

## 3. Install Dependencies

`pip install -r requirements.txt`

## 4. Run the Verification Script

Windows terminal:  
`python verify_human.py`  
or  
`py verify_human.py`

macOS terminal:  
`python3 verify_human.py`

Visual Studio Code:  
1. Open verify_human.py  
2. Make sure the correct interpreter is selected  
3. Press Run or F5

## 5. Using the Verification Interface

- Arrow keys to navigate between pages and items  
- y to mark an item as a match  
- n to mark an item as not a match

## 6. Output Files

The results folder contains:  
- human_verification_state.json which tracks the current state  
- analysis_meta_human.csv and analysis_single_human.csv which contain verification results

To start over delete:

`analysis_meta_human.csv`  
`analysis_single_human.csv`  
`human_verification_state.json`

Then run the script again.
