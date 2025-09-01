from __future__ import annotations
import json
import os
from typing import List, Iterable
from .models import Entity


def _load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def entity_from_raw(raw: dict) -> Entity:
    # Map JSON path card into Entity (Feature/Being)
    enters = raw.get('enters_play') or 'within_reach'
    return Entity(
        id=raw.get('id'),
        title=raw.get('title'),
        entity_type=raw.get('card_type') or 'Path',
        presence=int(raw.get('presence', 1) or 1),
        progress_threshold=(int(raw['progress_threshold']) if isinstance(raw.get('progress_threshold'), int) else _parse_threshold(raw.get('progress_threshold'))),
        harm_threshold=int((raw.get('harm_threshold', -1) or -1)),
        area='within_reach' if enters == 'within_reach' else 'along_the_way',
    )


def _parse_threshold(value) -> int:
    if value is None:
        return -1
    if isinstance(value, int):
        return value
    s = ''.join(ch for ch in str(value) if ch.isdigit())
    return int(s) if s else -1


def build_woods_path_deck(base_dir: str, exclude_ids: Iterable[str] = ()) -> List[Entity]:
    woods = _load_json(os.path.join(base_dir, 'reference JSON', 'Path Sets', 'Terrain sets', 'woods.json'))
    deck: List[Entity] = []
    ex = set(exclude_ids or [])
    for raw in woods:
        cid = raw.get('id')
        if cid in ex:
            continue
        if raw.get('card_type') in ('Feature', 'Being'):
            deck.append(entity_from_raw(raw))
    return deck

