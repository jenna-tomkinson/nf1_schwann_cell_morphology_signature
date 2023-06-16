#!/usr/bin/env python
# coding: utf-8

# # Training a Logistic Regression Model

# ## Imports

# In[ ]:


import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from joblib import dump


# ## Find the git root Directory

# In[ ]:


# Get the current working directory
cwd = Path.cwd()

if (cwd / ".git").is_dir():
    root_dir = cwd

else:
    root_dir = None
    for parent in cwd.parents:
        if (parent / ".git").is_dir():
            root_dir = parent
            break

# Check if a Git root directory was found
if root_dir is None:
    raise FileNotFoundError("No Git root directory found.")


# ## Import Utils

# In[ ]:


sys.path.append(f"{root_dir}/utils")
import preprocess_utils as ppu


# # Seed and Generator for Reproducibility

# In[ ]:


rnd_val = 0  # Random value for all seeds
rng = np.random.default_rng(seed=rnd_val)  # random number generator


# # Converting parquet to pandas dataframe

# ## Define paths

# In[ ]:


data_path = Path("data")

data_path.mkdir(
    parents=True, exist_ok=True
)  # Create the parent directories if they don't exist

filename3 = "Plate_3_sc_norm_fs.parquet"
filename3p = "Plate_3_prime_sc_norm_fs.parquet"
plate_path = Path(
    f"{root_dir}/nf1_painting_repo/3.processing_features/data/feature_selected_data"
)

lr_output_path = data_path / "lr_model.joblib"

le_output_path = data_path / "label_encoder.joblib"

testdf_output_path = data_path / "testdf.joblib"

path3 = plate_path / filename3

path3p = plate_path / filename3p


# ## Feature selected plate data

# In[ ]:


# Creates an object for accessing the plate 3 normalized data using the path of the data
po3 = ppu.Preprocess_data(path=path3)

# Creates an object for accessing the plate 3 prime normalized data using the path of the data
po3p = ppu.Preprocess_data(path=path3p)

plate3df = po3.df  # Returns the dataframe generated by the csv
plate3pdf = po3p.df  # Returns the dataframe generated by the csv

common_columns = list(plate3df.columns.intersection(plate3pdf.columns))


# ## Annotated plate data

# In[ ]:


filename3 = "Plate_3_sc.parquet"
filename3p = "Plate_3_prime_sc.parquet"
plate_path = Path(
    f"{root_dir}/nf1_painting_repo/3.processing_features/data/annotated_data"
)

path3 = plate_path / filename3

path3p = plate_path / filename3p

# Creates an object for accessing the plate 3 normalized data using the path of the data
po3 = ppu.Preprocess_data(path=path3)

# Creates an object for accessing the plate 3 prime normalized data using the path of the data
po3p = ppu.Preprocess_data(path=path3p)

# Returns the dataframe generated by the csv
plate3df = po3.df

# Returns the dataframe generated by the csv
plate3pdf = po3p.df


# # Preprocess Data

# ## Use only common columns

# In[ ]:


# Set plate column:
plate3df["Metadata_plate"] = "3"
plate3pdf["Metadata_plate"] = "3p"

plate3df = plate3df.loc[:, common_columns]
plate3pdf = plate3pdf.loc[:, common_columns]

# Combine the plate dataframes:
platedf = pd.concat([plate3df, plate3pdf], axis="rows")


# ## Normalize Data

# In[ ]:


# Get all columns that aren't metadata
columns_to_normalize = [col for col in platedf.columns if "Metadata" not in col]

# Normalize the columns
mms = MinMaxScaler()
normdf = pd.DataFrame(
    mms.fit_transform(platedf[columns_to_normalize]), columns=columns_to_normalize
)

# Apply the transformation to the dataframe
platedf[columns_to_normalize] = normdf


# ## Create Classes

# In[ ]:


target_column = "Metadata_genotype"
stratify_column = "Metadata_Well"

# These represent the fractions of the entire dataset
train_val_frac = 0.85
test_frac = 1 - train_val_frac
val_frac = 0.15


# ## Down-sample and stratify by well

# In[ ]:


# Find the cardinality of the smallest class
smallest_gene = platedf[target_column].value_counts().min()
platedata = pd.DataFrame()

for gene in platedf[target_column].unique():

    # Determine what fraction of each gene's dataset would be needed for to have the same number of samples per geneotype
    df = platedf.loc[platedf["Metadata_genotype"] == gene]
    df_frac = smallest_gene / len(df)

    # Use the fraction above to stratify sample by well
    stratwell = df.groupby(stratify_column, group_keys=False).apply(
        lambda x: x.sample(frac=df_frac, random_state=rnd_val)
    )

    # Store these stratified samples in a dataframe
    platedata = pd.concat([platedata, stratwell], axis="rows")


# ## Stratified Train-test split

# In[ ]:


traindf, testdf = train_test_split(
    platedata,
    train_size=train_val_frac,
    stratify=platedata[[target_column, stratify_column]],
    shuffle=True,
    random_state=rnd_val,
)


# ## Encode Labels

# In[ ]:


le = LabelEncoder()
testdf["label"] = le.fit_transform(testdf[target_column].values)
traindf["label"] = le.transform(traindf[target_column].values)


# ## Remove unecessary columns

# In[ ]:


traindf = po3.remove_meta(df=traindf)
testdf = po3.remove_meta(df=testdf)


# # Model Training

# In[1]:


lr = LogisticRegression(
    max_iter=1000, solver="sag", multi_class="ovr", random_state=rnd_val, n_jobs=-1
)
lr.fit(X=traindf.drop("label", axis="columns"), y=traindf["label"])


# ## Save Model

# In[2]:


dump(lr, lr_output_path)


# ## Save Data

# In[3]:


dump(testdf, testdf_output_path)
dump(le, le_output_path)
