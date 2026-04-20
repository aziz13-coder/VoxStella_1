# Astrocartography Blog Prompts

Date: 2026-04-07

## Purpose

Prepare a production-ready writing prompt for an AI writing agent that does **not** have access to the Vox Stella codebase, internal docs, or product workflow.

The target post is:

1. `Astrocartography App: Compare Cities for Home, Love, Career, and Travel`

## Important truth constraints

The writing agent must not invent product details.

These points are safe to state:

- Vox Stella is a desktop astrology app.
- One of its features is Astrocartography.
- The Astrocartography workflow is map-first.
- Users can inspect planetary lines on a world map.
- Users can inspect cities and compare locations.
- The feature includes deeper inspection layers such as local space, parans, and report-style interpretation.
- The product supports goal-based location ranking for practical categories like home, love, career, and money.

These points must be handled carefully:

- Do **not** claim the public UI currently ships a visible dedicated `travel` preset unless that is confirmed elsewhere.
- If the sample backend output below is used, describe it as a `travel-oriented backend example` or `internal sample engine run`, not as a guaranteed public preset label in the live picker.
- Do **not** invent APIs, algorithm names, weighting systems, or hidden technical architecture.
- Do **not** promise outcomes or say the software can tell readers the one objectively best city for their life.

## SEO direction

Primary search-intent phrases:

- `astrocartography app`
- `astrocartography software`
- `relocation astrology software`
- `compare cities astrology`
- `astrocartography map`

Secondary phrases:

- `where should I move astrology`
- `best places to live astrocartography`
- `location astrology`
- `relocation astrology`
- `local space astrology`
- `parans astrology`

## Existing content to avoid duplicating

Vox Stella already has a relocation explainer with this angle:

- `What Is Relocation Astrology? How to Use an Astrocartography Map to Compare Cities`

So this new post should **not** become another general "what is astrocartography" guide.

This post should focus on:

- software intent
- map-first workflow
- practical city comparison
- showing how readers move from map to shortlist to inspection

## Product context the writer may rely on

- Astrocartography in Vox Stella is a location astrology workflow.
- The map is the primary canvas.
- Users can review line patterns across the world instead of jumping straight into one city.
- Users can inspect a city to see nearby lines and a deeper interpretation layer.
- Users can compare cities side by side.
- The product includes advanced layers beyond the first map view, including local space and parans.
- The feature is useful for relocation and travel planning as a structured decision aid, not as magic certainty.

## Engine-backed sample example for the article

Use the following sample **exactly as provided**.

This is a real backend run from the local engine, prepared for content illustration.

### Sample chart used for the example

- sample chart datetime: `1988-05-23 09:15`
- timezone: `America/New_York`
- sample birth location: `New York, New York, USA`
- usage note: this is an arbitrary demonstration chart for content, not a real user case study

### Sample travel-oriented backend run

This was run as a travel-oriented internal backend example across a short leisure shortlist:

- `Barcelona, Spain`
- `Lisbon, Portugal`
- `Rio de Janeiro, Brazil`

Returned ranking:

1. `Barcelona, Spain`
   - score: `43`
   - raw score: `5.903`
   - lead line: `Mercury MC`
   - relocation headline: `Relocation is led by Mercury MC, Venus MC.`
   - support notes:
     - `Beliefs 100 / 100`
     - `Restoration 100 / 100`
     - `Visibility 67 / 100`
   - caution notes:
     - `Malefic Pressure 25 / 100`
     - `Health Risk 25 / 100`

2. `Lisbon, Portugal`
   - score: `43`
   - raw score: `5.903`
   - lead line: `Sun MC`
   - relocation headline: `Relocation is led by Mercury MC, Venus MC.`
   - support notes:
     - `Beliefs 100 / 100`
     - `Restoration 100 / 100`
     - `Visibility 67 / 100`
   - caution notes:
     - `Malefic Pressure 25 / 100`
     - `Health Risk 25 / 100`

3. `Rio de Janeiro, Brazil`
   - score: `35`
   - raw score: `2.740`
   - lead line: `Jupiter MC`
   - relocation headline: `Relocation is led by Sun MC, Jupiter MC.`
   - support notes:
     - `Career Status 100 / 100`
     - `Personal Growth 75 / 100`
     - `Body Presence 75 / 100`
   - caution notes:
     - `Malefic Pressure 50 / 100`
     - `Health Risk 50 / 100`

### How to use this sample in the article

- Use it as one short example section in the middle of the post.
- Present it as an illustration of how a location-ranking workflow can turn a vague travel question into a structured shortlist.
- Do **not** say this proves Barcelona or Lisbon are "the best" places for everyone.
- Do **not** say the engine guarantees outcomes.
- Do **not** invent extra destinations or extra scores.
- It is acceptable to say the sample scan surfaced `Barcelona` and `Lisbon` as the strongest options in this mini-shortlist, while `Rio` landed lower.

## Prompt

```text
Write a polished, SEO-focused blog post for the Vox Stella website.

Important constraints:
- You do NOT have access to the app code, internal files, internal docs, or engineering workflow.
- Do NOT invent implementation details, APIs, hidden algorithms, or technical architecture.
- Use only the product/context details provided below.
- The article should feel authoritative, practical, modern, and readable.
- The goal is to attract organic search traffic from people searching for astrocartography tools, astrocartography apps, relocation astrology software, and practical ways to compare cities.
- The article should be SEO-strong without reading like keyword stuffing.

This is the article topic:
Astrocartography App: Compare Cities for Home, Love, Career, and Travel

Core article goal:
- Position Vox Stella as a serious astrocartography app for people who want a map-first way to compare locations.
- Show that the product is useful because it helps readers move from broad map exploration into city-level comparison and deeper inspection.
- Make the post attractive to tool-intent searchers, not just general astrology readers.

Product facts you may rely on:
- Vox Stella is a desktop astrology app.
- It includes an Astrocartography feature.
- The Astrocartography workflow is map-first.
- Users can inspect a world map with planetary angular lines.
- Users can inspect cities in more detail.
- Users can compare cities side by side.
- The product includes deeper inspection layers such as local space, parans, and a compact report-style reading.
- The product supports goal-based location ranking for practical categories such as home, love, career, and money.
- The feature is useful for relocation and travel planning as a structured decision aid, not as absolute certainty.

Critical truth constraints:
- Do NOT claim the public app definitely ships a visible dedicated travel preset unless explicitly stated below.
- You MAY use the sample backend run below, but you must frame it as a travel-oriented internal backend example used to illustrate how the ranking workflow works.
- Do NOT imply that every user will get the same destinations.
- Do NOT oversell astrology as proof.

Existing content to avoid duplicating:
- Vox Stella already has a relocation explainer titled:
  What Is Relocation Astrology? How to Use an Astrocartography Map to Compare Cities
- So this new piece should not become another broad beginner definition article.
- It should stay focused on software intent, workflow, and practical comparison.

SEO requirements:
- Naturally incorporate phrases such as:
  - astrocartography app
  - astrocartography software
  - relocation astrology software
  - astrocartography map
  - compare cities astrology
  - location astrology
  - best places to live astrocartography
  - where should I move astrology
- Use them naturally, not mechanically.

Use this sample engine example exactly as provided:

Sample chart for demonstration:
- 1988-05-23 09:15
- timezone: America/New_York
- birth location: New York, New York, USA
- note: arbitrary demonstration chart for content, not a real user case study

Travel-oriented internal backend example across a mini-shortlist:

1. Barcelona, Spain
- score: 43
- raw score: 5.903
- lead line: Mercury MC
- relocation headline: Relocation is led by Mercury MC, Venus MC.
- support notes:
  - Beliefs 100 / 100
  - Restoration 100 / 100
  - Visibility 67 / 100
- caution notes:
  - Malefic Pressure 25 / 100
  - Health Risk 25 / 100

2. Lisbon, Portugal
- score: 43
- raw score: 5.903
- lead line: Sun MC
- relocation headline: Relocation is led by Mercury MC, Venus MC.
- support notes:
  - Beliefs 100 / 100
  - Restoration 100 / 100
  - Visibility 67 / 100
- caution notes:
  - Malefic Pressure 25 / 100
  - Health Risk 25 / 100

3. Rio de Janeiro, Brazil
- score: 35
- raw score: 2.740
- lead line: Jupiter MC
- relocation headline: Relocation is led by Sun MC, Jupiter MC.
- support notes:
  - Career Status 100 / 100
  - Personal Growth 75 / 100
  - Body Presence 75 / 100
- caution notes:
  - Malefic Pressure 50 / 100
  - Health Risk 50 / 100

Instructions for using the sample:
- Use it in one section in the middle of the article.
- Present it as a concrete example of how a vague travel question can turn into a structured shortlist.
- You may say that Barcelona and Lisbon surfaced as the strongest options in this sample run, while Rio landed lower.
- Do not invent extra cities or extra scores.
- Do not say this is scientific proof.

Output format:
Please provide the following in order:

1. 5 SEO title options
- At least 2 should directly target "astrocartography app"
- At least 1 should directly target "astrocartography software"

2. Recommended URL slug

3. Meta title
- Around 60 characters max

4. Meta description
- Around 155 characters max

5. Primary keyword
6. Secondary keywords
7. Long-tail keywords

8. Article outline
- H1
- H2s
- H3s where useful

9. Full blog post
Requirements:
- 1,400 to 2,000 words
- strong opening paragraph aimed at someone evaluating a tool
- clear distinction between map exploration and city-level comparison
- explain why compare workflow matters more than reading one line in isolation
- include one section using the exact sample backend travel example above
- mention local space and parans as deeper layers, without overexplaining them
- mention Vox Stella naturally, without sounding like a product release note
- no fake technical claims
- no mystical exaggeration
- no promises

10. On-page FAQ
- 5 to 7 questions
- questions should support SEO and user trust

11. Suggested internal links
- include likely anchor text suggestions to:
  - the existing relocation guide
  - the product page
  - the features page
```
