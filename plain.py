# plain.py
"""Plain-language helpers: turn statistics into sentences anyone can read.

These work fully offline. They are also the fallback when the AI explanation
(Groq) is not available.
"""


def fmt_num(x: float) -> str:
    return f"{x:+.4f}" if abs(x) < 0.01 else f"{x:+.3f}"


def fmt_abs(x: float) -> str:
    x = abs(x)
    return f"{x:.4f}" if x < 0.01 else f"{x:.2f}"


def fmt_p(p: float) -> str:
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def confidence(p: float):
    """(short label, longer sentence, emoji) describing how sure we are."""
    if p < 0.01:
        return ("Very sure", "We are very sure this is a real change, not just random ups and downs.", "🟢")
    if p < 0.05:
        return ("Fairly sure", "We are fairly sure this is a real change rather than chance.", "🟢")
    if p < 0.10:
        return ("Not sure yet", "There are hints of a change, but not enough evidence to be sure.", "🟡")
    return ("Can't tell yet", "Any change is smaller than the normal ups and downs, so we can't say it is real.", "⚪")


def headline(region_name: str, var_info: dict, stats: dict, years: tuple) -> str:
    """One bold sentence summarising the result."""
    emoji, name = var_info["emoji"], var_info["plain_name"]
    unit = var_info["unit"]
    per_dec = fmt_abs(stats["change_per_decade"])
    span = f"{years[0]}–{years[1]}"
    if stats["is_significant"]:
        phrase = var_info["up_phrase"] if stats["change_per_decade"] > 0 else var_info["down_phrase"]
        return (f"{emoji} **{region_name} is {phrase}.** Between {span} the {name} changed by about "
                f"**{fmt_abs(stats['total_change'])} {unit}** in total (roughly {per_dec} {unit} every 10 years).")
    leaning = var_info["up_phrase"] if stats["change_per_decade"] > 0 else var_info["down_phrase"]
    return (f"{emoji} **No clear change in {name} at {region_name} yet.** The data lean slightly towards "
            f"\"{leaning}\" (about {per_dec} {unit} per 10 years), but that is within normal ups and downs.")


def robustness_sentence(rob: dict) -> str:
    if not rob or not rob.get("n_windows"):
        return ""
    return (f"{rob['label']}. Across {rob['n_windows']} different choices of start and end year, "
            f"{rob['same_sign_share']*100:.0f}% point the same way and "
            f"{rob['significant_share']*100:.0f}% of them are statistically significant.")


def tts_sentence(tts: dict, last_year: int) -> str:
    """Explain how long until a non-significant trend would become significant."""
    if not tts:
        return ""
    e50, e80 = tts["extra_50"], tts["extra_80"]
    if e50 is None:
        return (f"At the current pace the trend would still not be significant after "
                f"{tts['max_extra']} more years. The change is tiny compared with the natural noise.")
    if e80 is None:
        return (f"If the current trend and noise continue, it would probably cross the significance line "
                f"after about **{e50} more year{'s' if e50 != 1 else ''}** (around {tts['year_50']}).")
    if e50 == e80:
        return (f"If the current trend and noise continue, it would likely become significant after about "
                f"**{e50} more year{'s' if e50 != 1 else ''}** (around {tts['year_50']}).")
    return (f"If the current trend and noise continue, it would be expected to become significant after about "
            f"**{e50} more years** (around {tts['year_50']}), and we would be quite sure of it "
            f"after about **{e80} years** (around {tts['year_80']}).")


def template_narrative(facts: dict) -> str:
    """Rule-based explanation used when the AI service is unavailable."""
    regions = facts["regions"]
    parts = []
    for r in regions:
        sig = r["significant"]
        unit = facts["unit"]
        if sig:
            parts.append(
                f"At {r['name']}, {facts['plain_name']} is {r['direction_words']}: about "
                f"{r['total_abs']} {unit} over {facts['period']}, roughly {r['rate_abs']} {unit} per 10 years. "
                f"{r['confidence_sentence']}")
        else:
            parts.append(
                f"At {r['name']}, there is no statistically clear change in {facts['plain_name']} over "
                f"{facts['period']}. The slight tendency ({r['rate_abs']} {unit} per 10 years) is within "
                f"normal ups and downs. {r['time_to_significance_sentence']}")
        if r.get("robustness_sentence"):
            parts.append(r["robustness_sentence"])
    parts.append("These values come from NASA's MERRA-2 reanalysis (a model blended with satellite and other "
                 "observations), so they describe the large grid cell around the point, not a single weather station.")
    return "\n\n".join(parts)
