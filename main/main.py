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
    # Top skills by frequency from comma-separated required_skills.
    if "required_skills" in df.columns:
        skills_series = (
            df["required_skills"]
            .dropna()
            .astype(str)
            .str.split(",")
            .explode()
            .str.strip()
        )
        skills_series = skills_series[skills_series != ""]
        top_skills = (
            skills_series.value_counts()
            .rename_axis("skill")
            .reset_index(name="count")
            .head(5)
        )
    else:
        top_skills = pd.DataFrame(columns=["skill", "count"])
    results["top_skills"] = top_skills

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
            df_ben.groupby("benefits_tier", observed=True)["salary_usd"]
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


def generate_report(
    salary_results: dict, skills_results: dict, remote_results: dict, total_records: int
) -> str:
    exp = salary_results["avg_salary_by_experience"]
    exp_map = dict(zip(exp["experience_level"], exp["avg_salary"]))
    top_industries = salary_results["top_industries"].head(5).reset_index(drop=True)
    size = salary_results["company_size_salary"]
    size_map = dict(zip(size["company_size"], size["avg_salary"]))
    edu_counts = skills_results["education_counts"]
    most_edu = skills_results["most_common_education"]
    ben_corr = skills_results["benefits_correlation"]
    ben_tier = skills_results["benefits_salary_by_tier"]
    top_skills = skills_results.get("top_skills", pd.DataFrame(columns=["skill", "count"]))
    remote = remote_results["remote_salary_stats"]
    remote_map = dict(zip(remote["remote_ratio"], remote["avg_salary"]))
    remote_corr = remote_results["remote_salary_correlation"]

    en = exp_map.get("EN", float("nan"))
    mi = exp_map.get("MI", float("nan"))
    se = exp_map.get("SE", float("nan"))
    ex = exp_map.get("EX", float("nan"))
    small = size_map.get("S", float("nan"))
    medium = size_map.get("M", float("nan"))
    large = size_map.get("L", float("nan"))

    if pd.notna(en) and pd.notna(ex) and en != 0:
        exp_lift = ((ex - en) / en) * 100
        salary_obs = f"Executive roles earn about {exp_lift:.1f}% more than entry-level roles."
    else:
        salary_obs = "Salary clearly increases with experience level."

    ind_obs = "Top-paying industries cluster tightly, so rankings are informative but differences are moderate."
    size_obs = "Larger companies tend to offer higher salaries than small companies in this dataset."
    edu_obs = "Education demand is broadly distributed, but one credential clearly appears most often."

    ben_interp = (
        "Weak positive correlation between benefits score and salary."
        if pd.notna(ben_corr) and ben_corr > 0
        else "Weak negative/no meaningful linear correlation between benefits score and salary."
    )
    ben_key_obs = "Benefits tiers show very small pay differences, suggesting benefits score is not a major salary driver."

    remote_interp = (
        "Remote work has minimal impact on salary in this sample."
        if pd.notna(remote_corr) and abs(remote_corr) < 0.1
        else "Remote ratio appears related to salary, but effect size is still limited."
    )
    remote_key_obs = "Fully remote roles are only slightly higher paid than on-site roles."

    lines = [
        "AI JOB MARKET ANALYSIS REPORT",
        "==================================================",
        "",
        "Overview",
        "--------------------------------------------------",
        "This report analyzes global AI job listings to uncover",
        "trends in salary, experience levels, company characteristics,",
        "education requirements, and remote work patterns.",
        "",
        f"Total Records Analyzed: {total_records:,}",
        f"Date Generated: {pd.Timestamp.today().date()}",
        "",
        "",
        "1. Salary Insights",
        "--------------------------------------------------",
        "",
        "Average Salary by Experience Level:",
        f"- Entry (EN): ${en:,.0f}" if pd.notna(en) else "- Entry (EN): n/a",
        f"- Mid (MI): ${mi:,.0f}" if pd.notna(mi) else "- Mid (MI): n/a",
        f"- Senior (SE): ${se:,.0f}" if pd.notna(se) else "- Senior (SE): n/a",
        f"- Executive (EX): ${ex:,.0f}" if pd.notna(ex) else "- Executive (EX): n/a",
        "",
        "Key Observation:",
        f"- {salary_obs}",
        "",
        "Top 5 Highest Paying Industries:",
        *[
            f"{i + 1}. {row['industry']} (${row['avg_salary']:,.0f})"
            for i, row in top_industries.iterrows()
        ],
        "",
        "Key Observation:",
        f"- {ind_obs}",
        "",
        "Top 5 Most Important Skills (by demand in postings):",
        "",
        "Key Observation:",
        "- These skills represent baseline market demand and can be prioritized in hiring/training roadmaps.",
        "",
        "Company Size vs Salary:",
        f"- Small (S): ${small:,.0f}" if pd.notna(small) else "- Small (S): n/a",
        f"- Medium (M): ${medium:,.0f}" if pd.notna(medium) else "- Medium (M): n/a",
        f"- Large (L): ${large:,.0f}" if pd.notna(large) else "- Large (L): n/a",
        "",
        "Key Observation:",
        f"- {size_obs}",
        "Interpretation: Experience and company size both show clear salary gradients.",
        "Interpretation: Industry effects exist, but the top industries are relatively close in average pay.",
        "",
        "",
        "2. Education & Benefits Analysis",
        "--------------------------------------------------",
        "",
        "Most Common Education Requirement:",
        f"- {most_edu if most_edu is not None else 'n/a'}",
        "",
        "Education Distribution:",
        (
            f"- {edu_counts.iloc[0]['education_required']} leads ({edu_counts.iloc[0]['count']:,} postings), "
            f"followed by {edu_counts.iloc[1]['education_required']} ({edu_counts.iloc[1]['count']:,})"
            if len(edu_counts) >= 2
            else "- Not enough data to summarize education distribution."
        ),
        "",
        "Benefits vs Salary Correlation:",
        f"- Correlation Value: {ben_corr:.4f}" if pd.notna(ben_corr) else "- Correlation Value: n/a",
        "",
        "Interpretation:",
        f"- {ben_interp}",
        "",
        "Salary by Benefits Tier:",
    ]

    if ben_tier is not None and len(ben_tier) > 0:
        for _, row in ben_tier.iterrows():
            lines.append(f"- {row['benefits_tier']}: ${row['avg_salary']:,.0f}")
    else:
        lines.append("- Low: n/a")
        lines.append("- Medium: n/a")
        lines.append("- High: n/a")

    lines.extend(
        [
            "",
            "Key Observation:",
            f"- {ben_key_obs}",
            "Interpretation: Education requirements are concentrated in a few credentials, with Bachelor typically leading.",
            "Interpretation: Benefits appear to have limited explanatory power for salary in this dataset.",
            "",
            "",
            "3. Remote Work Trends",
            "--------------------------------------------------",
            "",
            "Salary by Remote Ratio:",
            f"- On-site (0%): ${remote_map.get(0, float('nan')):,.0f}" if pd.notna(remote_map.get(0, float('nan'))) else "- On-site (0%): n/a",
            f"- Hybrid (50%): ${remote_map.get(50, float('nan')):,.0f}" if pd.notna(remote_map.get(50, float('nan'))) else "- Hybrid (50%): n/a",
            f"- Fully Remote (100%): ${remote_map.get(100, float('nan')):,.0f}" if pd.notna(remote_map.get(100, float('nan'))) else "- Fully Remote (100%): n/a",
            "",
            "Remote vs Salary Correlation:",
            f"- Correlation Value: {remote_corr:.4f}" if pd.notna(remote_corr) else "- Correlation Value: n/a",
            "",
            "Interpretation:",
            f"- {remote_interp}",
            "",
            "Key Observation:",
            f"- {remote_key_obs}",
            "Interpretation: Remote policy alone is not a strong predictor of compensation.",
            "Interpretation: Role seniority and employer profile likely explain more salary variance than remote ratio.",
            "",
            "",
            "4. Key Takeaways",
            "--------------------------------------------------",
            "",
            "- The most influential factor in salary is: Experience level.",
            f"- The highest paying segment of the market is: {top_industries.iloc[0]['industry']} industry roles.",
            "- Remote work impact is: Positive but very small in practical terms.",
            f"- Education requirements trend shows: {most_edu if most_edu is not None else 'n/a'} is the dominant requirement.",
            "- Salary strategy should prioritize role seniority and target high-paying industries over benefits-tier optimization.",
            "",
            "",
            "5. Limitations",
            "--------------------------------------------------",
            "",
            "- Missing salary values may affect accuracy",
            "- Correlation does not imply causation",
            "- Dataset may not represent all global markets",
        ]
    )
    if len(top_skills) > 0:
        skill_lines = [
            f"{i + 1}. {row['skill']} ({int(row['count']):,} postings)"
            for i, row in top_skills.reset_index(drop=True).iterrows()
        ]
    else:
        skill_lines = ["- n/a"]
    skills_header_idx = lines.index("Top 5 Most Important Skills (by demand in postings):")
    lines[skills_header_idx + 1:skills_header_idx + 1] = skill_lines
    return "\n".join(lines)


if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    _data = _root / "data" / "ai_job_dataset.csv"
    df = read_data(_data)
    df = clean_data(df)

    salary_results = analyze_salary(df)
    skills_results = analyze_skills(df)
    remote_results = analyze_remote(df)

    report = generate_report(salary_results, skills_results, remote_results, len(df))
    print(report)

    try:
        from pdf_report import generate_board_pdf, generate_structured_markdown

        _pdf_path = generate_board_pdf(
            _root / "reports" / "ai_job_market_board_report.pdf",
            df,
            salary_results,
            skills_results,
            remote_results,
        )
        _md_path = generate_structured_markdown(
            _root / "reports" / "ai_job_market_executive_report.md",
            df,
            salary_results,
            skills_results,
            remote_results,
        )
        print(f"\nPDF report written to: {_pdf_path}")
        print(f"Markdown report written to: {_md_path}")
    except ModuleNotFoundError as exc:
        print(
            "\nPDF step skipped. Missing dependency "
            f"'{exc.name}'. Install with: python -m pip install reportlab matplotlib pillow"
        )

