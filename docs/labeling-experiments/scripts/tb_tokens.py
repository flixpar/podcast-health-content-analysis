"""Does the loss track how much the unbudgeted run thought on that window?"""
import sys; sys.path.insert(0, "benchmark/runs/analysis")
from tb_common import *
import statistics as st
def rt(key, i):
    u = D["runs"][key][i]["usage"]; return u["reasoning"] if u else None
def spearman(x, y):
    import scipy.stats as ss; return ss.spearmanr(x, y)
C0, C1, B = ("dev-high-chat-lenient",0), ("dev-high-chat-lenient",1), ("dev-high-budget16k-lenient",0)
items = sorted(set(D["runs"][C0]) & set(D["runs"][C1]) & set(D["runs"][B]))
print("B at cap:", sum(rt(B,i) >= 16000 for i in items), "of", len(items))
print("C0 vs C1 reasoning spearman", spearman([rt(C0,i) for i in items], [rt(C1,i) for i in items]))
words = {i: D["items"][i]["word_count"] for i in items}
ngold = {i: sum(1 for g in D["gold"][i] if g["tier"]=="required") for i in items}
need = {i: (rt(C0,i)+rt(C1,i))/2 for i in items}
print("need vs words", spearman([need[i] for i in items],[words[i] for i in items]), "need vs required gold", spearman([need[i] for i in items],[ngold[i] for i in items]))
bins = [(0,4000),(4000,12000),(12000,16000),(16000,24000),(24000,32000),(32000,10**6)]
GR = ("detection:frame","detection:evidence","claim","detection:topic")
def table(items, need, base_keys, cand_keys, label):
    print(f"## {label}: bin | windows | req gold (frame/evid/claim/topic) | recall base-mean -> cand-mean for frame, evidence, claim, topic")
    for lo, hi in bins:
        its = [i for i in items if lo <= need[i] < hi]
        if not its: continue
        out = []
        for g in GR:
            req = sum(D["runs"][base_keys[0]][i]["counts"][g]["required"] for i in its)
            rb = st.mean(pool([D["runs"][k][i] for i in its], g)["rec"] for k in base_keys)
            rc = st.mean(pool([D["runs"][k][i] for i in its], g)["rec"] for k in cand_keys)
            tpb = st.mean(sum(D["runs"][k][i]["counts"][g]["tp"] for i in its) for k in base_keys)
            tpc = st.mean(sum(D["runs"][k][i]["counts"][g]["tp"] for i in its) for k in cand_keys)
            out.append(f"{g.split(':')[-1]} req{req} R {rb:.2f}->{rc:.2f} tp {tpb:.1f}->{tpc:.1f}")
        print(f"{lo//1000}-{hi//1000 if hi<10**6 else 'inf'}k", len(its), " | ".join(out))
table(items, need, [C0, C1], [B], "dev 16k (need = mean chat r0/r1 reasoning)")
# per-window correlation of tp loss (frame+evidence+claim) with need
loss = {i: sum(D["runs"][B][i]["counts"][g]["tp"] - (D["runs"][C0][i]["counts"][g]["tp"]+D["runs"][C1][i]["counts"][g]["tp"])/2 for g in GR[:3]) for i in items}
print("spearman(need, tp change frame+evid+claim)", spearman([need[i] for i in items],[loss[i] for i in items]))
ngr = {i: sum(D["runs"][C0][i]["counts"][g]["required"] for g in GR[:3]) for i in items}
rel = [loss[i]/ngr[i] for i in items if ngr[i] >= 3]
print("spearman(need, relative change) n", len(rel), spearman([need[i] for i in items if ngr[i]>=3], rel))
print("spearman(words, tp change)", spearman([words[i] for i in items],[loss[i] for i in items]), "spearman(req gold, tp change)", spearman([ngr[i] for i in items],[loss[i] for i in items]))
# output tokens (non-reasoning) as an output-size proxy
for k in (C0, C1, B):
    print("answer tokens median", k, st.median(D["runs"][k][i]["usage"]["completion"] - D["runs"][k][i]["usage"]["reasoning"] for i in items))
# s70
S0 = [("s70-high-chat-lenient",0),("s70-high-chat-lenient",1)]
sitems = sorted(set.intersection(*[set(D["runs"][k]) for k in D["runs"] if k[0].startswith("s70")]))
sneed = {i: st.mean(rt(k,i) for k in S0) for i in sitems}
for b in (16,12,8,4):
    table(sitems, sneed, S0, [(f"s70-high-budget{b}k-lenient",0),(f"s70-high-budget{b}k-lenient",1)], f"s70 {b}k")
# answer tokens by budget in s70
for b in (None,16,12,8,4):
    ks = S0 if b is None else [(f"s70-high-budget{b}k-lenient",r) for r in (0,1)]
    print("s70 answer tokens median", b, st.median(D["runs"][k][i]["usage"]["completion"] - D["runs"][k][i]["usage"]["reasoning"] for k in ks for i in sitems),
          "atoms/window", round(st.mean(len(D["runs"][k][i]["preds"]) for k in ks for i in sitems),2))
