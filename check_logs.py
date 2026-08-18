import os

log_dir = r"C:\Users\jakeb\AppData\Local\hermes\logs"
log_names = ["agent.log", "errors.log", "desktop.log", "gateway.log"]

for log_name in log_names:
    log_path = os.path.join(log_dir, log_name)
    try:
        with open(log_path, "r", errors="replace") as f:
            lines = f.readlines()
        # Find recent vision/auxiliary/timeout/bionic lines
        matching = [l.strip() for l in lines if any(
            keyword in l.lower() for keyword in ["vision", "auxiliary", "timeout", "bionic", "aux", "5120"]
        )]
        if matching:
            print(f"=== {log_name} — last {min(len(matching), 15)} matching lines ===")
            for line in matching[-15:]:
                print(f"  {line[:200]}")
            print()
    except FileNotFoundError:
        print(f"=== {log_name}: NOT FOUND ===")
    except Exception as e:
        print(f"=== {log_name}: ERROR {e} ===")
