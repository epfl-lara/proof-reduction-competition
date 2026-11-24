"""Coverage-aware deterministic aggregation."""


def aggregate(records, count):
    fields = (
        "length_reduction_pct",
        "heartbeat_reduction_pct",
        "compatibility_pct",
        "combined_pct",
    )
    complete = [
        r
        for r in records
        if r["final"]["status"] in {"passed", "failed", "invalid"}
        and r["final"]["scores"]["combined_pct"] is not None
    ]

    def mean(where, field):
        return (
            sum(r[where]["scores"][field] for r in complete) / len(complete)
            if complete
            else None
        )

    before = {f: mean("initial", f) for f in fields}
    after = {f: mean("final", f) for f in fields}
    all_complete = len(complete) == count
    return {
        "benchmark_problems": count,
        "recorded_problems": len(records),
        "fully_scored_problems": len(complete),
        "changed_problems": sum(r["changed"] for r in records),
        "attempts": sum(r["attempts"] for r in records),
        "measured_subset_initial_mean": before,
        "measured_subset_final_mean": after,
        "measured_subset_delta_pp": {
            f: after[f] - before[f] if complete else None for f in fields
        },
        "full_benchmark_combined_pct": after["combined_pct"] if all_complete else None,
        "full_benchmark_delta_pp": (
            after["combined_pct"] - before["combined_pct"] if all_complete else None
        ),
        "unscored_names": [r["name"] for r in records if r not in complete],
    }
