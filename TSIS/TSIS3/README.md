# TSIS3 — Racer (Practice 12)

A lane-based arcade racer built with Python & Pygame.

## Quick start

```bash
pip install pygame
python main.py
```

## Controls
| Key | Action |
|-----|--------|
| ← / A | Move car left |
| → / D | Move car right |

## File structure
```
TSIS3/
├── main.py          # Entry point + screen state machine
├── racer.py         # Road, Player, Enemies, Coins, Obstacles, Power-ups
├── ui.py            # All Pygame screens (no external UI libs)
├── persistence.py   # JSON save / load for settings & leaderboard
├── settings.json    # Saved preferences (auto-created)
├── leaderboard.json # Top-10 scores (auto-created)
└── assets/          # Reserved for images / sounds (optional)
```

## Features built on top of Practice 10 & 11

### Practice 10 (foundation — already done)
- Lane-based road scrolling
- Random coin spawning
- Coin counter display

### Practice 11 (foundation — already done)
- Weighted coins: Bronze ×1 · Silver ×3 · Gold ×5
- Enemy speed scales with coins collected

### Practice 12 (new)

#### 3.1 Lane hazards & road events
| Object | Effect |
|--------|--------|
| 🟤 Oil spill | Slow + locked lanes for 3 s |
| 🔴 Barrier | Instant crash (or absorbs shield) |
| ⚫ Pothole | Brief slow-down |
| 🟡 Speed bump | Brief slow-down |
| 🟢 Nitro strip | Speed boost for 3 s |

#### 3.2 Dynamic traffic
- Enemy cars scroll toward you in random lanes
- Safe-spawn: barriers never spawn on player's lane
- Density & speed increase with difficulty level

#### 3.3 Power-ups (one active at a time)
| Icon | Name | Effect |
|------|------|--------|
| N (blue) | Nitro | +130 px/s for 4 s |
| S (gold) | Shield | Absorb next 1 collision |
| R (green) | Repair | Instantly clear all debuffs |

- Power-ups despawn after 9 s if uncollected
- Active power-up + remaining time shown in HUD

#### 3.4 Score & leaderboard
- **Score** = coin_value × 12 + distance + level_bonus
- Distance meter in HUD
- Username entry before race
- Top-10 screen with rank / name / score / distance / coins
- Auto-saved to `leaderboard.json`

#### 3.5 Screens
- **Main Menu**: Play · Leaderboard · Settings · Quit
- **Settings**: Sound toggle · Car colour (5 options) · Difficulty (Easy / Normal / Hard)
- **Game Over**: Score · Distance · Coins + Retry / Main Menu
- **Leaderboard**: Top 10 with medal colours for top 3
- Settings auto-saved to `settings.json` on back

#### 3.6 Difficulty scaling
Every 500 m the level increases:
- Enemy speed +22 px/s × difficulty multiplier
- Road speed  +16 px/s × difficulty multiplier
- More frequent spawns (obstacles, traffic)
- Barriers appear from level 3+
- Difficulty multipliers: Easy 0.7 × · Normal 1.0 × · Hard 1.5 ×
