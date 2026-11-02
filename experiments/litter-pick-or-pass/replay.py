"""Replay the two recorded Jev photo trials. Uses only the Python standard library."""

import json
from collections import defaultdict
from pathlib import Path


def run_trial(data, order):
    crops = data["crops"]
    remaining = {"intruder": list(range(order["intruders"])), "litter": list(range(order["litter"]))}
    used = set()
    previous_sources = defaultdict(set)
    rounds = []
    for _ in range(data["max_rounds"]):
        seen_this_round = set()
        decisions = []
        for kind, slots in remaining.items():
            retry = []
            for slot in slots:
                previous = previous_sources[kind, slot]
                eligible = [
                    key for key in order[kind + "_order"]
                    if key not in used and crops[key]["source"] not in previous
                ]
                if not eligible:
                    raise ValueError(f"Ran out of photos for {kind} {slot + 1}")
                key = next((k for k in eligible if crops[k]["source"] not in seen_this_round), eligible[0])
                crop = crops[key]
                used.add(key)
                previous.add(crop["source"])
                seen_this_round.add(crop["source"])
                yes = crop["score"] >= data["threshold"]
                decisions.append((f"{kind}_{slot + 1}", key, yes))
                if not yes:
                    retry.append(slot)
            remaining[kind] = retry
        rounds.append(decisions)
        if not remaining["litter"]:
            break
    return rounds


def main():
    data = json.loads((Path(__file__).parent / "data" / "pilot.json").read_text())
    crops = data["crops"].values()
    print(f"{len(crops)} crops from {len({c['source'] for c in crops})} photos")
    for label in ("litter", "non_litter", "unverified"):
        group = [c for c in crops if c["label"] == label]
        yes = sum(c["score"] >= data["threshold"] for c in group)
        print(f"{label:>12}: {yes}/{len(group)} marked for pickup")
    for order in data["orders"].values():
        litter = decoys = 0
        print(f"\nGoal {order['litter']} litter, {order['intruders']} decoys")
        for n, decisions in enumerate(run_trial(data, order), 1):
            for slot, _, yes in decisions:
                if yes and slot.startswith("litter_"):
                    litter += 1
                elif yes:
                    decoys += 1
            print(f"Round {n}: {litter} litter, {decoys} decoys marked for pickup")


if __name__ == "__main__":
    main()
