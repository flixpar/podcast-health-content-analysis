"""Probe per-request KV footprint on a vLLM server: hold N concurrent requests
that share the codebook system prompt and read vllm:kv_cache_usage_perc."""
import json, sys, threading, time, urllib.request
sys.path.insert(0, '.')
from analysis import topic_labeling as tl

API = "http://127.0.0.1:8222"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def metric(name):
    text = opener.open(API + "/metrics", timeout=10).read().decode()
    vals = [float(l.split()[-1]) for l in text.splitlines() if l.startswith(name)]
    return vals

def main(bench, model, ns, max_tokens):
    tax = json.load(open(f"benchmark/{bench}/taxonomy.json"))
    ins = tl.taxonomy_instructions(tax)
    items = [json.loads(l) for l in open(f"benchmark/{bench}/items.jsonl")][:64]
    for n in ns:
        threads = []
        for i in range(n):
            w = {k: items[i][k] for k in ("window_id", "episode_id", "units")}
            body = {"model": model, "messages": [{"role": "system", "content": ins}, {"role": "user", "content": tl.window_input(w)}],
                    "max_tokens": max_tokens, "reasoning_effort": "high", "temperature": 1.0, "ignore_eos": True}
            req = urllib.request.Request(API + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            t = threading.Thread(target=lambda r=req: opener.open(r, timeout=3600).read())
            t.start(); threads.append(t)
        peak = 0.0
        while any(t.is_alive() for t in threads):
            u = metric("vllm:kv_cache_usage_perc")
            r = metric("vllm:num_requests_running")
            peak = max(peak, u[0] if u else 0)
            time.sleep(1)
        print(f"n={n} peak_kv_usage={peak:.4f}", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")], int(sys.argv[4]))
