# Web-enabled Qwen trial: stopped by user

The user stopped this experiment at **14:07 Zurich time on October 7, 2026**.
It has **7/15 completed theorems, three interrupted workers and five unstarted
theorems**. There is no full-cohort mean. No requests were resumed or resampled
after the stop, and interrupted usage remains unknown.

The [stop summary](qwen38_xhigh_web_57m/stop_summary.json) records the exact
scope and preserves the [ten best already checked proofs](qwen38_xhigh_web_57m/best_checked_at_stop.jsonl),
including the interrupted workers' incumbents. This export includes evaluation
and completion provenance and is not a full competition submission. All seven
completed selections passed their required versions. Their
[saved-evidence audit](qwen38_xhigh_web_57m/audit_at_user_stop.json) passed;
it does not certify completion of the remaining eight problems.

On the same seven completed theorems, the local-tools run averaged 75.096867%
and this run averaged 76.449566%, a difference of +1.352699 percentage points.
This is a partial matched-subset comparison, not a benchmark mean or proof that
web improves results. The benchmark recorded **zero host web lookups**.

The gateway did not expose native hosted search, and its standalone search
endpoint returned HTTP 404. The maintained host tools instead use public
DuckDuckGo Lite search and bounded HTTPS page retrieval. A
[real Qwen availability probe](web_probe_02/generation.json) successfully used
both tools; [two exact retrieved sources](web_probe_02/evidence/web_requests.jsonl)
passed their [offline evidence audit](web_probe_02/web_audit.json).

The frozen comparison keeps model/effort, local semantic assets, seeds,
denominators, native retry limits and the 3420-second deadline fixed. Changes
are the web capability and necessary permission/tool text. See the
[launch plan](qwen38_xhigh_web_57m/launch_plan.json) and
[review](web_review.json). Web tools are retained behind `--web-search`.

Original request/config/result bytes, native events, proof ledgers, profiles,
retrieved source bodies and matching source snapshots are preserved. The stop
is recorded separately from deadline expiration. The prior running summary is
saved in `run_before_user_stop.json`; `run.json` now records the user stop.
Disposable scratch files and superseded endpoint smoke-response dumps were
removed; [cleanup inventory](cleanup.json) records that cleanup.
