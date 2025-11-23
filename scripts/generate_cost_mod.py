#!/usr/bin/env python3
"""
Generate a CoE5 mod file that modifies ritual costs by a percentage.

Usage:
    python generate_cost_mod.py <percentage> [output_file]

Examples:
    python generate_cost_mod.py 50      # Reduce costs to 50% of original
    python generate_cost_mod.py 150     # Increase costs to 150% of original
    python generate_cost_mod.py 75 my_mod.c5m  # Custom output file
"""

import re
import sys
import math
from pathlib import Path

# Resource type names for comments (based on Ritual Data v5.33.c5m)
RESOURCE_TYPES = {
    0: "Gold",
    1: "Iron",
    2: "Herbs",
    3: "Fungus",
    4: "Sacrifices",
    5: "Hands",
    6: "Blood",
    7: "Prisoners",
    8: "Unburied",
    9: "Coins",
    10: "Silk",
    11: "Relics",
    12: "Gems",
    13: "Monster Parts",
    14: "Corpses (humanoid)",
    15: "Gems",
    16: "Entrails",
    17: "Corpses",
    18: "Hearts",
    19: "Skulls",
}

def parse_ritual_data(filepath):
    """Parse the ritual data file and extract ritual names and costs."""
    rituals = []
    current_ritual = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip comments for parsing, but keep the line
            line_stripped = line.split('#')[0].strip()

            # Check for new ritual definition
            match = re.match(r'newritual\s+"([^"]+)"', line_stripped)
            if match:
                if current_ritual and current_ritual['costs']:
                    rituals.append(current_ritual)
                current_ritual = {
                    'name': match.group(1),
                    'costs': []
                }
                continue

            # Check for cost line
            if current_ritual:
                match = re.match(r'cost\s+(\d+)\s+(\d+)', line_stripped)
                if match:
                    resource_type = int(match.group(1))
                    amount = int(match.group(2))
                    current_ritual['costs'].append({
                        'type': resource_type,
                        'amount': amount
                    })

        # Don't forget the last ritual
        if current_ritual and current_ritual['costs']:
            rituals.append(current_ritual)

    return rituals


def generate_mod_file(rituals, percentage, output_path):
    """Generate a mod file that modifies ritual costs by the given percentage."""

    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"# OBM Ritual Cost Modifier\n")
        f.write(f"# \n")
        f.write(f"# This mod adjusts all ritual costs to {percentage}% of their original values.\n")
        f.write(f"# Generated from Ritual Data v5.33.c5m\n")
        f.write(f"# \n")
        f.write(f"# Total rituals modified: {len(rituals)}\n")
        f.write(f"# \n\n")

        for ritual in rituals:
            f.write(f'selectritual "{ritual["name"]}"\n')

            for cost in ritual['costs']:
                resource_type = cost['type']
                original_amount = cost['amount']

                # Calculate new cost
                new_amount = math.ceil(original_amount * percentage / 100)

                # Ensure minimum cost of 1
                new_amount = max(1, new_amount)

                # Get resource name for comment
                resource_name = RESOURCE_TYPES.get(resource_type, f"Resource {resource_type}")

                f.write(f"cost {resource_type} {new_amount}  # {new_amount} {resource_name} (was {original_amount})\n")

            f.write("\n")

    return len(rituals)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    try:
        percentage = float(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid percentage")
        sys.exit(1)

    if percentage <= 0:
        print("Error: Percentage must be greater than 0")
        sys.exit(1)

    # Determine output filename
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = f"ritual_costs_{int(percentage)}pct.c5m"

    # Find the ritual data file
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    ritual_data_file = project_dir / "data" / "Ritual Data v5.33.c5m"

    if not ritual_data_file.exists():
        print(f"Error: Could not find '{ritual_data_file}'")
        sys.exit(1)

    print(f"Parsing ritual data from: {ritual_data_file}")
    rituals = parse_ritual_data(ritual_data_file)
    print(f"Found {len(rituals)} rituals with costs")

    output_path = project_dir / "output" / output_file
    print(f"Generating mod file: {output_path}")
    num_modified = generate_mod_file(rituals, percentage, output_path)

    print(f"Successfully generated mod with {num_modified} ritual cost modifications at {percentage}% of original")
    print(f"\nTo use this mod:")
    print(f"  1. Copy '{output_file}' to your CoE5 mods folder")
    print(f"  2. Enable the mod in the game's mod menu")


if __name__ == "__main__":
    main()
