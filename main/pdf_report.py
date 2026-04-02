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
    benefits_tier: pd.DataFrame | None, skills_results: dict
) -> io.BytesIO | None:
    if benefits_tier is None or len(benefits_tier) == 0:
        return None
    _setup_matplotlib()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    tiers = [str(t) for t in benefits_tier["benefits_tier"]]
    ax.bar(tiers, benefits_tier["avg_salary"], color="#c05621")
    ax.set_ylabel("Mean salary (USD)")
    ax.set_title("Mean salary by benefits score tier (tertiles)")
    corr = skills_results.get("benefits_correlation")
    if corr is not None and not pd.isna(corr):
        ax.text(
            0.02,
            0.98,
            f"Pearson r (benefits vs salary): {corr:.4f}",
            transform=ax.transAxes,
            va="top",
            fontsize=9,
        )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    return _save_fig_to_buffer(fig)


def figure_remote(remote_stats: pd.DataFrame) -> io.BytesIO:
    _setup_matplotlib()
    labels = [f"{int(r)}% remote" for r in remote_stats["remote_ratio"]]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.bar(labels, remote_stats["avg_salary"], color="#285e61")
    ax.set_ylabel("Mean salary (USD)")
    ax.set_title("Mean salary by remote work ratio")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v / 1000:.0f}k"))
    return _save_fig_to_buffer(fig)


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _salary_row(exp: pd.DataFrame, code: str) -> float | None:
    row = exp.loc[exp["experience_level"] == code, "avg_salary"]
    if len(row) == 0:
        return None
    v = row.iloc[0]
    if pd.isna(v):
        return None
    return float(v)


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
    title_style = ParagraphStyle(
        name="BoardTitle",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=16,
        textColor=colors.HexColor("#1a365d"),
    )
    h2 = ParagraphStyle(
        name="BoardH2",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=10,
        textColor=colors.HexColor("#2c5282"),
    )
    body = ParagraphStyle(
        name="BoardBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=10,
    )
    small = ParagraphStyle(
        name="BoardSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
    )

    n_rows = len(df)
    exp = salary_results["avg_salary_by_experience"]
    top_ind = salary_results["top_industries"]
    size_df = salary_results["company_size_salary"]
    best_industry = str(top_ind.iloc[0]["industry"])
    best_ind_salary = float(top_ind.iloc[0]["avg_salary"])
    most_edu = skills_results["most_common_education"]
    ben_corr = skills_results["benefits_correlation"]
    rem_corr = remote_results["remote_salary_correlation"]
    rem_stats = remote_results["remote_salary_stats"]

    en_sal = _salary_row(exp, "EN")
    ex_sal = _salary_row(exp, "EX")
    exp_sentence = (
        f"Mean salary rises with seniority, from about ${en_sal / 1000:.0f}k at entry level "
        f"to about ${ex_sal / 1000:.0f}k for executive roles."
        if en_sal is not None and ex_sal is not None
        else "Mean salary rises with seniority across experience bands (see chart)."
    )

    exec_lines = [
        (
            f"This briefing summarizes compensation and related attributes across {n_rows:,} job postings "
            "in the analyzed AI job dataset. Figures use the same aggregations as the tabular analysis; "
            "all associations are descriptive, not causal."
        ),
        exp_sentence,
        (
            f"The industry with the highest mean salary in this sample is {best_industry} "
            f"(approximately ${best_ind_salary:,.0f}). Rankings should be read alongside posting volume, "
            "because thin segments can move averages."
        ),
        (
            f"Mean pay increases from small to large company size in these data, and the most common "
            f"required education level is {most_edu}."
        ),
    ]
    if ben_corr is not None and not pd.isna(ben_corr):
        exec_lines.append(
            "The Pearson correlation between benefits score and salary is near zero in this dataset "
            f"(r ≈ {ben_corr:.4f}), so higher benefits scores do not linearly track higher salaries here."
        )
    if rem_corr is not None and not pd.isna(rem_corr):
        exec_lines.append(
            f"Mean salary increases modestly with remote ratio (0%, 50%, 100%); the Pearson correlation "
            f"with salary is {rem_corr:.4f}."
        )

    story: list = []
    chart_width = 6.3 * inch

    story.append(_p("AI job market analysis", title_style))
    story.append(_p(f"Board briefing - {date.today().isoformat()}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))
    story.append(_p("Executive summary", h2))
    for para in exec_lines:
        story.append(_p(para, body))

    story.append(PageBreak())
    story.append(_p("1. Experience and compensation", h2))
    story.append(
        _p(
            "Experience level is a primary lens for pay structure: both mean and median salaries increase "
            "from entry through executive roles. The chart reflects the same group summaries used elsewhere "
            "in the analysis pipeline.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(_rl_image_from_buffer(figure_experience_salary(exp), chart_width))

    story.append(Spacer(1, 0.2 * inch))
    story.append(_p("2. Industry benchmarks", h2))
    story.append(
        _p(
            "Industries are compared using mean salary. The visualization highlights the top industries; "
            "leadership should treat leaders and laggards as indicative, not definitive, without controls "
            "for role mix and geography.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(_rl_image_from_buffer(figure_industry_salary(top_ind), chart_width))

    story.append(PageBreak())
    story.append(_p("3. Company size", h2))
    story.append(
        _p(
            "Company size uses categories S, M, and L. Larger employers show higher average salaries in this "
            "snapshot, which may reflect role seniority, bargaining power, or sector mix rather than size alone.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(_rl_image_from_buffer(figure_company_size(size_df), chart_width))

    story.append(Spacer(1, 0.2 * inch))
    story.append(_p("4. Education requirements", h2))
    story.append(
        _p(
            "The frequency of required education informs hiring and training strategy. The modal requirement "
            "is the single most common category in the sample.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(_rl_image_from_buffer(figure_education(skills_results["education_counts"]), chart_width))

    story.append(PageBreak())
    story.append(_p("5. Benefits score and salary", h2))
    story.append(
        _p(
            "Benefits scores are split into low, medium, and high tertiles to show mean salary by tier, "
            "alongside the correlation note on the chart.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    ben_buf = figure_benefits_tier(skills_results["benefits_salary_by_tier"], skills_results)
    if ben_buf is not None:
        story.append(_rl_image_from_buffer(ben_buf, chart_width))
    else:
        story.append(_p("Benefits tier chart was not produced (bucketing unavailable for this sample).", body))

    story.append(Spacer(1, 0.2 * inch))
    story.append(_p("6. Remote work and compensation", h2))
    story.append(
        _p(
            "Remote ratio is observed at 0%, 50%, and 100%. Average pay differs modestly across these "
            "buckets; interpretation should note that remote policy may correlate with role type.",
            body,
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(_rl_image_from_buffer(figure_remote(rem_stats), chart_width))

    story.append(PageBreak())
    story.append(_p("Methodology and limitations", h2))
    story.append(
        _p(
            "Data were loaded from the project CSV; dates were parsed for quality control. Statistics are "
            "simple means, medians, counts, and Pearson correlations where stated. Results do not control for "
            "confounders such as location, seniority beyond coarse bands, or company-specific pay policy.",
            body,
        )
    )
    story.append(Spacer(1, 0.25 * inch))
    story.append(_p("Prepared for internal discussion.", small))

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
