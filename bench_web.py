#!/usr/bin/env python3
"""Web benchmark: external web search via Hermes-configured provider."""
import requests, time, json, subprocess, sys

# Determine which web provider Hermes is configured to use
import yaml
cfg=yaml.safe_load(open(r"C:\Users\jakeb\AppData\Local\hermes\config.yaml"))
aux=cfg.get("auxiliary",{})
we=cfg.get("web",{})
providers = list(we.keys()) if isinstance(we,dict) else []
print("Hermes web config providers: %s" % providers)
print("auxiliary.web_extract.provider: %s" % aux.get("web_extract",{}).get("provider"))
print("auxiliary.web_extract.model: %s" % aux.get("web_extract",{}).get("model"))

# Hit a real, free search endpoint to measure latency
# Use Brave free (configured) or DuckDuckGo HTML as fallback
ENGINES = [
    ("DuckDuckGo HTML", "https://html.duckduckgo.com/html/?q="),
    ("Brave free", "https://api.search.brave.com/res/v1/web/search?q="),
]
QUERY="best practices for llama.cpp flash attention windows"
for name,base in ENGINES:
    t0=time.time()
    try:
        if "brave" in base:
            # brave needs key; skip if not present
            hdr=cfg.get("web",{}).get("brave",{})
            key=hdr.get("api_key") if isinstance(hdr,dict) else None
            if not key:
                print("%s: skipped (no api key in config)" % name); continue
            r=requests.get(base+QUERY.replace(' ','+'), headers={"X-Subscription-Token":key}, timeout=20)
        else:
            r=requests.get(base+QUERY.replace(' ','+'), timeout=20)
        dt=time.time()-t0
        ok = r.status_code==200 and len(r.text)>200
        print("%s: HTTP %d | %.2fs | %d bytes %s" % (name, r.status_code, dt, len(r.text), "OK" if ok else "thin"))
        if ok:
            # count result links
            links=r.text.count("result__a")
            print("   approx result links: %d" % links)
    except Exception as e:
        print("%s: ERROR %s" % (name, e))
