# Astrocartography PathFinder Engine Slice

Date: 2026-04-04

## Purpose

This memo documents the first real PathFinder engine slice built on top of the Astrocartography runtime asset layer.

It implements:

- source-backed goal models
- relocation scoring
- crossing/paran scoring
- weighted multi-city comparison

## Runtime Assets

Interpretation asset:

- `backend/knowledge/astrocartography/interpretation_runtime.json`

Goal-model asset:

- `backend/knowledge/astrocartography/place_goal_models.runtime.json`

Builders:

- `scripts/build_astrocartography_runtime_assets.py`
- `scripts/build_astrocartography_goal_models.py`

## First Goal Models

The first active PathFinder profiles are:

- `education`
- `love`
- `work`
- `money`

Each model is:

- explainable
- JSON-backed
- tied to recovered Almagest categories through `legacy_refs`
- limited to explicit component families:
  - line weights
  - crossing weights
  - relocation weights
  - relocation-metric modifiers

## Scoring Layers

### 1. Line layer

The engine scores matching nearby lines by:

- planet
- angle
- distance band
- linear falloff inside the band

### 2. Crossing layer

The engine surfaces nearby line-pair combinations and scores matching planet pairs.

Two crossing modes are currently supported:

- exact segment intersections
- fallback blended zones when two relevant lines are both nearby but no exact sampled intersection is found

### 3. Relocation layer

The engine recasts the natal chart for the inspected city and scores:

- target planets landing in favored houses
- target planets landing on favored angles
- derived relocation metrics such as visibility, partnership, stability, uncertainty, and benefic pressure

It also exposes a compact relocation summary:

- angular planets
- prominent occupied houses
- lightweight derived metrics

## API Additions

New endpoint:

- `/api/astro-clock/astrocartography/goals`

New compare endpoint:

- `/api/astro-clock/astrocartography/compare`

Extended endpoint:

- `/api/astro-clock/astrocartography/location`

The location endpoint now returns, when a goal is selected:

- nearby line readings
- nearby crossings
- relocation summary
- weighted goal evaluation

## Frontend Additions

The Astrocartography modal now includes:

- a `PathFinder Goal` selector in the left rail
- goal-aware inspect requests
- inspector badges for goal score
- crossings/parans section
- relocation summary section
- backend-ranked compare tray for pinned cities

## Current Best-City Scope

The weighted ranking engine currently operates over user-supplied candidate cities:

- inspect a city
- add it to the compare tray
- compare two or more pinned targets under one selected goal model

This is a real weighted best-city engine for bounded candidate sets, not yet a global atlas searcher over every city in the database.

## Important Boundaries

What is now source-backed:

- geometry
- interpretation copy
- line range policy
- goal categories and legacy mapping

What remains provisional:

- the exact numeric weight tuning inside the first four goal models
- the lightweight relocation-derived metrics
- the transit multiplier used in goal evaluation

Those are now isolated in data and engine code, which means they can be tuned without changing the core API shape.
