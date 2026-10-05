"""Warm the shared prefix with one request, then hold N concurrent requests
(distinct windows) and report per-request cached prompt tokens and peak KV."""
import json, sys, threading, time, urllib.request
sys.path.insert(0, '.')
from analysis import topic_labeling as tl

API = "http://127.0.0.1:8222"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def kv():
    text = opener.open(API + "/metrics", timeout=10).read().decode()
    return sum(float(l.split()[-1]) for l in text.splitlines() if l.startswith("vllm:kv_cache_usage_perc"))

def send(model, ins, w, max_tokens, out):
    body = {"model": model, "messages": [{"role": "system", "content": ins}, {"role": "user", "content": tl.window_input(w)}],
            "max_tokens": max_tokens, "reasoning_effort": "high", "temperature": 1.0, "ignore_eos": True}
    req = urllib.request.Request(API + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    r = json.loads(opener.open(req, timeout=3600).read())
    out.append(((r["usage"].get("prompt_tokens_details") or {}).get("cached_tokens"), r["usage"]["prompt_tokens"]))

bench, model, ns, max_tokens = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")], int(sys.argv[4])
tax = json.load(open(f"benchmark/{bench}/taxonomy.json"))
ins = tl.taxonomy_instructions(tax)
items = [json.loads(l) for l in open(f"benchmark/{bench}/items.jsonl")]
ws = [{k: i[k] for k in ("window_id", "episode_id", "units")} for i in items]
out = []; send(model, ins, ws[-1], 16, out); print("warm", out)
k = 0
for n in ns:
    out = []; ths = []
    for i in range(n):
        t = threading.Thread(target=send, args=(model, ins, ws[k], max_tokens, out)); k += 1
        t.start(); ths.append(t); time.sleep(0.3)
    peak = 0
    while any(t.is_alive() for t in ths):
        peak = max(peak, kv()); time.sleep(0.5)
    print(f"n={n} peak_kv={peak:.4f} cached/prompt={out}", flush=True)
    time.sleep(2)
