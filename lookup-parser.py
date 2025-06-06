import csv
import re

input_file = "mat-dump.txt"
output_file = "parsed_blueprints.csv"

# Load and clean lines
with open(input_file, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

results = []
i = 0

while i < len(lines):
    if lines[i].startswith("Glorified"):
        name = lines[i]
        i += 1

        # Skip until we reach "Materials"
        while i < len(lines) and lines[i] != "Materials":
            i += 1

        # Skip "Materials" and "Material Quantity"
        i += 2

        materials = []
        while i < len(lines) and not lines[i].startswith("Glorified"):
            match = re.match(r"^(.*?)\s+(\d+)$", lines[i])
            if match:
                material_name = match.group(1).strip()
                quantity = int(match.group(2))
                materials.append((material_name, quantity))
            i += 1

        if len(materials) >= 3:
            base_item, _ = materials[0]
            type_residue_name, type_qty = materials[1]
            size_residue_name, size_qty = materials[2]

            results.append({
                "Name": name,
                "base_item": base_item,
                "type_residue_name": type_residue_name,
                "type_residue": type_qty,
                "size_residue_name": size_residue_name,
                "size_residue": size_qty
            })
        else:
            print(f"⚠️ Skipping blueprint due to insufficient materials: {name}")
    else:
        i += 1

# Write to CSV
with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=[
        "Name", "base_item",
        "type_residue_name", "type_residue",
        "size_residue_name", "size_residue"
    ])
    writer.writeheader()
    for row in results:
        writer.writerow(row)

print(f"✅ Updated CSV with residue names written to {output_file}")
