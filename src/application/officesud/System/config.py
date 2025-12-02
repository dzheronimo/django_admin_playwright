import os

HEADLESS = False

SESSION_VARS = {
    "EDS_PATH": None,
    "EDS_PASSWORD": None, 
    "EXCEL_FILE_PATH": None
}

def save_config_key(key, value):
    SESSION_VARS[key] = value

def setup_user_config():
    return