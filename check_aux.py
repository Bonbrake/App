aux_path = r"C:\Users\jakeb\AppData\Local\hermes\hermes-agent\agent\auxiliary_client.py"
with open(aux_path, "r") as f:
    lines = f.readlines()

# Show the retry/timeout related code
print("=== Lines 200-240 (retry timeout comments) ===")
for i in range(199, min(245, len(lines))):
    line = lines[i].rstrip()
    print(f"L{i+1}: {line}")

# Find where timeout is actually set
print("\n=== Searching for timeout config in auxiliary_client.py ===")
for i, line in enumerate(lines):
    lower = line.lower()
    if "timeout" in lower and ("aux" in lower or "vision" in lower or "default" in lower or "60" in lower or "120" in lower):
        start = max(0, i-2)
        end = min(len(lines), i+3)
        for j in range(start, end):
            marker = ">>> " if j == i else "    "
            print(f"  {marker}L{j+1}: {lines[j].rstrip()[:140]}")
        print("  ---")
