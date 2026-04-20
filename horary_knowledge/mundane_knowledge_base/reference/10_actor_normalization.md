# Actor Normalization

Status: first pass

## Purpose

Bonatti and parts of the later tradition use actor language that does not map one-to-one onto modern states. This file records a cautious translation layer so the future mundane feature can preserve the doctrine without pretending medieval institutions and modern states are identical.

## Traditional To Modern Mapping

### King

Modern nearest equivalents:

- head of state
- head of government
- executive authority

Do not assume these are always the same office.

### Nobles

Modern nearest equivalents:

- ruling elite
- cabinet
- senior party leadership
- entrenched political and administrative class

### Rustics or common people

Modern nearest equivalents:

- general population
- laboring population
- non-elite public

### Soldiers

Modern nearest equivalents:

- military forces
- security apparatus
- organized armed capacity of the state

### Clerics and bishops

Modern nearest equivalents:

- formal religious leadership
- church hierarchy
- institutional moral authority where politically relevant

## Working Translation Rules

### 1. Preserve the source actor first

When doctrine comes from Bonatti or another traditional source:

- keep the original actor label in the knowledge base
- add a modern interpretation note beside it
- do not erase the original class term

### 2. Avoid over-normalization

Do not flatten:

- king -> president
- nobles -> politicians
- people -> voters

These are sometimes approximately right, but often too coarse.

### 3. Map by political function, not title

The safer mapping rule is:

- identify who exercises the function described in the doctrine
- then map the actor to the modern polity under study

### 4. Keep regime sensitivity

Different polities require different mappings:

- monarchy
- republic
- parliamentary democracy
- military regime
- party-state

## Immediate Product Use

The future runtime should carry both:

- `source_actor`
- `normalized_actor`

This makes it possible to:

- preserve the doctrine
- explain the translation
- avoid hiding weak assumptions
