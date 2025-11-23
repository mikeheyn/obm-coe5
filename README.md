# obm-coe5

A mod toolkit for Conquest of Elysium 5.

## About

This repository contains tools for creating custom modifications for Conquest of Elysium 5 (CoE5), a turn-based fantasy strategy game. The primary feature is a ritual cost modifier that allows you to scale all ritual costs by a percentage.

## Features

### Ritual Cost Modifier

The `generate_cost_mod.py` script generates a mod file that modifies all ritual costs by a specified percentage.

**Usage:**

```bash
python generate_cost_mod.py <percentage> [output_file]
```

**Examples:**

```bash
# Reduce all costs to 50% of original
python generate_cost_mod.py 50

# Increase all costs to 150% of original
python generate_cost_mod.py 150

# Custom output filename
python generate_cost_mod.py 75 my_custom_mod.c5m
```

**Output:**

The script generates a `.c5m` mod file that uses `selectritual` to modify each ritual's cost. Comments show both the new and original values for reference.

Example output:
```
selectritual "Lesser Ritual of Mastery"
cost 2 13  # 13 Herbs (was 25)

selectritual "Ritual of Mastery"
cost 2 75  # 75 Herbs (was 150)
```

**Supported resource types:**
- Gold, Iron, Herbs, Fungus, Gems
- Hands, Sacrifices, Blood, Demon Parts
- Unburied, Silk, Relics, Prisoners
- Coins, Corpses, Monster Parts, Entrails
- Hearts, Skulls

## Installation

1. Run the script to generate your desired cost mod:
   ```bash
   python generate_cost_mod.py 50
   ```

2. Copy the generated `.c5m` file to your CoE5 mods directory:
   - Windows: `%USERPROFILE%\AppData\Roaming\coe5\mods\`
   - Linux: `~/.coe5/mods/`

3. Enable the mod in the game's mod menu

## Files

- `Ritual Data v5.33.c5m` - Reference file containing all base game ritual data
- `generate_cost_mod.py` - Script to generate ritual cost modifier mods
- `ritual_costs_*.c5m` - Generated mod files (not tracked in git)

## Requirements

- Python 3.6+
- Conquest of Elysium 5

## License

This project is for personal/community use with Conquest of Elysium 5.
