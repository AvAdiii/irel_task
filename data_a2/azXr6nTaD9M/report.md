# Concept DAG Report — azXr6nTaD9M

**Source language:** Hindi
**Concepts:** 9 | **Edges:** 8 | **Topo order:** 9/9

## Topological Order

1. Call By Value
2. Recursion
3. Tree
4. Factorial
5. Space Complexity
6. Stack
7. Time Complexity
8. Activation Record
9. Instruction Pointer

## Concepts

### Recursion
- Mentions: 34
- First seen: 00:02
- Sources: a, o

### Stack
- Mentions: 14
- First seen: 00:02
- Sources: a, o

### Activation Record
- Mentions: 7
- First seen: 02:19
- Sources: a, o

### Call By Value
- Mentions: 2
- First seen: 01:28
- Sources: a

### Instruction Pointer
- Mentions: 2
- First seen: 03:57
- Sources: a

### Time Complexity
- Mentions: 4
- First seen: 06:52
- Sources: a, o

### Space Complexity
- Mentions: 3
- First seen: 06:45
- Sources: a

### Tree
- Mentions: 1
- First seen: 00:32
- Sources: a

### Factorial
- Mentions: 1
- First seen: 00:13
- Sources: a

## Prerequisite Edges

| From | To | Type | Rule |
|------|-----|------|------|
| recursion | stack | domain_rule | recursion uses stack to store function calls |
| recursion | activation record | domain_rule | recursion creates activation records on the stack |
| recursion | factorial | causal | factorial is an example of recursion |
| stack | activation record | domain_rule | stack stores activation records |
| stack | instruction pointer | domain_rule | stack uses instruction pointer to manage function calls |
| recursion | time complexity | domain_rule | recursion has time complexity |
| recursion | space complexity | domain_rule | recursion has space complexity |
| call by value | activation record | causal | call by value is related to activation records |
