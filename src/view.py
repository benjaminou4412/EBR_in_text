from __future__ import annotations
from typing import List, Optional
from .models import GameState, Action, ActionTarget, CommitDecision


def render_state(state: GameState) -> None:
    r = state.ranger
    print("=== Earthborne Rangers - Refactor Demo ===")
    print(f"Ranger: {r.name} | Energy AWA {r.energy['AWA']} FIT {r.energy['FIT']} SPI {r.energy['SPI']} FOC {r.energy['FOC']} | Injury {r.injury}")
    print("Hand:")
    for i, c in enumerate(r.hand, start=1):
        icons = ", ".join(f"{k[:3]}+{v}" for k, v in c.approach.counts.items() if v)
        if not icons:
            icons = "-"
        print(f" {i}. {c.title} [{icons}]")

    print("\nIn Play:")
    for e in state.entities:
        if e.entity_type == "Feature":
            print(f" - Feature: {e.title} prog {e.progress}/{e.progress_threshold} pres {e.presence} area {e.area}")
        elif e.entity_type == "Being":
            print(f" - Being: {e.title} prog {e.progress}/{e.progress_threshold} harm {e.harm}/{e.harm_threshold} pres {e.presence} {'(exhausted)' if e.exhausted else ''}")
        elif e.entity_type == "Weather":
            print(f" - Weather: {e.title} clouds {e.clouds}")
    print("")


def choose_action(actions: List[Action]) -> Optional[Action]:
    if not actions:
        print("No actions available.")
        return None
    print("Choose an action:")
    for i, a in enumerate(actions, start=1):
        src = a.source_title or a.source_id or ""
        print(f" {i}. {a.name} {{aspect {a.aspect}, approach {a.approach}}} [{src}]")
    raw = input("> ").strip().lower()
    if raw in ("q", "quit"):
        return None
    try:
        idx = int(raw) - 1
        return actions[idx]
    except Exception:
        return None


def choose_target(state: GameState, action: Action) -> Optional[str]:
    if not action.target_provider:
        return None
    targets = action.target_provider(state)
    if not targets:
        print("No valid targets.")
        return None
    print("Choose target:")
    for i, t in enumerate(targets, start=1):
        print(f" {i}. {t.title}")
    try:
        idx = int(input("> ").strip()) - 1
        return targets[idx].id
    except Exception:
        return None


def choose_commit(action: Action, hand_size: int) -> CommitDecision:
    # Energy commitment
    energy = 1  # default
    raw_energy = input(f"Commit [{action.aspect}] energy (default 1): ").strip()
    if raw_energy:
        try:
            energy = int(raw_energy)
            if energy < 1:
                print(f"Invalid energy amount, using default (1)")
                energy = 1
        except ValueError:
            print(f"Invalid input '{raw_energy}', using default (1)")
            energy = 1
    
    # Card commitment
    raw = input(f"Commit cards for [{action.approach}] (comma-separated indices, blank=none): ").strip()
    hand_indices = []
    if raw:
        try:
            picks = [int(x) - 1 for x in raw.split(",") if x.strip()]
            picks = [p for p in picks if 0 <= p < hand_size]
            # dedupe preserve order
            seen = set()
            for p in picks:
                if p not in seen:
                    hand_indices.append(p)
                    seen.add(p)
        except ValueError:
            print("Invalid card indices, committing no cards")
    
    return CommitDecision(hand_indices=hand_indices, energy=energy)

