import logging

DEBUG_LEVEL = logging.DEBUG
LOG_FILENAME = 'log'
LOG_PATH = 'atmi_backend/log'
LOG_MAXBYTES = 100 * 1024 * 1024
LOG_BACKUPS = 5

STUDY_ID = "studyId"
TASK_ID = "taskId"
DICOM = "dicom"
OUTPUT_PATH_PREFIX = "output_path_prefix"
INPUT = "input"
SERIES_EXTRACTION_QC = "series_extraction_qc"
ID = "id"
OUTPUT = "output"
SUBTASK_NAME = "moz-series-extraction"

SERIES_DESCRIPTION = "SeriesDescription"
SERIES_NUMBER = "SeriesNumber"
GRID_PERIOD = "GridPeriod"
PIXEL_SPACING = "PixelSpacing"
SLICE_THICKNESS = "SliceThickness"
MODALITY = "Modality"
CT = "CT"
INSTANCE_NUMBER = "InstanceNumber"
DATA_ROOT = "./data"
OUTPUT_ROOT = "./output"
QUALIFIED_FILE_EXT = ["\\.dcm", "IM_"]

REGISTER_MAX_HOURS = 10000000

SECRET_KEY = "dbe924ec-7767-4186-ad8a-b68face4a8fa"
