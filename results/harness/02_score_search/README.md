# Score-feedback optimization

Queued after the structural-context cohort completes and passes its saved-evidence
audit. The [controller](../controller.json) will first run the initial theorem
with Astra/max, Astra/low and Luna/max, then retain those results and expand to
all 45 cells. See the [protocol](PROTOCOL.md) for the feedback tuple, selection,
stopping policy and comparisons. No score-search results are claimed yet.
