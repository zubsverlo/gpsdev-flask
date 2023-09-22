import warnings
from trajectory_report.report.Report import (Report,
                                             OneEmployeeReport,
                                             ReportWithAdditionalColumns)
import pandas as pd

warnings.filterwarnings("ignore","Pandas doesn't allow columns to be created via a new attribute name - see https://pandas.pydata.org/pandas-docs/stable/indexing.html#attribute-access", UserWarning)
pd.options.mode.chained_assignment = None  # default='warn'