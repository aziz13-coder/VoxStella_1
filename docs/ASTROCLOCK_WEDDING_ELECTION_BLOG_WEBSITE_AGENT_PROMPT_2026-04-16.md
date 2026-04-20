# Website Agent Prompt: Wedding Election Blog

Date: 2026-04-16

## Purpose

This prompt is for an AI agent that **does have access to the website code** and is expected to polish, publish, and deploy a Vox Stella blog post.

The source draft lives here:

`C:\Users\sabaa\Downloads\codexhorary\docs\ASTROCLOCK_WEDDING_ELECTION_BLOG_DRAFT_2026-04-16.md`

## Prompt

```text
You have access to the website code and blog publishing workflow.

Your task is to take the source draft below, polish it into a production-ready blog post, integrate it into the website blog in the correct format and location, then deploy the updated blog.

Source draft:
C:\Users\sabaa\Downloads\codexhorary\docs\ASTROCLOCK_WEDDING_ELECTION_BLOG_DRAFT_2026-04-16.md

Primary goal:
- turn the draft into a polished, SEO-aware blog post that can drive traffic, explain the topic clearly, and guide readers toward the Vox Stella product

Secondary goals:
- preserve the product truth constraints
- improve readability, flow, and search intent targeting
- make the article feel editorial and useful rather than like a release note
- publish it in the blog and deploy the website

Critical truth constraints:
- Do NOT invent product implementation details, APIs, hidden scoring, or internal logic.
- Do NOT expose the technical reasoning behind the Alpha/Beta paths.
- Do NOT claim that Beta is universally better than Alpha.
- Do NOT claim that election astrology guarantees a successful marriage.
- Do NOT overpromise outcomes.

Safe product facts:
- Vox Stella is a desktop astrology app.
- Astro Clock includes an Election workflow.
- One Election matter is Marriage.
- The Marriage Election flow includes Alpha and Beta.
- Alpha keeps the original wedding election path and can optionally layer one natal snap.
- Beta uses a dedicated marriage path with chart A and chart B.

Editorial direction:
- Keep the article grounded, modern, and practical.
- The audience includes readers searching for wedding election astrology, marriage election astrology, best wedding date astrology, and how to choose a wedding date with astrology.
- Keep the tone authoritative but accessible.
- Avoid mystical exaggeration and avoid sounding overly technical.
- Make Alpha vs Beta easy to understand at a glance.
- Keep the comparison high-level and user-facing.

SEO direction:
- Strengthen keyword placement naturally, without stuffing.
- Improve headings, intro, slug, title, meta title, meta description, excerpt, and FAQ if needed.
- Preserve readability first.

Formatting and publishing tasks:
1. Inspect the existing website/blog structure and follow the site's current blog conventions.
2. Convert the draft into the correct content format used by the website.
3. Add any needed frontmatter or metadata.
4. Improve headline options and choose the strongest final title.
5. Refine the CTA and FAQ for conversion and search intent.
6. Add internal links where appropriate if relevant articles or product pages already exist.
7. Add the post to the website blog.
8. Run the appropriate checks/build steps.
9. Deploy the website.

Content priorities:
- The article should explain what wedding election astrology is.
- It should explain why someone would use a Marriage Election workflow.
- It should explain Alpha vs Beta without exposing internal logic.
- It should help readers understand that Alpha is the clearer first pass and Beta is the more relationship-centered refinement path.
- It should feel like a practical guide, not a product announcement.

If the draft needs trimming, preserve:
- the non-technical explanation
- the Alpha vs Beta comparison
- the practical workflow guidance
- the FAQ

If the website has a stronger editorial style, adapt the prose to match that style while keeping the factual constraints above.

Complete the task end to end: polish, publish, and deploy.
```
