# Pedagogical Flow Report
**Video:** `N2P7w22tN9c`

## Pipeline Summary
| Metric | Value |
|--------|-------|
| Raw ASR segments | 143 |
| Normalized segments | 140 |
| Concepts extracted | 12 |
| Graph edges | 41 |
| Causal anchors detected | 0 |
| Causal edges created | 0 |

## Topological Order (Teaching Sequence)
1. **edge**
2. **vertex**
3. **graph**
4. **graph traversal**
5. **tree**
6. **tree traversal**
7. **visited**
8. **stack**
9. **depth first search**
10. **traversal technique**
11. **pre-order traversal**
12. **breadth first search**

## Concepts
| # | Concept | Mentions | First (s) | Sources |
|---|---------|----------|-----------|---------|
| 1 | graph | 12 | 2 | asr, asr+ocr, ocr |
| 2 | graph traversal | 3 | 36 | asr |
| 3 | tree | 4 | 48 | asr |
| 4 | tree traversal | 1 | 48 | asr |
| 5 | vertex | 5 | 66 | asr |
| 6 | edge | 3 | 75 | asr |
| 7 | depth first search | 3 | 174 | asr |
| 8 | visited | 1 | 304 | asr |
| 9 | stack | 3 | 425 | asr |
| 10 | pre-order traversal | 1 | 509 | ocr |
| 11 | traversal technique | 1 | 639 | asr |
| 12 | breadth first search | 1 | 668 | asr |

## Example Tree
Nodes: A, B, C, D, E, F, G, H, I, K, L, M, N, O, P, R, S, T, U, V, W, X, Y

## Edge Distribution
| Edge Type | Count |
|-----------|-------|
| is_prerequisite_for | 10 |
| refines | 3 |
| temporal_precedence | 28 |

## Prerequisite Edges (Domain + Causal)
- **tree** -> **tree traversal** (is_prerequisite_for, conf=0.90)
- **tree traversal** -> **pre-order traversal** (refines, conf=0.90)
- **traversal technique** -> **pre-order traversal** (is_prerequisite_for, conf=0.70)
- **graph** -> **graph traversal** (is_prerequisite_for, conf=0.90)
- **vertex** -> **graph** (is_prerequisite_for, conf=0.70)
- **edge** -> **graph** (is_prerequisite_for, conf=0.70)
- **graph traversal** -> **breadth first search** (refines, conf=0.90)
- **graph traversal** -> **depth first search** (refines, conf=0.90)
- **graph** -> **breadth first search** (is_prerequisite_for, conf=0.80)
- **graph** -> **depth first search** (is_prerequisite_for, conf=0.80)
- **stack** -> **depth first search** (is_prerequisite_for, conf=0.80)
- **visited** -> **breadth first search** (is_prerequisite_for, conf=0.70)
- **visited** -> **depth first search** (is_prerequisite_for, conf=0.70)
