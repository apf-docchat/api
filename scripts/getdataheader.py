import pandas as pd
import os, sys

dataanalysis_file_path = sys.argv[1]

# Components of the path
#path_components = ["data", "user_docs", "org3", "files", "dataanalysis", "file1.csv"]

# Constructing the path
#path = os.path.join(*path_components)

# Read the CSV file
data = pd.read_csv(dataanalysis_file_path)

# Display the first few rows to understand the structure
header = data.columns.tolist()
print(header)
