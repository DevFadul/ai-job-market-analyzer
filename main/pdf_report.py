"""Board-style PDF report: narrative sections plus charts aligned to analyze_* outputs."""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.lib.utils import ImageReader  # noqa: E402
from reportlab.platypus import Image as RLImage  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
)

EXPERIENCE_LABELS = {
    "EN": "Entry",
    "MI": "Mid-level",
    "SE": "Senior",
    "EX": "Executive",
}

SIZE_LABELS = {"S": "Small", "M": "Medium", "L": "Large"}
PALETTE = {
    "ink": "#0f172a",
    "primary": "#1d4ed8",
    "secondary": "#7c3aed",
    "accent": "#0f766e",
    "muted": "#64748b",
    "bg": "#f8fafc",
}


def _setup_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.grid": True,
            "grid.alpha": 0.3,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
        }
    )


def _save_fig_to_buffer(fig: plt.Figure) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf


def _rl_image_from_buffer(buf: io.BytesIO, max_width: float) -> RLImage:
    buf.seek(0)
    ir = ImageReader(buf)
    iw, ih = ir.getSize()
    aspect = ih / float(iw)
    w = max_width
    h = w * aspect
    buf.seek(0)
    return RLImage(buf, width=w, height=h)


def figure_experience_salary(exp_stats: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    labels = [EXPERIENCE_LABELS.get(x, str(x)) for x in exp_stats["experience_level"]]
    n = len(labels)
    x = range(n)
    w = 0.35
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar([i - w / 2 for i in x], exp_stats["avg_salary"], width=w, color="#2c5282", label="Mean")
    ax.bar([i + w / 2 for i in x], exp_stats["median_salary"], width=w, color="#63b3ed", label="Median")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Salary (USD)")
    ax.set_title("Salary by experience level (mean and median)")
    ax.legend()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    return _save_fig_to_buffer(fig)


def figure_industry_salary(industry_stats: pd.DataFrame, top_n: int = 12) -> io.BytesIO:
    _setup_matplotlib()
    d = industry_stats.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.barh(d["industry"], d["avg_salary"], color="#276749")
    ax.set_xlabel("Mean salary (USD)")
    ax.set_title(f"Top {top_n} industries by mean salary")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    fig.tight_layout()
    return _save_fig_to_buffer(fig)


def figure_company_size(size_stats: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    labels = [SIZE_LABELS.get(s, str(s)) for s in size_stats["company_size"]]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.bar(labels, size_stats["avg_salary"], color="#744210")
    ax.set_ylabel("Mean salary (USD)")
    ax.set_title("Mean salary by company size")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    return _save_fig_to_buffer(fig)


def figure_education(edu_counts: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.bar(edu_counts["education_required"], edu_counts["count"], color="#553c9a")
    ax.set_ylabel("Job postings")
    ax.set_xlabel("Education required")
    ax.set_title("Distribution of required education")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    fig.tight_layout()
    return _save_fig_to_buffer(fig)


def figure_benefits_tier(
    benefits_tier: pd.DataFrame | None, skills_results: dict, df: pd.DataFrame
) -> io.BytesIO | None:
    if benefits_tier is None or len(benefits_tier) == 0:
        return None
    _setup_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), gridspec_kw={"width_ratios": [2.2, 1.2]})
    ax_left, ax_right = axes
    tiers = [str(t) for t in benefits_tier["benefits_tier"]]

    raw = df.dropna(subset=["salary_usd", "benefits_score"]).copy()
    raw["salary_usd"] = pd.to_numeric(raw["salary_usd"], errors="coerce")
    raw["benefits_score"] = pd.to_numeric(raw["benefits_score"], errors="coerce")
    raw["benefits_tier"] = pd.qcut(
        raw["benefits_score"], q=3, labels=["Low", "Medium", "High"], duplicates="drop"
    )
    box_data = [raw.loc[raw["benefits_tier"] == t, "salary_usd"].dropna() for t in tiers]
    bp = ax_left.boxplot(box_data, labels=tiers, showfliers=False, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#f6ad55")
    ax_left.set_ylabel("Salary (USD)")
    ax_left.set_title("Salary distribution by benefits tier")
    ax_left.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))

    overall_mean = float(raw["salary_usd"].mean())
    deltas = [float(v - overall_mean) for v in benefits_tier["avg_salary"]]
    colors_delta = ["#38a169" if d >= 0 else "#e53e3e" for d in deltas]
    ax_right.bar(tiers, deltas, color=colors_delta)
    ax_right.axhline(0, color="black", linewidth=1)
    ax_right.set_title("Delta vs overall mean")
    ax_right.set_ylabel("Mean salary delta (USD)")
    ax_right.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.1f}k"))
    for idx, delta in enumerate(deltas):
        ax_right.text(idx, delta, f"{delta:+.0f}", ha="center", va="bottom", fontsize=8)
    corr = skills_results.get("benefits_correlation")
    if corr is not None and not pd.isna(corr):
        ax_left.text(
            0.02,
            0.98,
            f"Pearson r (benefits vs salary): {corr:.4f}",
            transform=ax_left.transAxes,
            va="top",
            fontsize=9,
        )
    fig.suptitle("Benefits and compensation: distribution and effect size", y=1.02)
    fig.tight_layout()
    return _save_fig_to_buffer(fig)


def figure_remote(remote_stats: pd.DataFrame, df: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    labels = [f"{int(r)}% remote" for r in remote_stats["remote_ratio"]]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.2), gridspec_kw={"width_ratios": [2.2, 1.2]})
    ax_left, ax_right = axes

    raw = df.dropna(subset=["salary_usd", "remote_ratio"]).copy()
    raw["salary_usd"] = pd.to_numeric(raw["salary_usd"], errors="coerce")
    raw["remote_ratio"] = pd.to_numeric(raw["remote_ratio"], errors="coerce")
    box_data = [raw.loc[raw["remote_ratio"] == int(r), "salary_usd"].dropna() for r in remote_stats["remote_ratio"]]
    bp = ax_left.boxplot(box_data, labels=labels, showfliers=False, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#81e6d9")
    ax_left.set_ylabel("Salary (USD)")
    ax_left.set_title("Salary distribution by remote ratio")
    ax_left.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))

    overall_mean = float(raw["salary_usd"].mean())
    deltas = [float(v - overall_mean) for v in remote_stats["avg_salary"]]
    colors_delta = ["#38a169" if d >= 0 else "#e53e3e" for d in deltas]
    ax_right.bar(labels, deltas, color=colors_delta)
    ax_right.axhline(0, color="black", linewidth=1)
    ax_right.set_title("Delta vs overall mean")
    ax_right.set_ylabel("Mean salary delta (USD)")
    ax_right.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.1f}k"))
    for idx, delta in enumerate(deltas):
        ax_right.text(idx, delta, f"{delta:+.0f}", ha="center", va="bottom", fontsize=8)
    fig.suptitle("Remote policy and compensation: distribution and effect size", y=1.02)
    fig.tight_layout()
    return _save_fig_to_buffer(fig)


def figure_salary_progression_line(exp_stats: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    labels = [EXPERIENCE_LABELS.get(x, str(x)) for x in exp_stats["experience_level"]]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(labels, exp_stats["avg_salary"], marker="o", linewidth=2.2, color=PALETTE["primary"])
    ax.fill_between(labels, exp_stats["avg_salary"], alpha=0.12, color=PALETTE["primary"])
    ax.set_title("Salary progression across experience bands")
    ax.set_ylabel("Mean salary (USD)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    return _save_fig_to_buffer(fig)


def figure_benefits_scatter(df: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    d = df.dropna(subset=["salary_usd", "benefits_score"]).copy()
    d["salary_usd"] = pd.to_numeric(d["salary_usd"], errors="coerce")
    d["benefits_score"] = pd.to_numeric(d["benefits_score"], errors="coerce")
    if len(d) > 2500:
        d = d.sample(2500, random_state=42)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(d["benefits_score"], d["salary_usd"], s=9, alpha=0.25, color=PALETTE["secondary"])
    ax.set_title("Benefits score vs salary (sampled scatter)")
    ax.set_xlabel("Benefits score")
    ax.set_ylabel("Salary (USD)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    return _save_fig_to_buffer(fig)


def figure_top_skills(skills_df: pd.DataFrame) -> io.BytesIO | None:
    if skills_df is None or len(skills_df) == 0:
        return None
    _setup_matplotlib()
    d = skills_df.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.barh(d["skill"], d["count"], color=PALETTE["accent"])
    ax.set_title("Top in-demand skills in AI postings")
    ax.set_xlabel("Posting count")
    return _save_fig_to_buffer(fig)


def figure_top_roles(df: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    d = (
        df["job_title"]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
        .head(8)
        .sort_values(ascending=True)
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.barh(d.index, d.values, color=PALETTE["primary"])
    ax.set_title("Role evolution signal: top job titles by demand")
    ax.set_xlabel("Posting count")
    return _save_fig_to_buffer(fig)


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _fmt_usd(value: float) -> str:
    return f"${value:,.0f}"


def _safe_pct_change(new: float, base: float) -> float | None:
    if base == 0:
        return None
    return (new - base) / base


def _salary_row(exp: pd.DataFrame, code: str) -> float | None:
    row = exp.loc[exp["experience_level"] == code, "avg_salary"]
    if len(row) == 0:
        return None
    v = row.iloc[0]
    if pd.isna(v):
        return None
    return float(v)


def _build_pdf_section_lines(
    total_records: int, salary_results: dict, skills_results: dict, remote_results: dict
) -> list[str]:
    exp = salary_results["avg_salary_by_experience"]
    exp_map = dict(zip(exp["experience_level"], exp["avg_salary"]))
    top_industries = salary_results["top_industries"].head(5).reset_index(drop=True)
    size_df = salary_results["company_size_salary"]
    size_map = dict(zip(size_df["company_size"], size_df["avg_salary"]))
    edu_counts = skills_results["education_counts"]
    most_edu = skills_results["most_common_education"]
    ben_corr = skills_results["benefits_correlation"]
    ben_tier = skills_results["benefits_salary_by_tier"]
    top_skills = skills_results.get("top_skills", pd.DataFrame(columns=["skill", "count"]))
    remote = remote_results["remote_salary_stats"]
    remote_map = dict(zip(remote["remote_ratio"], remote["avg_salary"]))
    remote_corr = remote_results["remote_salary_correlation"]

    en = exp_map.get("EN", float("nan"))
    ex = exp_map.get("EX", float("nan"))
    salary_obs = (
        f"Executive roles earn about {((ex - en) / en) * 100:.1f}% more than entry-level roles."
        if pd.notna(en) and pd.notna(ex) and en != 0
        else "Salary clearly increases with experience level."
    )
    ben_interp = (
        "Weak positive correlation between benefits score and salary."
        if pd.notna(ben_corr) and ben_corr > 0
        else "Weak negative/no meaningful linear correlation between benefits score and salary."
    )
    remote_interp = (
        "Remote work has minimal impact on salary in this sample."
        if pd.notna(remote_corr) and abs(remote_corr) < 0.1
        else "Remote ratio appears related to salary, but effect size is still limited."
    )

    lines = [
        "AI JOB MARKET ANALYSIS REPORT",
        "Overview",
        "This report analyzes global AI job listings to uncover trends in salary, experience levels, company characteristics, education requirements, and remote work patterns.",
        f"Total Records Analyzed: {total_records:,}",
        f"Date Generated: {date.today().isoformat()}",
        "",
        "1. Salary Insights",
        f"Average Salary by Experience Level: EN {_fmt_usd(en) if pd.notna(en) else 'n/a'}, "
        f"MI {_fmt_usd(exp_map.get('MI', float('nan'))) if pd.notna(exp_map.get('MI', float('nan'))) else 'n/a'}, "
        f"SE {_fmt_usd(exp_map.get('SE', float('nan'))) if pd.notna(exp_map.get('SE', float('nan'))) else 'n/a'}, "
        f"EX {_fmt_usd(ex) if pd.notna(ex) else 'n/a'}",
        f"Key Observation: {salary_obs}",
        "Top 5 Highest Paying Industries:",
    ]
    for i, row in top_industries.iterrows():
        lines.append(f"{i + 1}. {row['industry']} ({_fmt_usd(float(row['avg_salary']))})")
    lines.append("Top 5 Most Important Skills (by demand):")
    if len(top_skills) > 0:
        for i, row in top_skills.reset_index(drop=True).iterrows():
            lines.append(f"{i + 1}. {row['skill']} ({int(row['count']):,} postings)")
    else:
        lines.append("- n/a")
    lines.extend(
        [
            f"Company Size vs Salary: Small {_fmt_usd(size_map.get('S', float('nan'))) if pd.notna(size_map.get('S', float('nan'))) else 'n/a'}, "
            f"Medium {_fmt_usd(size_map.get('M', float('nan'))) if pd.notna(size_map.get('M', float('nan'))) else 'n/a'}, "
            f"Large {_fmt_usd(size_map.get('L', float('nan'))) if pd.notna(size_map.get('L', float('nan'))) else 'n/a'}",
            "Interpretation: Experience and company size are strong salary differentiators in this dataset.",
            "Interpretation: Industry ranks are meaningful, but salary gaps among top industries are moderate.",
            "",
            "2. Education & Benefits Analysis",
            f"Most Common Education Requirement: {most_edu if most_edu is not None else 'n/a'}",
            (
                f"Education Distribution: {edu_counts.iloc[0]['education_required']} leads ({edu_counts.iloc[0]['count']:,}), "
                f"followed by {edu_counts.iloc[1]['education_required']} ({edu_counts.iloc[1]['count']:,})."
                if len(edu_counts) >= 2
                else "Education Distribution: not enough data."
            ),
            f"Benefits vs Salary Correlation: {ben_corr:.4f}" if pd.notna(ben_corr) else "Benefits vs Salary Correlation: n/a",
            f"Interpretation: {ben_interp}",
        ]
    )
    if ben_tier is not None and len(ben_tier) > 0:
        tier_vals = ", ".join([f"{row['benefits_tier']} {_fmt_usd(float(row['avg_salary']))}" for _, row in ben_tier.iterrows()])
        lines.append(f"Salary by Benefits Tier: {tier_vals}")
    else:
        lines.append("Salary by Benefits Tier: n/a")
    lines.extend(
        [
            "Interpretation: Benefits score has limited explanatory power for salary in this sample.",
            "",
            "3. Remote Work Trends",
            f"Salary by Remote Ratio: On-site {_fmt_usd(remote_map.get(0, float('nan'))) if pd.notna(remote_map.get(0, float('nan'))) else 'n/a'}, "
            f"Hybrid {_fmt_usd(remote_map.get(50, float('nan'))) if pd.notna(remote_map.get(50, float('nan'))) else 'n/a'}, "
            f"Fully Remote {_fmt_usd(remote_map.get(100, float('nan'))) if pd.notna(remote_map.get(100, float('nan'))) else 'n/a'}",
            f"Remote vs Salary Correlation: {remote_corr:.4f}" if pd.notna(remote_corr) else "Remote vs Salary Correlation: n/a",
            f"Interpretation: {remote_interp}",
            "Interpretation: Remote ratio contributes only marginal salary differences compared with role seniority.",
            "",
            "4. Key Takeaways",
            "The most influential factor in salary is experience level.",
            f"The highest paying segment in this sample is {top_industries.iloc[0]['industry']}.",
            "Remote work impact is directionally positive but practically small.",
            f"Education requirements trend shows {most_edu if most_edu is not None else 'n/a'} as dominant.",
            "",
            "5. Limitations",
            "Missing salary values may affect accuracy.",
            "Correlation does not imply causation.",
            "Dataset may not represent all global markets.",
        ]
    )
    return lines


def generate_board_pdf(
    output_path: Path | str,
    df: pd.DataFrame,
    salary_results: dict,
    skills_results: dict,
    remote_results: dict,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="Title", parent=styles["Heading1"], fontSize=28, textColor=colors.HexColor(PALETTE["ink"]), spaceAfter=10)
    subtitle_style = ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=13, textColor=colors.HexColor(PALETTE["muted"]), leading=18, spaceAfter=8)
    h1 = ParagraphStyle(name="H1", parent=styles["Heading1"], fontSize=20, textColor=colors.HexColor(PALETTE["primary"]), spaceBefore=8, spaceAfter=8)
    h2 = ParagraphStyle(name="H2", parent=styles["Heading2"], fontSize=15, textColor=colors.HexColor(PALETTE["ink"]), spaceBefore=6, spaceAfter=6)
    body = ParagraphStyle(name="Body", parent=styles["Normal"], fontSize=10.5, leading=14.5, spaceAfter=8)
    quote = ParagraphStyle(name="Quote", parent=styles["Normal"], fontSize=11, leading=15, textColor=colors.HexColor(PALETTE["secondary"]), leftIndent=16, rightIndent=16, spaceAfter=10)
    kpi = ParagraphStyle(name="KPI", parent=styles["Heading1"], fontSize=22, textColor=colors.HexColor(PALETTE["accent"]), spaceAfter=2)
    small = ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor(PALETTE["muted"]))

    n_rows = len(df)
    exp = salary_results["avg_salary_by_experience"]
    top_ind = salary_results["top_industries"]
    size_df = salary_results["company_size_salary"]
    skills_df = skills_results.get("top_skills", pd.DataFrame(columns=["skill", "count"]))
    ben_corr = skills_results["benefits_correlation"]
    rem_corr = remote_results["remote_salary_correlation"]
    rem_stats = remote_results["remote_salary_stats"]
    en_sal = _salary_row(exp, "EN")
    ex_sal = _salary_row(exp, "EX")

    growth_ratio = (ex_sal / en_sal) if (en_sal and ex_sal and en_sal > 0) else None
    premium_large = None
    try:
        s = float(size_df.loc[size_df["company_size"] == "S", "avg_salary"].iloc[0])
        l = float(size_df.loc[size_df["company_size"] == "L", "avg_salary"].iloc[0])
        premium_large = ((l - s) / s) * 100 if s else None
    except Exception:
        premium_large = None

    story: list = []
    chart_width = 6.4 * inch

    # 1) Cover page
    story.append(Spacer(1, 1.2 * inch))
    story.append(_p("AI JOB MARKET ANALYSIS REPORT 2026", title_style))
    story.append(_p("Fearless Hiring Futures: executive signals from 15,000 AI job postings", subtitle_style))
    story.append(_p("An investor-grade briefing for boards, CHROs, and workforce strategy leaders.", body))
    story.append(Spacer(1, 0.3 * inch))
    story.append(_p(f"Date: {date.today().isoformat()}", small))
    story.append(PageBreak())

    # 2) Key findings
    story.append(_p("Key Findings", h1))
    story.append(_p("Signal blocks", h2))
    story.append(_p(f"{growth_ratio:.2f}x", kpi) if growth_ratio is not None else _p("n/a", kpi))
    story.append(_p("Salary multiple from entry to executive roles", small))
    story.append(_p(f"+{premium_large:.1f}%", kpi) if premium_large is not None else _p("n/a", kpi))
    story.append(_p("Large-company salary premium vs small companies", small))
    story.append(_p(f"{abs(rem_corr):.4f}", kpi) if pd.notna(rem_corr) else _p("n/a", kpi))
    story.append(_p("Remote-to-salary linear correlation (very low)", small))
    story.append(_p(f"{len(skills_df):,}", kpi))
    story.append(_p("Top skills surfaced in demand shortlist", small))
    story.append(Spacer(1, 0.14 * inch))
    story.append(_p("Productivity / Market Growth: Compensation expands steeply across experience bands, signaling that value capture in AI labor markets is concentrated at senior levels.", body))
    story.append(_p("Hiring Trends: Industry pay leaders are close in average salary, but role seniority and firm size create larger pay deltas than policy variables like remote ratio.", body))
    story.append(_p("Skill Evolution: A concentrated cluster of technical skills dominates demand, indicating standardization in stack expectations across employers.", body))
    story.append(PageBreak())

    # 3) Implications
    story.append(_p("5 Implications for Executive Teams", h1))
    implications = [
        ("1) Design compensation architecture around capability depth", "The largest salary step changes are tied to experience bands; progression paths should reward deep, scarce AI capability."),
        ("2) Compete on role design, not remote policy alone", "Remote status has weak salary linkage; value proposition should emphasize project quality and learning velocity."),
        ("3) Treat skills as portfolio bets", "Top skills represent core market currency; workforce plans should balance foundational and emerging competencies."),
        ("4) Prioritize sector benchmarking in talent strategy", "Top industries cluster tightly, so winning talent may depend more on speed and role narrative than absolute pay."),
        ("5) Integrate workforce analytics into board cadence", "Observed patterns are dynamic and should be monitored quarterly to support hiring, retention, and reskilling decisions."),
    ]
    for head, expl in implications:
        story.append(_p(head, h2))
        story.append(_p(expl, body))
    story.append(PageBreak())

    # 4+) Numbered insights
    story.append(_p("01 | Market Productivity / Growth", h1))
    story.append(_p("The market exhibits a sharp compensation slope from entry to executive levels, indicating economic value concentrates in advanced AI delivery capability.", body))
    story.append(_rl_image_from_buffer(figure_salary_progression_line(exp), chart_width))
    story.append(_p("Insight callout: Capability maturity, not just participation in AI hiring, is where premium value is realized.", quote))
    story.append(PageBreak())

    story.append(_p("02 | Salaries / Value", h1))
    story.append(_p("Industry-level comparisons show competitive pay bands among leaders, with consulting currently at the top of this dataset.", body))
    story.append(_rl_image_from_buffer(figure_industry_salary(top_ind), chart_width))
    story.append(_p("Data explanation: The chart ranks mean salary by industry; adjacent leaders are close, so non-pay differentiators remain strategic.", body))
    story.append(PageBreak())

    story.append(_p("03 | Job Demand", h1))
    story.append(_p("Demand concentrates around a practical technical core, with Python, SQL, and ML platform skills forming a repeatable baseline.", body))
    skills_buf = figure_top_skills(skills_df)
    if skills_buf is not None:
        story.append(_rl_image_from_buffer(skills_buf, chart_width))
    story.append(_p("Persona - Developer: \"A backend engineer adding Python + SQL + MLOps capabilities can move from support roles into higher-value AI delivery tracks within 12 months.\"", quote))
    story.append(PageBreak())

    story.append(_p("04 | Transformation / Strategy", h1))
    story.append(_p("Firm scale continues to matter in compensation outcomes, suggesting resource depth and program complexity influence talent pricing.", body))
    story.append(_rl_image_from_buffer(figure_company_size(size_df), chart_width))
    story.append(_p("Insight callout: Organizations can offset pay gaps with accelerated career pathways and high-visibility AI problem ownership.", quote))
    story.append(PageBreak())

    story.append(_p("05 | Skills Shift", h1))
    story.append(_p("Benefits score has near-zero linear correlation with salary. The market appears to reward direct capability contribution more than generalized package differentiation.", body))
    story.append(_rl_image_from_buffer(figure_benefits_scatter(df), chart_width))
    story.append(_p(f"Data explanation: Pearson correlation (benefits vs salary) = {ben_corr:.4f}" if pd.notna(ben_corr) else "Data explanation: correlation unavailable.", body))
    story.append(PageBreak())

    story.append(_p("06 | Role Evolution", h1))
    story.append(_p("Role demand indicates an ecosystem moving from experimentation to scaled operationalization across data, engineering, and AI-specialist roles.", body))
    story.append(_rl_image_from_buffer(figure_top_roles(df), chart_width))
    story.append(_p("Persona - Analyst: \"A data analyst adding model monitoring and cloud workflow skills can transition into AI operations roles with stronger pay trajectories.\"", quote))
    story.append(PageBreak())

    story.append(_p("07 | Myth Busting", h1))
    story.append(_p("Myth: remote-first roles inherently command a major salary premium. Reality: this dataset shows only marginal differences across 0%, 50%, and 100% remote categories.", body))
    story.append(_rl_image_from_buffer(figure_remote(rem_stats, df), chart_width))
    story.append(_p("Insight callout: Work modality influences access and flexibility, but appears secondary to capability and role scope in pay formation.", quote))
    story.append(PageBreak())

    story.append(_p("08 | Additional Insight: Education Signal", h1))
    story.append(_p("Education requirements remain broad, with bachelor-level credentials most common. This supports mixed pipelines combining formal education and capability-based hiring.", body))
    story.append(_rl_image_from_buffer(figure_education(skills_results["education_counts"]), chart_width))
    story.append(_p("Persona - Student: \"A bachelor graduate who pairs academic depth with deployable portfolio projects can close readiness gaps faster than degree-only peers.\"", quote))
    story.append(PageBreak())

    # Final conclusion
    story.append(_p("Conclusion / Future Outlook", h1))
    story.append(_p("AI labor markets are transitioning from experimentation to execution. Salary premiums are primarily driven by experience depth and organizational context, while remote policy and benefits show weaker direct influence. The strategic imperative for leaders is clear: build capability pipelines, align progression frameworks to high-impact skills, and institutionalize market sensing to stay ahead of talent shifts.", body))
    story.append(_p("Method note: This report is based on the provided job-posting dataset and should be interpreted as directional market intelligence rather than causal proof.", small))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    doc.build(story)
    return output_path


def generate_structured_markdown(
    output_path: Path | str,
    df: pd.DataFrame,
    salary_results: dict,
    skills_results: dict,
    remote_results: dict,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    exp = salary_results["avg_salary_by_experience"]
    exp_map = dict(zip(exp["experience_level"], exp["avg_salary"]))
    top_ind = salary_results["top_industries"].head(5)
    top_skills = skills_results.get("top_skills", pd.DataFrame(columns=["skill", "count"]))
    rem_corr = remote_results["remote_salary_correlation"]
    ben_corr = skills_results["benefits_correlation"]
    lines = [
        "# AI JOB MARKET ANALYSIS REPORT",
        "",
        "## Cover",
        "AI JOB MARKET ANALYSIS REPORT 2026  ",
        "Fearless Hiring Futures: executive signals from AI labor markets",
        "",
        "## Key Findings",
        f"- **Total records analyzed:** {len(df):,}",
        f"- **Entry to executive salary multiple:** {(exp_map.get('EX', float('nan')) / exp_map.get('EN', float('nan'))):.2f}x",
        f"- **Remote-salary correlation:** {rem_corr:.4f}" if pd.notna(rem_corr) else "- **Remote-salary correlation:** n/a",
        f"- **Benefits-salary correlation:** {ben_corr:.4f}" if pd.notna(ben_corr) else "- **Benefits-salary correlation:** n/a",
        "",
        "## Implications",
        "1. Compensation strategy should emphasize capability depth.",
        "2. Remote policy should be positioned as access/flexibility, not salary determinant.",
        "3. Skills investment should prioritize repeatedly demanded technical capabilities.",
        "4. Sector benchmarking should be refreshed quarterly.",
        "5. Workforce analytics should be embedded in board governance.",
        "",
        "## Insight 01 | Market Productivity / Growth",
        "Salary progression across experience bands indicates strong value concentration at higher seniority.",
        "",
        "## Insight 02 | Salaries / Value",
        "Top-paying industries:",
    ]
    for i, row in top_ind.reset_index(drop=True).iterrows():
        lines.append(f"{i + 1}. {row['industry']} (${row['avg_salary']:,.0f})")
    lines.extend(["", "## Insight 03 | Job Demand", "Top skills by posting demand:"])
    for i, row in top_skills.head(5).reset_index(drop=True).iterrows():
        lines.append(f"{i + 1}. {row['skill']} ({int(row['count']):,})")
    lines.extend(
        [
            "",
            "## Insight 04 | Transformation / Strategy",
            "Company scale remains associated with salary levels.",
            "",
            "## Insight 05 | Skills Shift",
            "Benefits score has weak linear relationship with salary.",
            "",
            "## Insight 06 | Role Evolution",
            "Role mix indicates shift toward operational AI capabilities.",
            "",
            "## Insight 07 | Myth Busting",
            "Remote status alone does not strongly explain salary differences.",
            "",
            "## Conclusion / Future Outlook",
            "The AI job market rewards capability maturity and execution depth; leaders should align talent strategy to skill velocity and role evolution.",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
