from pathlib import Path

import pandas as pd

def read_data(file_path):
    df = pd.read_csv(file_path)
    return df

def clean_data(df):
     df['posting_date'] = pd.to_datetime(df['posting_date'])
     df['application_deadline'] = pd.to_datetime(df['application_deadline'])
     return df

def analyze_salary(df: pd.DataFrame) -> dict:
    results = {}

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

def analyze_skills(df: pd.DataFrame) -> dict:
    results = {}
    df_edu = df.dropna(subset=["education_required"]).copy()
    df_edu["education_required"] = df_edu["education_required"].astype(str).str.strip()
    edu_counts = (
        df_edu["education_required"]
        .value_counts()
        .rename_axis("education_required")
        .reset_index(name="count")
    )
    most_common_education = edu_counts.iloc[0]["education_required"] if len(edu_counts) > 0 else None
    results["education_counts"] = edu_counts
    results["most_common_education"] = most_common_education
    df_ben = df.dropna(subset=["salary_usd", "benefits_score"]).copy()
    df_ben["salary_usd"] = pd.to_numeric(df_ben["salary_usd"], errors="coerce")
    df_ben["benefits_score"] = pd.to_numeric(df_ben["benefits_score"], errors="coerce")

    benefits_salary_corr = df_ben["salary_usd"].corr(df_ben["benefits_score"])
    benefits_tier_table = None
    try:
        df_ben["benefits_tier"] = pd.qcut(
            df_ben["benefits_score"],
            q=3,
            labels=["Low", "Medium", "High"],
            duplicates="drop"   
        )
        benefits_tier_table = (
            df_ben.groupby("benefits_tier")["salary_usd"]
            .agg(avg_salary="mean", count="count")
            .reset_index()
            .sort_values("benefits_tier")
        )
    except Exception:
        benefits_tier_table = None
    results["benefits_correlation"] = benefits_salary_corr
    results["benefits_salary_by_tier"] = benefits_tier_table
    return results

def analyze_remote(df: pd.DataFrame) -> dict:
    results = {}
    df_remote = df.dropna(subset=["salary_usd", "remote_ratio"]).copy()
    df_remote["salary_usd"] = pd.to_numeric(df_remote["salary_usd"], errors="coerce")
    df_remote["remote_ratio"] = pd.to_numeric(df_remote["remote_ratio"], errors="coerce")

    remote_order = [0, 50, 100]
    remote_stats = (
        df_remote.groupby("remote_ratio")["salary_usd"]
        .agg(avg_salary="mean", median_salary="median", count="count")
        .reset_index()
    )
    remote_rank = {lvl: i for i, lvl in enumerate(remote_order)}
    remote_stats["remote_rank"] = remote_stats["remote_ratio"].map(remote_rank)
    remote_stats = remote_stats.sort_values("remote_rank").drop(columns=["remote_rank"])
    remote_salary_corr = df_remote["salary_usd"].corr(df_remote["remote_ratio"])
    results["remote_salary_stats"] = remote_stats
    results["remote_salary_correlation"] = remote_salary_corr
    return results


def generate_report(salary_results: dict, skills_results: dict, remote_results: dict) -> str:
    
    lines = []
    lines.append("AI Job Market Report")
    lines.append("")
    
    lines.append("Average salary per experience (mean and median):")
    lines.append(salary_results["avg_salary_by_experience"].to_string(index=False))
    lines.append("")
    
    top_industries = salary_results["top_industries"].head(5)
    lines.append("Top industries by average salary (top 5):")
    lines.append(top_industries.to_string(index=False))
    lines.append("")
    
    lines.append("Company size vs salary:")
    lines.append(salary_results["company_size_salary"].to_string(index=False))
    lines.append("")
    
    lines.append("Most common education level:")
    lines.append(str(skills_results["most_common_education"]))
    lines.append("")
    
    corr = skills_results["benefits_correlation"]
    if corr is None or pd.isna(corr):
        lines.append("Benefits vs salary correlation: could not be computed.")
    else:
        lines.append(f"Benefits vs salary correlation (Pearson): {corr:.4f}")
    lines.append("")
    if skills_results["benefits_salary_by_tier"] is not None:
        lines.append("Average salary by benefits tier (quantile buckets):")
        lines.append(skills_results["benefits_salary_by_tier"].to_string(index=False))
        lines.append("")
    else:
        lines.append("Average salary by benefits tier: unavailable (bucketing failed).")
        lines.append("")
  
    lines.append("Remote ratio vs salary:")
    lines.append(remote_results["remote_salary_stats"].to_string(index=False))
    lines.append("")
    remote_corr = remote_results["remote_salary_correlation"]
    if remote_corr is None or pd.isna(remote_corr):
        lines.append("Remote ratio vs salary correlation: could not be computed.")
    else:
        lines.append(f"Remote ratio vs salary correlation (Pearson): {remote_corr:.4f}")
    lines.append("")
    lines.append("Note: Correlation/association does not imply causation.")
    return "\n".join(lines)


if __name__ == "__main__":
    _data = Path(__file__).resolve().parent.parent / "data" / "ai_job_dataset.csv"
    df = read_data(_data)
    df = clean_data(df)

    salary_results = analyze_salary(df)
    skills_results = analyze_skills(df)
    remote_results = analyze_remote(df)

    report = generate_report(salary_results, skills_results, remote_results)
    print(report)

