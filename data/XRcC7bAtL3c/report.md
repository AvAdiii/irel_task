# Pedagogical Flow Report
**Video:** `XRcC7bAtL3c`

## Pipeline Summary
| Metric | Value |
|--------|-------|
| Raw ASR segments | 93 |
| Normalized segments | 80 |
| Concepts extracted | 14 |
| Graph edges | 51 |
| Causal anchors detected | 20 |
| Causal edges created | 14 |

## Topological Order (Teaching Sequence)
1. **tree**
2. **node**
3. **root node**
4. **children**
5. **left subtree**
6. **right subtree**
7. **binary tree**
8. **dummy node**
9. **tree traversal**
10. **traversal technique**
11. **in-order traversal**
12. **post-order traversal**
13. **pre-order traversal**
14. **leaf node**

## Concepts
| # | Concept | Mentions | First (s) | Sources |
|---|---------|----------|-----------|---------|
| 1 | pre-order traversal | 13 | 0 | asr, asr+ocr, ocr |
| 2 | root node | 34 | 0 | asr+ocr, ocr |
| 3 | tree | 12 | 3 | asr |
| 4 | tree traversal | 2 | 3 | asr |
| 5 | in-order traversal | 10 | 6 | asr |
| 6 | post-order traversal | 17 | 6 | asr, asr+ocr, ocr |
| 7 | left subtree | 29 | 12 | asr, asr+ocr, ocr |
| 8 | node | 11 | 12 | asr, ocr |
| 9 | right subtree | 13 | 22 | asr, asr+ocr, ocr |
| 10 | traversal technique | 4 | 78 | asr |
| 11 | binary tree | 2 | 99 | asr |
| 12 | children | 7 | 105 | asr |
| 13 | leaf node | 2 | 114 | asr |
| 14 | dummy node | 2 | 120 | asr |

## Example Tree
Nodes: A, B, C, D, E, F, G, H, I

## Edge Distribution
| Edge Type | Count |
|-----------|-------|
| is_part_of | 1 |
| is_prerequisite_for | 27 |
| refines | 3 |
| temporal_precedence | 20 |

## Prerequisite Edges (Domain + Causal)
- **tree** -> **binary tree** (is_prerequisite_for, conf=0.90)
- **tree** -> **tree traversal** (is_prerequisite_for, conf=0.90)
- **binary tree** -> **tree traversal** (is_prerequisite_for, conf=0.90)
- **node** -> **root node** (is_prerequisite_for, conf=0.80)
- **node** -> **leaf node** (is_prerequisite_for, conf=0.80)
- **root node** -> **tree traversal** (is_prerequisite_for, conf=0.80)
- **children** -> **left subtree** (is_prerequisite_for, conf=0.70)
- **children** -> **right subtree** (is_prerequisite_for, conf=0.70)
- **tree traversal** -> **pre-order traversal** (refines, conf=0.90)
- **tree traversal** -> **in-order traversal** (refines, conf=0.90)
- **tree traversal** -> **post-order traversal** (refines, conf=0.90)
- **traversal technique** -> **pre-order traversal** (is_prerequisite_for, conf=0.70)
- **traversal technique** -> **in-order traversal** (is_prerequisite_for, conf=0.70)
- **traversal technique** -> **post-order traversal** (is_prerequisite_for, conf=0.70)
- **left subtree** -> **pre-order traversal** (is_prerequisite_for, conf=0.70)
- **right subtree** -> **pre-order traversal** (is_prerequisite_for, conf=0.70)
- **left subtree** -> **in-order traversal** (is_prerequisite_for, conf=0.80)
- **right subtree** -> **in-order traversal** (is_prerequisite_for, conf=0.80)
- **left subtree** -> **post-order traversal** (is_prerequisite_for, conf=0.80)
- **right subtree** -> **post-order traversal** (is_prerequisite_for, conf=0.80)
- **dummy node** -> **traversal technique** (is_part_of, conf=0.60)
- **root node** -> **right subtree** (is_prerequisite_for, conf=0.70)
- **root node** -> **left subtree** (is_prerequisite_for, conf=0.70)
- **node** -> **right subtree** (is_prerequisite_for, conf=0.70)
- **node** -> **left subtree** (is_prerequisite_for, conf=0.70)
- **root node** -> **pre-order traversal** (is_prerequisite_for, conf=0.75)
- **node** -> **pre-order traversal** (is_prerequisite_for, conf=0.75)
- **root node** -> **in-order traversal** (is_prerequisite_for, conf=0.75)
- **root node** -> **post-order traversal** (is_prerequisite_for, conf=0.75)
- **node** -> **post-order traversal** (is_prerequisite_for, conf=0.75)
- **tree** -> **node** (is_prerequisite_for, conf=0.75)
