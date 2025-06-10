# utils/results_manager.py
import os
import pandas as pd
from datetime import datetime

RESULTS_DIR = ".results"

def ensure_results_dir():
    """Ensures the results directory exists."""
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

def save_results(results_df, filename_prefix="simulation_results"):
    """Saves simulation results to a CSV file."""
    ensure_results_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{filename_prefix}_{timestamp}.csv"
    file_path = os.path.join(RESULTS_DIR, file_name)
    results_df.to_csv(file_path, index=False)
    return file_name

def load_results(file_name):
    """Loads simulation results from a CSV file."""
    file_path = os.path.join(RESULTS_DIR, file_name)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

def get_available_results():
    """Returns a list of available results file names."""
    ensure_results_dir()
    return [f for f in os.listdir(RESULTS_DIR) if f.endswith('.csv')]