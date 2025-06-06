import csv
from collections import defaultdict
import re
import csv
import requests
import time
from tqdm import tqdm

from urllib.parse import quote
import requests
import json
from pulp import *


# === Config ===
UPDATE_PRICES = False  # Toggle to enable/disable price fetching


# === Input file ===
stock_file = "stock-paste.txt"

# === Parsed outputs ===
blueprint_counts = defaultdict(int)
residue_stock = defaultdict(int)
mutaplasmid_stock = defaultdict(int)

# === Load file ===
with open(stock_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

for line in lines:
    # Blueprint lines — no count
    if line.startswith("Glorified") and "Blueprint" in line:
        blueprint_counts[line] += 1

    # All other lines should have tab and quantity
    elif '\t' in line:
        name, count = line.rsplit("\t", 1)
        name = name.strip()
        count = int(count)

        if "Residue" in name:
            residue_stock[name] += count
        else:
            mutaplasmid_stock[name] += count

# === Output debug preview ===
# print("✅ Glorified blueprints you own:\n")
# for bp, count in blueprint_counts.items():
#     print(f"  {bp}: {count}")

# print("\n✅ Residue stock:\n")
# for residue, qty in residue_stock.items():
#     print(f"  {residue}: {qty}")

# print("\n✅ Mutaplasmid stock (Decayed, Gravid, Unstable):\n")
# for item, qty in mutaplasmid_stock.items():
#     print(f"  {item}: {qty}")



# === Load blueprint CSV ===
blueprints = []
with open("parsed_blueprints.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        blueprints.append({
            "name": row["Name"],
            "base_item": row["base_item"],
            "type_residue_name": row["type_residue_name"],
            "type_residue": int(row["type_residue"]),
            "size_residue_name": row["size_residue_name"],
            "size_residue": int(row["size_residue"])
        })


# --------------------------- STOCK-------------------------------------
used_in_blueprints = defaultdict(int)

for bp in blueprints:
    count = blueprint_counts.get(bp["name"], 0)
    if count > 0:
        used_in_blueprints[bp["base_item"]] += count

base_item_stock = dict(mutaplasmid_stock)  # includes Decayed, Gravid, Unstable
rolling_candidates = {}

for item, stock in mutaplasmid_stock.items():
    if item.startswith("Decayed"):
        used = used_in_blueprints.get(item, 0)
        adjusted_stock = stock - used
        excess = adjusted_stock - 3

        if excess > 0:
            rolling_candidates[item] = {
                "stock": stock,
                "used_by_bps": used,
                "adjusted_stock": adjusted_stock,
                "excess": excess,
                "price": None,
                "residue_yield": {}
            }


# === Step 4: Attach residue yield to each rolling candidate from blueprint info
for bp in blueprints:
    base_item = bp["base_item"]
    if base_item in rolling_candidates:
        type_name = bp["type_residue_name"]
        size_name = bp["size_residue_name"]
        type_yield = 0.15 * bp["type_residue"]   #actual residue is 20%. we use 15% to keep some rolled modules if the roll really good. 
        size_yield = 0.15 * bp["size_residue"]

        rc = rolling_candidates[base_item]
        # Add to existing yields if already seen in other blueprints
        rc["residue_yield"][type_name] = rc["residue_yield"].get(type_name, 0) + type_yield
        rc["residue_yield"][size_name] = rc["residue_yield"].get(size_name, 0) + size_yield
    
# === Debug output
# print("\n🎯 Rolling candidates (after accounting for blueprint usage):")
# for item, info in rolling_candidates.items():
#     print(f"{item}: stock={info['stock']}, used_by_bps={info['used_by_bps']}, adjusted={info['adjusted_stock']}, excess={info['excess']}")
    
#     if info["residue_yield"]:
#         print("  ↳ Yields per 1 rolled:")
#         for res, qty in info["residue_yield"].items():
#             print(f"     - {qty:.1f} of {res}")
#     else:
#         print("  ↳ No residue yield data.")



# === Constants ===
ESI_UNIVERSE_IDS = "https://esi.evetech.net/latest/universe/ids/"
FUZZWORK_AGGREGATE = "https://market.fuzzwork.co.uk/aggregates/"
JITA_REGION_ID = 10000002
HEADERS = {"Accept": "application/json"}
CSV_FILE = "rolling-partners.csv"

# === Helpers ===
def resolve_type_id(name):
    try:
        res = requests.post(
            ESI_UNIVERSE_IDS,
            params={"datasource": "tranquility", "language": "en"},
            headers=HEADERS,
            json=[name]
        )
        res.raise_for_status()
        data = res.json()
        for entry in data.get("inventory_types", []):
            if entry["name"].strip().lower() == name.strip().lower():
                return entry["id"]
        print(f"⚠️ No matching inventory_type for '{name}'")
        return None
    except Exception as e:
        print(f"❌ Error resolving type ID for '{name}': {e}")
        return None

def get_fuzzwork_price(type_id):
    try:
        url = f"{FUZZWORK_AGGREGATE}?region={JITA_REGION_ID}&types={type_id}"
        res = requests.get(url)
        res.raise_for_status()
        return res.json().get(str(type_id), {}).get("sell", {}).get("min")
    except Exception as e:
        print(f"❌ Error fetching price for type_id={type_id}: {e}")
        return None

# === Read CSV, update if needed ===
rows = []
with open(CSV_FILE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        muta = row["MUTAPLASMID"].strip().strip('"')
        partner = row["PARTNER"].strip().strip('"')
        price_str = row.get("PRICE", "").strip()

        if UPDATE_PRICES:
            muta_id = resolve_type_id(muta)
            partner_id = resolve_type_id(partner)

            if muta_id and partner_id:
                muta_price = get_fuzzwork_price(muta_id)
                partner_price = get_fuzzwork_price(partner_id)

                if muta_price is not None and partner_price is not None:
                    total = float(muta_price) + float(partner_price)
                    row["PRICE"] = f"{total:.2f}"
                    print(f"✅ {muta}: {total:,.2f} ISK")

                    if muta in rolling_candidates:
                        rolling_candidates[muta]["price"] = total
                else:
                    print(f"⚠️ Skipping due to missing price: {muta} or {partner}")
            else:
                print(f"⚠️ Skipping due to unresolved ID: {muta} or {partner}")

            time.sleep(1)

        else:
            if price_str:
                try:
                    price_val = float(price_str.replace(",", ""))
                    print(f"ℹ️ Using cached price for {muta}: {price_val:,.2f} ISK")
                    if muta in rolling_candidates:
                        rolling_candidates[muta]["price"] = price_val
                except ValueError:
                    print(f"⚠️ Invalid price in CSV for {muta}: '{price_str}'")
        rows.append(row)


# === Write back CSV with PRICE column ===
fieldnames = ["MUTAPLASMID", "PARTNER", "PRICE"]
with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)



# === Convert blueprints list into blueprint_needs and counts ===
blueprint_counts = defaultdict(int)
blueprint_needs = {}

for bp in blueprints:
    name = bp["name"]
    blueprint_counts[name] += 1
    # Store residue requirements once
    if name not in blueprint_needs:
        blueprint_needs[name] = {
            bp["type_residue_name"]: bp["type_residue"],
            bp["size_residue_name"]: bp["size_residue"]
        }

# === Total available blueprints to use ===
MAX_BPOS = sum(blueprint_counts.values())


# Create a lookup for blueprint count
bpo_counts = {bp["name"]: blueprint_counts.get(bp["name"], 0) for bp in blueprints}

# Try decreasing number of BPOs used until feasible
for target_bpo_usage in range(MAX_BPOS, -1, -1):
    print(f"\n🧪 Trying to use {target_bpo_usage} BPOs...")

    # LP setup
    prob = LpProblem("Mutaplasmid_Planning", LpMinimize)

    # Decision variables
    bpo_vars = {bp["name"]: LpVariable(f"bpo_use_{bp['name']}", lowBound=0, upBound=bpo_counts[bp["name"]], cat=LpInteger)
                for bp in blueprints}
    roll_vars = {rc: LpVariable(f"roll_{rc}", lowBound=0, cat=LpInteger) for rc in rolling_candidates}

    # Primary constraint: total BPOs used == target
    prob += lpSum(bpo_vars.values()) == target_bpo_usage, "TargetTotalBPOsUsed"

    # Secondary objective: minimize cost of rolling
    prob += lpSum(roll_vars[rc] * rolling_candidates[rc]["price"] for rc in rolling_candidates), "TotalRollingCost"

    # Residue constraints
    residue_types = set()
    for b in blueprints:
        residue_types.update({b["type_residue_name"], b["size_residue_name"]})
    for rc in rolling_candidates.values():
        residue_types.update(rc["residue_yield"].keys())

    for residue in residue_types:
        required = lpSum(bpo_vars[bp["name"]] * (
            (bp["type_residue"] if bp["type_residue_name"] == residue else 0) +
            (bp["size_residue"] if bp["size_residue_name"] == residue else 0)
        ) for bp in blueprints)

        available = residue_stock.get(residue, 0) + lpSum(
            roll_vars[rc] * rolling_candidates[rc]["residue_yield"].get(residue, 0)
            for rc in rolling_candidates
        )

        prob += required <= available, f"ResidueRequirement_{residue}"

    # Solve
    status = prob.solve()

    if LpStatus[status] == "Optimal":
        print("✅ Feasible solution found!\n")
        break
    else:
        print("❌ No feasible solution at this level.")

# === Results ===
print("\n📦 Glorified BPOs to use:")
for bp in blueprints:
    var = bpo_vars[bp["name"]]
    if var.varValue and var.varValue > 0:
        print(f"{bp['name']}: {int(var.varValue)}")

print("\n🧬 Rolling Plan:")
for rc, var in roll_vars.items():
    if var.varValue and var.varValue > 0:
        print(f"{rc}: {int(var.varValue)}")

print(f"\n💰 Total rolling cost: {value(prob.objective):,.2f} ISK")