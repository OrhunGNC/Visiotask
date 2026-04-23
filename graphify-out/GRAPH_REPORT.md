# Graph Report - .  (2026-04-24)

## Corpus Check
- Corpus is ~5,510 words - fits in a single context window. You may not need a graph.

## Summary
- 104 nodes · 186 edges · 22 communities detected
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 37 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]

## God Nodes (most connected - your core abstractions)
1. `MacroApp` - 37 edges
2. `RoundedButton` - 14 edges
3. `SmoothScrollbar` - 11 edges
4. `ToggleSwitch` - 9 edges
5. `CustomInputDialog` - 8 edges
6. `RegionSelectorOverlay` - 8 edges
7. `run_macro()` - 4 edges
8. `AppState` - 4 edges
9. `_bind_mousewheel()` - 3 edges
10. `main()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `MacroApp`  [INFERRED]
  src\main.py → src\gui\app.py
- `MacroApp` --uses--> `RoundedButton`  [INFERRED]
  src\gui\app.py → src\gui\components.py
- `MacroApp` --uses--> `ToggleSwitch`  [INFERRED]
  src\gui\app.py → src\gui\components.py
- `MacroApp` --uses--> `SmoothScrollbar`  [INFERRED]
  src\gui\app.py → src\gui\components.py
- `MacroApp` --uses--> `CustomInputDialog`  [INFERRED]
  src\gui\app.py → src\gui\components.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.0
Nodes (1): _bind_mousewheel()

### Community 1 - "Community 1"
Cohesion: 0.0
Nodes (2): MacroApp, main()

### Community 2 - "Community 2"
Cohesion: 0.0
Nodes (2): CustomInputDialog, SmoothScrollbar

### Community 3 - "Community 3"
Cohesion: 0.0
Nodes (2): run_macro(), find_and_click()

### Community 4 - "Community 4"
Cohesion: 0.0
Nodes (9): PROJECT_CONTEXT.md, macro.py, app.py, components.py, overlay.py, vision.py, main.py, config.py (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.0
Nodes (1): RoundedButton

### Community 6 - "Community 6"
Cohesion: 0.0
Nodes (1): RegionSelectorOverlay

### Community 7 - "Community 7"
Cohesion: 0.0
Nodes (1): ToggleSwitch

### Community 8 - "Community 8"
Cohesion: 0.0
Nodes (1): AppState

### Community 9 - "Community 9"
Cohesion: 0.0
Nodes (2): README.md, requirements.txt

### Community 10 - "Community 10"
Cohesion: 0.0
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 0.0
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 0.0
Nodes (0): 

### Community 13 - "Community 13"
Cohesion: 0.0
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.0
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 0.0
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 0.0
Nodes (1): src/__init__.py

### Community 17 - "Community 17"
Cohesion: 0.0
Nodes (1): engine/__init__.py

### Community 18 - "Community 18"
Cohesion: 0.0
Nodes (1): gui/__init__.py

### Community 19 - "Community 19"
Cohesion: 0.0
Nodes (1): image/__init__.py

### Community 20 - "Community 20"
Cohesion: 0.0
Nodes (1): utils/__init__.py

### Community 21 - "Community 21"
Cohesion: 0.0
Nodes (1): createexe.txt

## Knowledge Gaps
- **Thin community `Community 9`** (2 nodes): `README.md`, `requirements.txt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `src/__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `engine/__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `gui/__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `image/__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `utils/__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `createexe.txt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.