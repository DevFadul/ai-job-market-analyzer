import pandas as pd

def read_data(file_path):
    df = pd.read_csv(file_path)
    return df

def clean_data(df):
     df['posting_date'] = pd.to_datetime(df['posting_date'])
     df['application_deadline'] = pd.to_datetime(df['application_deadline'])
     return df



df = read_data('../data/ai_job_dataset.csv')
df = clean_data(df)

