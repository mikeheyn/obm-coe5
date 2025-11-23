#!/usr/bin/env python3
"""
Generate a CoE5 mod file that modifies ritual costs and spawn rates.

This allows different percentage modifiers for different factions/classes,
creating a "tier list" balance system. Also supports global spawn rate modifiers.

Usage:
    python generate_tiered_cost_mod.py <config_file> [output_file]
    python generate_tiered_cost_mod.py --list-ritpows
    python generate_tiered_cost_mod.py --generate-config <output_config>

Examples:
    python generate_tiered_cost_mod.py my_balance.json
    python generate_tiered_cost_mod.py my_balance.json custom_mod.c5m
    python generate_tiered_cost_mod.py --list-ritpows
    python generate_tiered_cost_mod.py --generate-config balance_config.json
"""

import re
import sys
import json
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

# Spawn trait types that can be modified
SPAWN_TRAITS = [
    'spawnmon',      # General spawn (Dvala, etc.)
    'spawn1d6mon',   # Spawn 1d6 with percentage chance
    'satyrspawn',    # Dryad Queen satyr boost
    'harpyspawn',    # Dryad Queen harpy boost
    'centspawn',     # Dryad Queen centaur boost
    'minospawn',     # Dryad Queen minotaur boost
    'motherspawn',   # Various mother spawns (Hydra, Aztlan gods)
]


def parse_monster_data(filepath):
    """Parse the monster data file and extract monsters with spawn traits."""
    monsters = []
    current_monster = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Check for new monster definition
            match = re.match(r'newmonster\s+"([^"]+)"', line)
            if match:
                if current_monster and current_monster['spawns']:
                    monsters.append(current_monster)
                current_monster = {
                    'name': match.group(1),
                    'spawns': []
                }
                continue

            if current_monster:
                # Check for spawn traits
                for trait in SPAWN_TRAITS:
                    match = re.match(rf'{trait}\s+(\d+)', line.split('#')[0])
                    if match:
                        value = int(match.group(1))
                        # Extract comment if present
                        comment = ''
                        if '#' in line:
                            comment = line.split('#', 1)[1].strip()
                        current_monster['spawns'].append({
                            'trait': trait,
                            'value': value,
                            'comment': comment
                        })
                        break

        # Don't forget the last monster
        if current_monster and current_monster['spawns']:
            monsters.append(current_monster)

    return monsters


def parse_ritual_data(filepath):
    """Parse the ritual data file and extract ritual names, costs, and ritual power types."""
    rituals = []
    current_ritual = None
    ritpow_names = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Check for new ritual definition
            match = re.match(r'newritual\s+"([^"]+)"', line)
            if match:
                if current_ritual and current_ritual['costs']:
                    rituals.append(current_ritual)
                current_ritual = {
                    'name': match.group(1),
                    'costs': [],
                    'ritpow': None,
                    'ritpow_name': None,
                    'level': None
                }
                continue

            if current_ritual:
                # Check for ritual power
                match = re.match(r'ritpow\s+(\d+)\s+#\s+(.+)', line)
                if match:
                    ritpow_num = int(match.group(1))
                    ritpow_name = match.group(2).strip()
                    current_ritual['ritpow'] = ritpow_num
                    current_ritual['ritpow_name'] = ritpow_name
                    ritpow_names[ritpow_num] = ritpow_name
                    continue

                # Check for level
                match = re.match(r'level\s+(\d+)', line.split('#')[0])
                if match:
                    current_ritual['level'] = int(match.group(1))
                    continue

                # Check for cost line
                match = re.match(r'cost\s+(\d+)\s+(\d+)', line.split('#')[0])
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

    return rituals, ritpow_names


def process_config(config, ritpow_names):
    """Convert tier-based config to ritpow_modifiers format."""

    # Check if this is a tier-based config
    if 'tiers' in config and 'class_tiers' in config:
        tiers = config['tiers']
        class_tiers = config['class_tiers']

        # Build reverse lookup: ritpow_name -> ritpow_id
        name_to_id = {name: str(num) for num, name in ritpow_names.items()}

        # Convert class_tiers to ritpow_modifiers
        ritpow_modifiers = {}
        for class_name, tier in class_tiers.items():
            if class_name in name_to_id:
                ritpow_id = name_to_id[class_name]
                percentage = tiers.get(tier, 100)
                ritpow_modifiers[ritpow_id] = percentage

        return 100, ritpow_modifiers, tiers, class_tiers
    else:
        # Old format - direct ritpow_modifiers
        return config.get('default', 100), config.get('ritpow_modifiers', {}), None, None


def generate_mod_file(rituals, config, ritpow_names, output_path, project_dir):
    """Generate a mod file that modifies ritual costs based on config."""

    # Process config (supports both old and new tier-based format)
    default_pct, ritpow_modifiers, tiers, class_tiers = process_config(config, ritpow_names)

    # Get level modifiers if present
    level_modifiers = config.get('level_modifiers', {})

    modified_count = 0
    skipped_count = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# OBM Tiered Ritual Cost Modifier\n")
        f.write("# \n")
        f.write("# This mod adjusts ritual costs by class/ritual power type.\n")
        f.write("# Generated from Ritual Data v5.33.c5m\n")
        f.write("# \n")

        # Prepend base mod if specified
        base_mod = config.get('base_mod')
        if base_mod:
            base_path = project_dir / "data" / base_mod
            if base_path.exists():
                f.write("# " + "=" * 50 + "\n")
                f.write(f"# BASE MOD: {base_mod}\n")
                f.write("# (Our changes below override any conflicts)\n")
                f.write("# " + "=" * 50 + "\n\n")

                with open(base_path, 'r', encoding='utf-8') as base:
                    f.write(base.read())

                f.write("\n\n# " + "=" * 50 + "\n")
                f.write("# OBM MODIFICATIONS START HERE\n")
                f.write("# " + "=" * 50 + "\n\n")

        if level_modifiers:
            f.write("# Ritual Level Modifiers:\n")
            for level, pct in sorted(level_modifiers.items(), key=lambda x: int(x[0])):
                f.write(f"#   Level {level}: {pct}%\n")
            f.write("# \n")

        if tiers:
            # Tier-based format
            f.write("# Class Tier Definitions:\n")
            for tier_name, pct in sorted(tiers.items()):
                f.write(f"#   {tier_name}: {pct}%\n")
            f.write("# \n")
            f.write("# Class Assignments:\n")
            # Group classes by tier
            tier_groups = {}
            for class_name, tier in class_tiers.items():
                if tier not in tier_groups:
                    tier_groups[tier] = []
                tier_groups[tier].append(class_name)
            for tier_name in sorted(tier_groups.keys()):
                classes = sorted(tier_groups[tier_name])
                f.write(f"#   {tier_name}: {', '.join(classes)}\n")
            f.write("# \n\n")
        elif ritpow_modifiers:
            # Old format
            f.write(f"# Default modifier: {default_pct}%\n")
            f.write("# \n")
            f.write("# Custom modifiers:\n")
            for ritpow_id, pct in sorted(ritpow_modifiers.items(), key=lambda x: int(x[0])):
                f.write(f"#   Ritpow {ritpow_id}: {pct}%\n")
            f.write("# \n\n")
        else:
            f.write("\n")

        current_ritpow = None

        for ritual in rituals:
            ritpow = ritual['ritpow']
            level = ritual['level']

            # Determine base percentage for this ritual (from class tier)
            if ritpow is not None and str(ritpow) in ritpow_modifiers:
                class_pct = ritpow_modifiers[str(ritpow)]
            else:
                class_pct = default_pct

            # Apply level modifier if present
            if level is not None and str(level) in level_modifiers:
                level_pct = level_modifiers[str(level)]
            else:
                level_pct = 100

            # Combine modifiers (multiply percentages)
            percentage = (class_pct * level_pct) // 100

            # Skip if 100% (no change)
            if percentage == 100:
                skipped_count += 1
                continue

            # Add section header when ritpow changes
            if ritpow != current_ritpow:
                ritpow_name = ritual['ritpow_name'] or f"Unknown ({ritpow})"
                f.write(f"\n# --- {ritpow_name} ({percentage}%) ---\n\n")
                current_ritpow = ritpow

            f.write(f'selectritual "{ritual["name"]}"\n')

            for cost in ritual['costs']:
                resource_type = cost['type']
                original_amount = cost['amount']

                # Calculate new cost
                new_amount = math.ceil(original_amount * percentage / 100)
                new_amount = max(1, new_amount)

                resource_name = RESOURCE_TYPES.get(resource_type, f"Resource {resource_type}")
                f.write(f"cost {resource_type} {new_amount}  # {new_amount} {resource_name} (was {original_amount})\n")

            f.write("\n")
            modified_count += 1

    return modified_count, skipped_count


def generate_spawn_modifications(monsters, spawn_modifier, output_file):
    """Generate spawn modifications and append to output file."""
    if spawn_modifier == 100:
        return 0  # No changes needed

    modified_count = 0

    with open(output_file, 'a', encoding='utf-8') as f:
        f.write("\n# " + "=" * 50 + "\n")
        f.write("# SPAWN RATE MODIFICATIONS\n")
        f.write("# " + "=" * 50 + "\n")
        f.write(f"# Global spawn modifier: {spawn_modifier}%\n")
        f.write("# \n\n")

        for monster in monsters:
            f.write(f'selectmonster "{monster["name"]}"\n')

            for spawn in monster['spawns']:
                trait = spawn['trait']
                original_value = spawn['value']

                # Calculate new value
                new_value = math.ceil(original_value * spawn_modifier / 100)
                new_value = max(1, new_value)

                # Write the modification
                if spawn['comment']:
                    f.write(f"{trait} {new_value}  # was {original_value}; {spawn['comment']}\n")
                else:
                    f.write(f"{trait} {new_value}  # was {original_value}\n")

            f.write("\n")
            modified_count += 1

    return modified_count


def list_ritpows(ritpow_names):
    """Print all ritual power types."""
    print("\nRitual Power Types:")
    print("=" * 50)
    for num in sorted(ritpow_names.keys()):
        print(f"  {num}: {ritpow_names[num]}")
    print()


def generate_config_template(ritpow_names, output_path):
    """Generate a template config file."""
    config = {
        "description": "Tiered ritual cost modifier configuration",
        "default": 100,
        "ritpow_modifiers": {}
    }

    # Add all ritpows as comments in the format they'd use
    # We'll actually create it with 100% for all (no change by default)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('{\n')
        f.write('  "description": "Tiered ritual cost modifier configuration",\n')
        f.write('  "default": 100,\n')
        f.write('  "ritpow_modifiers": {\n')

        items = sorted(ritpow_names.items())
        for i, (num, name) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            # Default to 100% (no change)
            f.write(f'    "{num}": 100{comma}  \n')

        f.write('  }\n')
        f.write('}\n')

    # Also write a reference file
    ref_path = output_path.replace('.json', '_reference.txt')
    with open(ref_path, 'w', encoding='utf-8') as f:
        f.write("Ritual Power ID Reference\n")
        f.write("=" * 50 + "\n\n")
        for num, name in sorted(ritpow_names.items()):
            f.write(f"{num}: {name}\n")

    print(f"Generated config template: {output_path}")
    print(f"Generated reference file: {ref_path}")


def main():
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    ritual_data_file = project_dir / "data" / "Ritual Data v5.33.c5m"
    monster_data_file = project_dir / "data" / "Monster Data v5.33.c5m"

    if not ritual_data_file.exists():
        print(f"Error: Could not find '{ritual_data_file}'")
        sys.exit(1)

    if not monster_data_file.exists():
        print(f"Error: Could not find '{monster_data_file}'")
        sys.exit(1)

    # Parse ritual data
    rituals, ritpow_names = parse_ritual_data(ritual_data_file)

    # Parse monster data for spawn traits
    monsters_with_spawns = parse_monster_data(monster_data_file)

    # Handle command line arguments
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == '--list-ritpows':
        list_ritpows(ritpow_names)
        sys.exit(0)

    if sys.argv[1] == '--generate-config':
        if len(sys.argv) < 3:
            output = "balance_config.json"
        else:
            output = sys.argv[2]
        generate_config_template(ritpow_names, output)
        sys.exit(0)

    # Load config file
    config_file = sys.argv[1]
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)

    # Determine output filename
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = "tiered_ritual_costs.c5m"

    output_path = project_dir / "output" / output_file

    print(f"Parsing ritual data from: {ritual_data_file}")
    print(f"Found {len(rituals)} rituals with costs")
    print(f"Found {len(ritpow_names)} ritual power types")
    print(f"Found {len(monsters_with_spawns)} monsters with spawn traits")

    # Check for base mod
    base_mod = config.get('base_mod')
    if base_mod:
        base_path = project_dir / "data" / base_mod
        if not base_path.exists():
            print(f"Warning: Base mod '{base_mod}' not found at {base_path}")
        else:
            print(f"Using base mod: {base_mod}")

    print(f"\nGenerating mod file: {output_path}")
    modified, skipped = generate_mod_file(rituals, config, ritpow_names, output_path, project_dir)

    print(f"\nRitual Cost Results:")
    print(f"  Modified: {modified} rituals")
    print(f"  Skipped (100%): {skipped} rituals")

    # Handle spawn modifications
    spawn_modifier = config.get('spawn_modifier', 100)
    if spawn_modifier != 100:
        spawn_modified = generate_spawn_modifications(monsters_with_spawns, spawn_modifier, output_path)
        print(f"\nSpawn Rate Results:")
        print(f"  Modified: {spawn_modified} monsters")
        print(f"  Spawn modifier: {spawn_modifier}%")

    print(f"\nTo use this mod:")
    print(f"  1. Copy '{output_file}' to your CoE5 mods folder")
    print(f"  2. Enable the mod in the game's mod menu")


if __name__ == "__main__":
    main()
