import pandas as pd
from pandas.io.formats.style import Subset

def read_data(file_path):
    df = pd.read_csv(file_path)
    return df

def clean_data(df):
     df['posting_date'] = pd.to_datetime(df['posting_date'])
     df['application_deadline'] = pd.to_datetime(df['application_deadline'])
     return df
def analyze_salary(df:pd.DataFrame) -> dict:
    result = {}

    df_exp = df.dropna(subset = ["salary_usd", "experience_level"]).copy()
    df_exp["salary_usd"] = pd.to_numeric(df_exp["salary_usd"], errors = "coerce")

    experience_order = ["EN", "MI", "SE", "EX"]
    exp_stats = (
        df_exp.groupby("experience_level")["salary_usd"]
        .agg(avg_salary = "mean", median_salary = "median", count = "count")
        .reset_index()
)

    exp_rank = {lvl: i for i, lvl in enumerate(experience_order)}
    exp_stats["experience_rank"] = exp_stats["experience_level"].map(exp_rank)
    exp_stats = exp_stats.sort_values("experience_rank").drop(columns = ["experience_rank"])

    results["avg_salary_by_experience"] = exp_stats

    df_ind = df.dropna(subset=["salary_usd", "industry"]).copy()
    df_ind["salary_usd"] = pd.to_numeric(df_ind["salary_usd"], errors="coerce")
    industry_stats = (
        df_ind.groupby("industry")["salary_usd"]
        .agg(avg_salary="mean", count="count")
        .reset_index()
        .sort_values("avg_salary", ascending=False)
    )
    results["top_industries"] = industry_stats
    
    df_size = df.dropna(subset=["salary_usd", "company_size"]).copy()
    df_size["salary_usd"] = pd.to_numeric(df_size["salary_usd"], errors="coerce")
    size_order = ["S", "M", "L"] 
    size_stats = (
        df_size.groupby("company_size")["salary_usd"]
        .agg(avg_salary="mean", median_salary="median", count="count")
        .reset_index()
    )
    size_rank = {lvl: i for i, lvl in enumerate(size_order)}
    size_stats["size_rank"] = size_stats["company_size"].map(size_rank)
    size_stats = size_stats.sort_values("size_rank").drop(columns=["size_rank"])

    results["company_size_salary"] = size_stats
    
    return results



df = read_data('../data/ai_job_dataset.csv')
df = clean_data(df)

