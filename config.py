import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'gestptf.db')
EXCEL_PATH = os.path.join(BASE_DIR, 'xlsbase', 'Monitor Portafoglio.xlsx')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data', 'uploads')
EXPORT_FOLDER = os.path.join(BASE_DIR, 'data', 'exports')
DEFAULT_LANG = 'it'
