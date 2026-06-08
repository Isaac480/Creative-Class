"""Analyze face-rating experiment.

Outputs go to ./analysis/. Run with the project venv activated:
    python analyze.py
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

DATA_DIR = Path("exported_data")
OUT_DIR = Path("analysis")
OUT_DIR.mkdir(exist_ok=True)

DROP_PARTICIPANTS = {1, 2, 3, 4, 5, 6, 11}

LIKERT_5_AGREE = {
    "strongly disagree": 1, "disagree": 2,
    "neither agree nor disagree": 3, "neutral": 3,
    "agree": 4, "strongly agree": 5,
}
LIKERT_4_EASY = {"very easy": 1, "easy": 2, "hard": 3, "very hard": 4}
LIKERT_7_PARENS = re.compile(r"\((\d+)\)\s*$")


def likert_to_num(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    s = str(val).strip()
    m = LIKERT_7_PARENS.search(s)
    if m:
        return int(m.group(1))
    low = s.lower()
    if low in LIKERT_5_AGREE:
        return LIKERT_5_AGREE[low]
    if low in LIKERT_4_EASY:
        return LIKERT_4_EASY[low]
    try:
        return float(s)
    except ValueError:
        return np.nan


def face_id(stim: str) -> str:
    # "src/images/jpg/Modified Faces/13 copy.jpg" -> "13"
    base = os.path.splitext(os.path.basename(str(stim)))[0]
    base = base.replace(" copy", "").strip()
    return base


# ---------------------------------------------------------------------------
# 1. Load and filter face-rating trials
# ---------------------------------------------------------------------------
trials = pd.read_csv(DATA_DIR / "all_participants_trials.csv")
trials = trials[~trials["participant_id"].isin(DROP_PARTICIPANTS)].copy()
trials["face"] = trials["stimulus"].map(face_id)
trials["rating"] = pd.to_numeric(trials["response"], errors="coerce")
trials = trials.sort_values(["participant_id", "trial_index"]).reset_index(drop=True)

participants = sorted(trials["participant_id"].unique())
print(f"Participants kept: {participants}  (n={len(participants)})")
print(f"Total trials: {len(trials)}   unique faces: {trials['face'].nunique()}")

# Mark retest presentations: within a participant, first occurrence vs second
trials["presentation"] = trials.groupby(["participant_id", "face"]).cumcount() + 1

# ---------------------------------------------------------------------------
# 2. Per-face ratings: summary table + strip plot
# ---------------------------------------------------------------------------
face_summary = (
    trials.groupby("face")["rating"]
    .agg(["count", "mean", "std", "min", "max"])
    .sort_values("mean")
    .reset_index()
)
face_summary.to_csv(OUT_DIR / "face_ratings_summary.csv", index=False)

face_order = face_summary["face"].tolist()
face_to_y = {f: i for i, f in enumerate(face_order)}

colors = plt.cm.tab10(np.linspace(0, 1, len(participants)))
p_to_color = dict(zip(participants, colors))

fig, ax = plt.subplots(figsize=(9, 14))
for _, row in trials.iterrows():
    y = face_to_y[row["face"]] + np.random.uniform(-0.18, 0.18)
    ax.scatter(
        row["rating"], y,
        color=p_to_color[row["participant_id"]],
        alpha=0.7, s=22,
    )
# Mean marker
ax.scatter(
    face_summary["mean"],
    [face_to_y[f] for f in face_summary["face"]],
    marker="|", color="black", s=120, linewidths=2, label="mean",
)
ax.set_yticks(range(len(face_order)))
ax.set_yticklabels(face_order, fontsize=7)
ax.set_xlabel("Rating (0–100 slider)")
ax.set_ylabel("Face (sorted by mean rating, low → high)")
ax.set_title(f"Ratings per face — {len(participants)} participants\n(retest faces contribute 2 points/participant)")
handles = [
    plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=p_to_color[p], markersize=8, label=f"P{p}")
    for p in participants
]
handles.append(plt.Line2D([0], [0], marker="|", color="black", markersize=12, label="mean", linestyle="None"))
ax.legend(handles=handles, loc="lower right", fontsize=8)
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(OUT_DIR / "face_ratings_stripplot.png", dpi=150)
plt.close(fig)
print("Wrote face_ratings_stripplot.png + face_ratings_summary.csv")

# ---------------------------------------------------------------------------
# 3. Test-retest reliability (faces presented twice within a participant)
# ---------------------------------------------------------------------------
retest_faces = (
    trials.groupby(["participant_id", "face"]).size().reset_index(name="n").query("n == 2")
)
pairs = []
for _, row in retest_faces.iterrows():
    sub = trials[(trials["participant_id"] == row["participant_id"]) & (trials["face"] == row["face"])].sort_values("trial_index")
    r1, r2 = sub["rating"].iloc[0], sub["rating"].iloc[1]
    rt1, rt2 = sub["rt"].iloc[0], sub["rt"].iloc[1]
    t1, t2 = sub["trial_index"].iloc[0], sub["trial_index"].iloc[1]
    pairs.append({
        "participant_id": row["participant_id"], "face": row["face"],
        "rating1": r1, "rating2": r2, "diff": r2 - r1, "abs_diff": abs(r2 - r1),
        "rt1": rt1, "rt2": rt2, "trial1": t1, "trial2": t2,
    })
pairs_df = pd.DataFrame(pairs)
pairs_df.to_csv(OUT_DIR / "testretest_pairs.csv", index=False)

# Per-participant + overall metrics
per_p_rows = []
for p in participants:
    sub = pairs_df[pairs_df["participant_id"] == p]
    r, _ = stats.pearsonr(sub["rating1"], sub["rating2"])
    per_p_rows.append({
        "participant_id": p,
        "n_retest_faces": len(sub),
        "pearson_r": r,
        "mean_abs_diff": sub["abs_diff"].mean(),
        "median_abs_diff": sub["abs_diff"].median(),
        "mean_signed_diff": sub["diff"].mean(),  # >0 = ratings drift up on 2nd presentation
    })
r_overall, p_overall = stats.pearsonr(pairs_df["rating1"], pairs_df["rating2"])
per_p_rows.append({
    "participant_id": "ALL",
    "n_retest_faces": len(pairs_df),
    "pearson_r": r_overall,
    "mean_abs_diff": pairs_df["abs_diff"].mean(),
    "median_abs_diff": pairs_df["abs_diff"].median(),
    "mean_signed_diff": pairs_df["diff"].mean(),
})
tr_summary = pd.DataFrame(per_p_rows)
tr_summary.to_csv(OUT_DIR / "testretest_summary.csv", index=False)
print(f"Test-retest overall Pearson r = {r_overall:.3f} (p={p_overall:.3g}, n_pairs={len(pairs_df)})")

# Scatter: rating1 vs rating2
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
ax = axes[0]
for p in participants:
    sub = pairs_df[pairs_df["participant_id"] == p]
    ax.scatter(sub["rating1"], sub["rating2"], color=p_to_color[p], label=f"P{p}", s=50, alpha=0.8)
ax.plot([0, 100], [0, 100], "k--", alpha=0.4, label="y = x")
ax.set_xlabel("Rating on 1st presentation")
ax.set_ylabel("Rating on 2nd presentation")
ax.set_title(f"Test–retest scatter (overall r = {r_overall:.2f})")
ax.legend(fontsize=8)
ax.set_aspect("equal")
ax.grid(alpha=0.3)

# Bland-Altman
ax = axes[1]
mean_rating = (pairs_df["rating1"] + pairs_df["rating2"]) / 2
diff = pairs_df["rating2"] - pairs_df["rating1"]
for p in participants:
    mask = pairs_df["participant_id"] == p
    ax.scatter(mean_rating[mask], diff[mask], color=p_to_color[p], label=f"P{p}", s=50, alpha=0.8)
md = diff.mean()
sd = diff.std()
ax.axhline(md, color="black", linestyle="-", linewidth=1, label=f"mean diff = {md:.1f}")
ax.axhline(md + 1.96 * sd, color="grey", linestyle="--", linewidth=1, label=f"±1.96 SD ({md+1.96*sd:.1f}, {md-1.96*sd:.1f})")
ax.axhline(md - 1.96 * sd, color="grey", linestyle="--", linewidth=1)
ax.set_xlabel("Mean of 1st & 2nd rating")
ax.set_ylabel("2nd − 1st rating")
ax.set_title("Bland–Altman: agreement between presentations")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT_DIR / "testretest_plots.png", dpi=150)
plt.close(fig)
print("Wrote testretest_plots.png + testretest_pairs.csv + testretest_summary.csv")

# ---------------------------------------------------------------------------
# 4. Bonus: per-participant rating distributions + order effects + RT
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)
for ax, p in zip(axes.flat, participants):
    sub = trials[trials["participant_id"] == p]
    ax.hist(sub["rating"], bins=20, range=(0, 100), color=p_to_color[p], alpha=0.85)
    ax.set_title(f"P{p}: mean={sub['rating'].mean():.1f}, SD={sub['rating'].std():.1f}")
    ax.set_xlabel("Rating")
    ax.set_ylabel("Trials")
fig.suptitle("Per-participant rating distributions (scale-use bias check)")
fig.tight_layout()
fig.savefig(OUT_DIR / "rating_distributions.png", dpi=150)
plt.close(fig)

# Order effects: rating vs trial index, smoothed
fig, ax = plt.subplots(figsize=(10, 5))
for p in participants:
    sub = trials[trials["participant_id"] == p].sort_values("trial_index")
    rolling = sub["rating"].rolling(window=10, min_periods=3).mean()
    ax.plot(sub["trial_index"].values, rolling.values, label=f"P{p}", color=p_to_color[p], linewidth=2)
ax.set_xlabel("Trial index")
ax.set_ylabel("Rating (rolling mean, window=10)")
ax.set_title("Order effects: does rating drift over the experiment?")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT_DIR / "order_effects.png", dpi=150)
plt.close(fig)

# RT vs rating
fig, ax = plt.subplots(figsize=(9, 5))
for p in participants:
    sub = trials[trials["participant_id"] == p]
    ax.scatter(sub["rating"], sub["rt"], color=p_to_color[p], alpha=0.5, s=15, label=f"P{p}")
ax.set_xlabel("Rating")
ax.set_ylabel("Response time (ms)")
ax.set_yscale("log")
ax.set_title("RT vs rating per participant")
ax.legend()
ax.grid(alpha=0.3, which="both")
fig.tight_layout()
fig.savefig(OUT_DIR / "rt_vs_rating.png", dpi=150)
plt.close(fig)
print("Wrote rating_distributions.png + order_effects.png + rt_vs_rating.png")

# ---------------------------------------------------------------------------
# 5. Surveys
# ---------------------------------------------------------------------------
SURVEY_LABELS = {
    "surveyForm":  "demographics",
    "survey3Form": "KAI",
    "survey4Form": "Big5_TIPI",
    "survey5Form": "creative_perceptions",
    "survey6Form": "work_characteristics",
}

survey_rows = []
for p in participants:
    path = DATA_DIR / f"data_{p}_survey.csv"
    if not path.exists():
        continue
    sdf = pd.read_csv(path)
    row = {"participant_id": p}
    for _, srow in sdf.iterrows():
        form_name = srow.get("form_name")
        label = SURVEY_LABELS.get(form_name, form_name)
        try:
            fd = json.loads(srow["form_data"])
        except Exception:
            continue
        for k, v in fd.items():
            colbase = f"{label}__{k}"
            row[colbase] = v
            row[colbase + "_num"] = likert_to_num(v)
    survey_rows.append(row)

survey_wide = pd.DataFrame(survey_rows)
survey_wide.to_csv(OUT_DIR / "survey_wide.csv", index=False)

# Per-scale mean (numeric items only). NOTE: KAI/Big5 normally need
# reverse-coding for valid subscale scores. These means are descriptive only.
scale_means = {"participant_id": []}
for p in participants:
    scale_means["participant_id"].append(p)
for label in set(SURVEY_LABELS.values()):
    if label == "demographics":
        continue
    col_match = [c for c in survey_wide.columns if c.startswith(f"{label}__") and c.endswith("_num")]
    scale_means.setdefault(label + "_mean", [])
    for p in participants:
        sub = survey_wide[survey_wide["participant_id"] == p]
        if len(sub) == 0 or not col_match:
            scale_means[label + "_mean"].append(np.nan)
            continue
        vals = sub[col_match].iloc[0]
        scale_means[label + "_mean"].append(vals.astype(float).mean())
scale_df = pd.DataFrame(scale_means)
scale_df.to_csv(OUT_DIR / "survey_scale_means.csv", index=False)

# Plot scale means per participant
fig, ax = plt.subplots(figsize=(9, 5))
labels = [c for c in scale_df.columns if c != "participant_id"]
x = np.arange(len(labels))
width = 0.2
for i, p in enumerate(participants):
    vals = scale_df.set_index("participant_id").loc[p, labels].values
    ax.bar(x + i * width, vals, width, color=p_to_color[p], label=f"P{p}")
ax.set_xticks(x + width * (len(participants) - 1) / 2)
ax.set_xticklabels(labels, rotation=15)
ax.set_ylabel("Item mean (raw — not reverse-coded)")
ax.set_title("Survey scale means per participant\n(descriptive only — KAI/Big5 need item-level reverse-coding for valid scores)")
ax.legend()
ax.grid(alpha=0.3, axis="y")
fig.tight_layout()
fig.savefig(OUT_DIR / "survey_scale_means.png", dpi=150)
plt.close(fig)
print("Wrote survey_wide.csv + survey_scale_means.csv + survey_scale_means.png")

# ---------------------------------------------------------------------------
# 6. Compare to independent age ratings (face_ages.txt)
# ---------------------------------------------------------------------------
ages_path = OUT_DIR / "face_ages.txt"
age_corr_rows = []
if ages_path.exists():
    ages = pd.read_csv(
        ages_path, sep=r"\s+", header=None,
        names=["face_int", "indep_age"], engine="python",
    )
    ages["face"] = ages["face_int"].astype(int).astype(str)
    ages_unique = ages.drop_duplicates("face")[["face", "indep_age"]]

    # Face-level: mean participant rating vs independent age
    face_age = face_summary.merge(ages_unique, on="face", how="inner")
    face_age = face_age.rename(columns={"mean": "rating_mean", "std": "rating_sd"})
    face_age.to_csv(OUT_DIR / "face_age_vs_rating.csv", index=False)

    r_face, p_face = stats.pearsonr(face_age["indep_age"], face_age["rating_mean"])
    rho_face, ps_face = stats.spearmanr(face_age["indep_age"], face_age["rating_mean"])
    print(f"Face-level age↔rating: Pearson r={r_face:.3f} (p={p_face:.3g}), "
          f"Spearman ρ={rho_face:.3f} (p={ps_face:.3g}), n={len(face_age)}")

    # Face-level scatter with regression line + error bars
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.errorbar(
        face_age["indep_age"], face_age["rating_mean"],
        yerr=face_age["rating_sd"], fmt="o", markersize=6,
        alpha=0.7, color="#1f77b4", ecolor="#88aacc", elinewidth=0.8, capsize=0,
        label=f"face (mean ± SD, n={len(face_age)})",
    )
    slope, intercept, *_ = stats.linregress(face_age["indep_age"], face_age["rating_mean"])
    xs = np.linspace(face_age["indep_age"].min(), face_age["indep_age"].max(), 100)
    ax.plot(xs, slope * xs + intercept, "k--", alpha=0.6,
            label=f"fit: r={r_face:.2f}, ρ={rho_face:.2f}")
    ax.set_xlabel("Independent age rating (external raters)")
    ax.set_ylabel("Mean rating (this study)")
    ax.set_title("Face-level: external age rating vs this study's mean rating")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "age_vs_rating_face_level.png", dpi=150)
    plt.close(fig)

    # Per-participant: every trial gets the face's indep_age attached
    trials_with_age = trials.merge(ages_unique, on="face", how="left")

    fig, axes = plt.subplots(2, 2, figsize=(11, 9), sharex=True, sharey=True)
    for ax, p in zip(axes.flat, participants):
        sub = trials_with_age[trials_with_age["participant_id"] == p].dropna(subset=["indep_age", "rating"])
        ax.scatter(sub["indep_age"], sub["rating"], color=p_to_color[p], alpha=0.7, s=30)
        r_p, pp = stats.pearsonr(sub["indep_age"], sub["rating"])
        rho_p, pps = stats.spearmanr(sub["indep_age"], sub["rating"])
        slope, intercept, *_ = stats.linregress(sub["indep_age"], sub["rating"])
        xs = np.linspace(sub["indep_age"].min(), sub["indep_age"].max(), 100)
        ax.plot(xs, slope * xs + intercept, "k--", alpha=0.5)
        ax.set_title(f"P{p}: r={r_p:.2f} (p={pp:.2g}),  ρ={rho_p:.2f}\n"
                     f"slope={slope:.2f} rating-units / yr",
                     fontsize=10)
        ax.set_xlabel("Independent age rating")
        ax.set_ylabel("Rating (this study)")
        ax.grid(alpha=0.3)
        age_corr_rows.append({
            "participant_id": int(p), "n_trials": len(sub),
            "pearson_r": r_p, "pearson_p": pp,
            "spearman_rho": rho_p, "spearman_p": pps,
            "slope_rating_per_year": slope, "intercept": intercept,
        })
    fig.suptitle("Per-participant: rating vs independent age (all trials)")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "age_vs_rating_per_participant.png", dpi=150)
    plt.close(fig)

    # Pooled across participants (with face-level mean as well, for reference)
    all_sub = trials_with_age.dropna(subset=["indep_age", "rating"])
    r_all, p_all = stats.pearsonr(all_sub["indep_age"], all_sub["rating"])
    rho_all, ps_all = stats.spearmanr(all_sub["indep_age"], all_sub["rating"])
    age_corr_rows.append({
        "participant_id": "ALL_TRIALS", "n_trials": len(all_sub),
        "pearson_r": r_all, "pearson_p": p_all,
        "spearman_rho": rho_all, "spearman_p": ps_all,
        "slope_rating_per_year": np.nan, "intercept": np.nan,
    })
    age_corr_rows.append({
        "participant_id": "FACE_LEVEL_MEAN", "n_trials": len(face_age),
        "pearson_r": r_face, "pearson_p": p_face,
        "spearman_rho": rho_face, "spearman_p": ps_face,
        "slope_rating_per_year": np.nan, "intercept": np.nan,
    })

    age_corr_df = pd.DataFrame(age_corr_rows)
    age_corr_df.to_csv(OUT_DIR / "age_correlations.csv", index=False)
    print(f"Wrote face_age_vs_rating.csv + age_correlations.csv + 2 plots")
else:
    print(f"face_ages.txt not found at {ages_path} — skipping age comparison")

# ---------------------------------------------------------------------------
# 6b. Per-participant age-quartile scores + correlation with survey scales
# ---------------------------------------------------------------------------
age_scores_df = None
if ages_path.exists():
    quartile_rows = []
    score_rows = []
    for p in participants:
        sub = trials_with_age[trials_with_age["participant_id"] == p].dropna(
            subset=["rating", "indep_age"]
        )
        # Collapse retest trials -> one mean rating per face (60 faces per participant)
        per_face = sub.groupby("face").agg(
            rating=("rating", "mean"),
            indep_age=("indep_age", "first"),
        ).reset_index()
        per_face["quartile"] = pd.qcut(
            per_face["rating"], q=4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop"
        )
        by_q = per_face.groupby("quartile", observed=True).agg(
            n_faces=("face", "count"),
            mean_rating=("rating", "mean"),
            mean_age=("indep_age", "mean"),
            sd_age=("indep_age", "std"),
        ).reset_index()
        by_q.insert(0, "participant_id", p)
        quartile_rows.append(by_q)

        ages_by_q = by_q.set_index("quartile")["mean_age"]
        score_rows.append({
            "participant_id": int(p),
            "mean_age_Q1": ages_by_q.get("Q1", np.nan),
            "mean_age_Q2": ages_by_q.get("Q2", np.nan),
            "mean_age_Q3": ages_by_q.get("Q3", np.nan),
            "mean_age_Q4": ages_by_q.get("Q4", np.nan),
            "age_pref_Q4_minus_Q1": ages_by_q.get("Q4", np.nan) - ages_by_q.get("Q1", np.nan),
        })

    pd.concat(quartile_rows, ignore_index=True).to_csv(
        OUT_DIR / "age_quartiles_per_participant.csv", index=False
    )
    age_scores_df = pd.DataFrame(score_rows)
    age_scores_df.to_csv(OUT_DIR / "age_scores_per_participant.csv", index=False)

    # Plot: mean age per quartile per participant
    fig, ax = plt.subplots(figsize=(9, 5.5))
    quartiles = ["Q1", "Q2", "Q3", "Q4"]
    x = np.arange(len(quartiles))
    width = 0.2
    for i, p in enumerate(participants):
        vals = age_scores_df.set_index("participant_id").loc[p, [f"mean_age_{q}" for q in quartiles]].values
        ax.bar(x + i * width, vals, width, color=p_to_color[p], label=f"P{p}")
    ax.set_xticks(x + width * (len(participants) - 1) / 2)
    ax.set_xticklabels([f"{q}\n(lowest-rated)" if q == "Q1" else f"{q}\n(highest-rated)" if q == "Q4" else q for q in quartiles])
    ax.set_ylabel("Mean independent age (years) of faces in quartile")
    ax.set_title("Per-participant: mean face age by rating quartile\n(downward slope = rates younger faces higher)")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "age_by_rating_quartile.png", dpi=150)
    plt.close(fig)

    # Correlate age scores with survey scale means
    merged = age_scores_df.merge(scale_df, on="participant_id")
    score_cols = ["mean_age_Q1", "mean_age_Q2", "mean_age_Q3", "mean_age_Q4", "age_pref_Q4_minus_Q1"]
    scale_cols = [c for c in scale_df.columns if c != "participant_id"]
    corr_rows = []
    for sc in score_cols:
        for sca in scale_cols:
            x_v = merged[sc].astype(float)
            y_v = merged[sca].astype(float)
            if x_v.notna().sum() < 3 or y_v.notna().sum() < 3:
                continue
            r, p_pearson = stats.pearsonr(x_v, y_v)
            rho, p_spearman = stats.spearmanr(x_v, y_v)
            corr_rows.append({
                "age_score": sc, "survey_scale": sca, "n": len(merged),
                "pearson_r": r, "pearson_p": p_pearson,
                "spearman_rho": rho, "spearman_p": p_spearman,
            })
    corr_df = pd.DataFrame(corr_rows).sort_values("pearson_r", key=lambda s: -s.abs())
    corr_df.to_csv(OUT_DIR / "age_score_vs_survey.csv", index=False)

    # Scatter grid: each survey scale vs each age score (small multiples)
    nrows, ncols = len(score_cols), len(scale_cols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.0 * ncols, 2.6 * nrows), squeeze=False)
    for i, sc in enumerate(score_cols):
        for j, sca in enumerate(scale_cols):
            ax = axes[i][j]
            for p in participants:
                row = merged[merged["participant_id"] == p]
                ax.scatter(row[sca], row[sc], color=p_to_color[p], s=60)
                ax.annotate(f"P{p}", (row[sca].iloc[0], row[sc].iloc[0]),
                            textcoords="offset points", xytext=(4, 4), fontsize=8)
            r = corr_df[(corr_df["age_score"] == sc) & (corr_df["survey_scale"] == sca)]["pearson_r"]
            r_txt = f"r={r.iloc[0]:.2f}" if len(r) else ""
            ax.set_title(f"{sca}\nvs {sc}  {r_txt}", fontsize=8)
            if i == nrows - 1:
                ax.set_xlabel(sca, fontsize=8)
            if j == 0:
                ax.set_ylabel(sc, fontsize=8)
            ax.grid(alpha=0.3)
    fig.suptitle("Age-quartile scores vs survey scales (n=4 — descriptive only)", y=1.001)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "age_score_vs_survey_scatter.png", dpi=150)
    plt.close(fig)

    print("Wrote age_quartiles_per_participant.csv + age_scores_per_participant.csv "
          "+ age_score_vs_survey.csv + 2 plots")
    print("\nTop 5 |correlations| (n=4, descriptive only):")
    print(corr_df.head(5)[["age_score", "survey_scale", "pearson_r", "spearman_rho"]].to_string(index=False))

# ---------------------------------------------------------------------------
# 7. Participant-level summary table tying behavior + surveys together
# ---------------------------------------------------------------------------
behavior = (
    trials.groupby("participant_id")
    .agg(
        mean_rating=("rating", "mean"),
        sd_rating=("rating", "std"),
        median_rt_ms=("rt", "median"),
    )
    .reset_index()
)
tr = tr_summary[tr_summary["participant_id"] != "ALL"].rename(columns={
    "pearson_r": "testretest_r",
    "mean_abs_diff": "testretest_mae",
})
tr["participant_id"] = tr["participant_id"].astype(int)
combined = behavior.merge(tr[["participant_id", "testretest_r", "testretest_mae"]], on="participant_id")
combined = combined.merge(scale_df, on="participant_id", how="left")
if age_corr_rows:
    age_per_p = pd.DataFrame([r for r in age_corr_rows if isinstance(r["participant_id"], int)])
    age_per_p = age_per_p.rename(columns={
        "pearson_r": "age_r", "spearman_rho": "age_rho",
        "slope_rating_per_year": "age_slope",
    })[["participant_id", "age_r", "age_rho", "age_slope"]]
    combined = combined.merge(age_per_p, on="participant_id", how="left")
combined.to_csv(OUT_DIR / "participant_summary.csv", index=False)
print("Wrote participant_summary.csv")

print("\nDone. See ./analysis/ for outputs.")
