# Campaign Optimizer Golden Sample Checklist

Use this checklist when testing one image creative and one short video creative under 60 seconds.

## Contract Checks

- Video response has `frames_analyzed` between 12 and 16.
- Image response has `frames_analyzed` equal to 1.
- `ai_analysis.targeting.top_interests`, `behaviors`, `recommended_cities`, and `excluded_audiences` are present.
- `agent_analysis` includes evidence, Meta targeting, hook, virality, copy, and diagnosis sections.
- UI renders without crashing when transcript, generated hooks, or generated copy are empty.

## Quality Checks

- Meta targeting is specific enough to create real ad sets.
- Interest and behavior picks are tied to the visible creative or transcript.
- City reasoning explains why those cities fit the product, price point, or cultural use case.
- Hook reasoning cites the first few seconds or the image composition.
- Generated copy has at least three distinct angles, not the same line reworded.
- Fixes are actionable for the next edit, not generic advice.

## Reliability Checks

- Missing API key shows a friendly fallback response.
- OpenAI failure records a failed request in the admin panel.
- Limit exceeded returns a clear frontend message with remaining quota.
- Admin stats show usage counts, fallback rate, model profile, and recent failures.
