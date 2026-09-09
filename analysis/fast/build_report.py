"""Assemble the HTML report: inject data JSON + css + js into the template."""
import json, os
ROOT = "/home/felix/projects/podcast-misinfo"
OUT = f"{ROOT}/analysis/output/fast-analysis"
HERE = f"{ROOT}/analysis/fast/report"

def load(name, default=None):
    p = f"{OUT}/{name}"
    return json.load(open(p)) if os.path.exists(p) else default

R = load("report_data.json"); P = load("corpus_profile.json")
A = load("products_ads.json", {}); B = load("bundles.json", {}); V2 = load("report_data_v2.json"); QV = load("qual_vaccines_rogan.json", {}); QL = load("qual_legitimation.json", {}); AN = load("audit_narratives.json", {}); AL = load("audit_labels.json", {})
LEX = json.load(open(f"{ROOT}/analysis/fast/lexicon.json"))

D = {
  "meta": R["meta"], "headline": P["headline"], "genre_rows": P["genre_groups"]["rows"], "genre_mapping": P["genre_groups"]["mapping"],
  "concentration": P["concentration"], "distributions": P["distributions"], "quality": P["quality_flags"], "chart_overlap": P["chart_overlap"],
  "per_show": [{k: s[k] for k in ("podcast_id", "title", "genre_group", "on_health_chart", "n_transcripts", "total_words", "total_hours", "median_episode_minutes", "live_episodes_per_week", "share_rss_transcripts")} for s in P["per_show"]],
  "health_by_genre": R["health_by_genre"], "health_by_chart": R["health_by_chart"], "health_concentration": R["health_concentration"],
  "shows": R["shows"], "health_density_hist": R["health_density_hist"],
  "topics": R["topics"], "frames": R["frames"], "evidence": R["evidence"], "narratives": R["narratives"], "topic_by_genre": R["topic_by_genre"],
  "narrative_detail": {k: {kk: vv for kk, vv in v.items() if kk != "yearly"} for k, v in R["narrative_detail"].items()},
  "narrative_show_matrix": R["narrative_show_matrix"], "narrative_rate_by_show": R["narrative_rate_by_show"], "narrative_rate_by_genre": R["narrative_rate_by_genre"],
  "frames_by_genre": R["frames_by_genre"], "frames_by_show": R["frames_by_show"], "frames_overall": R["frames_overall"],
  "commercial": R["commercial"], "products_detail": R["products_detail"][:60],
  "monthly_topics": R["monthly_topics"], "monthly_narratives": R["monthly_narratives"], "monthly_health": R["monthly_health"],
  "weekly_narratives": R["weekly_narratives"], "yearly_topics": R["yearly_topics"], "yearly_narratives": R["yearly_narratives"],
  "bursts": R["bursts"], "diffusion": R["diffusion"], "examples": R["examples"],
  "ads": A, "audit_narr": AN, "audit_labels": AL, "bundles": B, "qual_v": QV, "qual_l": QL,
  "v2": ({"meta": V2["meta"], "health_by_chart": V2["health_by_chart"], "health_concentration": V2["health_concentration"], "health_density_hist": V2["health_density_hist"], "topics": [{k: t[k] for k in ("label","sentences","episodes","pct_episodes")} for t in V2["topics"]], "narratives": [{k: t[k] for k in ("label","sentences","episodes","shows")} for t in V2["narratives"]], "frames_by_genre": V2["frames_by_genre"], "narrative_rate_by_genre": V2["narrative_rate_by_genre"], "health_by_genre": V2["health_by_genre"]} if V2 else None),
  "lex_sizes": {k: (len(v) if isinstance(v, dict) and "terms" not in v else len(v.get("terms", []))) for k, v in LEX.items()},
  "narr_desc": {k: v.get("description", "") for k, v in LEX["narratives"].items()},
  "topic_desc": {k: v.get("description", "") for k, v in LEX["topics"].items()},
}
import html as _h
def md_to_html(path):
    if not os.path.exists(path): return ""
    out=[]; 
    for para in open(path).read().split("\n\n"):
        t=para.strip()
        if not t: continue
        if t.startswith("#"): 
            lvl=len(t)-len(t.lstrip("#")); out.append(f"<h4>{_h.escape(t.lstrip('#').strip())}</h4>" if lvl>=2 else "")
        elif t.startswith("|"):
            rows=[r for r in t.split("\n") if r.startswith("|") and not set(r) <= set("|-: ")]
            cells=[[c.strip() for c in r.strip("|").split("|")] for r in rows]
            out.append("<div class='tbl'><table>"+"".join(("<tr>"+"".join(f"<th>{_h.escape(c)}</th>" for c in row)+"</tr>") if i==0 else ("<tr>"+"".join(f"<td>{_h.escape(c)}</td>" for c in row)+"</tr>") for i,row in enumerate(cells))+"</table></div>")
        elif t.startswith("- ") or t.startswith("* "):
            out.append("<ul>"+"".join(f"<li>{_h.escape(li[2:].strip())}</li>" for li in t.split("\n") if li.strip())+"</ul>")
        else:
            out.append(f"<p>{_h.escape(t)}</p>")
    import re as _re
    txt = "\n".join(out)
    txt = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
    txt = _re.sub(r"`([^`]+)`", r"<code>\1</code>", txt)
    txt = _re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?!\w)", r"<i>\1</i>", txt)
    return txt
D["md"] = {k: md_to_html(f"{OUT}/{k}.md") for k in ("spotcheck_quant","spotcheck_interrater","qual_vaccines_rogan","qual_legitimation","deepseek_pilot_notes")}
D["pilot"] = load("deepseek_pilot.json")
tpl = open(f"{HERE}/template.html").read()
html = tpl.replace("/*__EXTRA__*/", open(f"{HERE}/extra.js").read() if os.path.exists(f"{HERE}/extra.js") else "").replace("/*__CSS__*/", open(f"{HERE}/style.css").read()).replace("/*__JS__*/", open(f"{HERE}/charts.js").read()).replace("/*__DATA__*/", "const DATA = " + json.dumps(D, separators=(",", ":")) + ";")
open(f"{OUT}/health_talk_scan.html", "w").write(html)
print("wrote", f"{OUT}/health_talk_scan.html", round(len(html)/1e6, 2), "MB")
