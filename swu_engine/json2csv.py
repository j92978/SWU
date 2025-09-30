import json
import csv

def json_to_csv(json_file, csv_file):
    # Load JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract card list
    cards = data.get("data", [])

    # Ensure each card has a unique ID
    for card in cards:
        set_code = card.get("Set", "").strip()
        number = str(card.get("Number", "")).strip()
        card["ID"] = f"{set_code}-{number}"

    # Collect all possible keys across cards (flatten lists into strings)
    fieldnames = set()
    for card in cards:
        for key, value in card.items():
            fieldnames.add(key)

    fieldnames = ["ID"] + sorted(fieldnames - {"ID"})  # ensure ID is first

    # Write CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for card in cards:
            flat_card = {}
            for k, v in card.items():
                if isinstance(v, list):
                    flat_card[k] = ";".join(str(x) for x in v)
                else:
                    flat_card[k] = v
            writer.writerow(flat_card)

    print(f"Converted {len(cards)} cards to {csv_file}")

if __name__ == "__main__":
    json_to_csv("jtl.json", "jtl.csv")
    json_to_csv("lof.json", "lof.csv")
    json_to_csv("shd.json", "shd.csv")
    json_to_csv("sor.json", "sor.csv")
    json_to_csv("twi.json", "twi.csv")