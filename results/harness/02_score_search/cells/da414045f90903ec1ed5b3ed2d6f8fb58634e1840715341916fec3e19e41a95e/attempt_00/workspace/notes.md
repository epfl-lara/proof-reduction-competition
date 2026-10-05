1. Factored replacement-number identity and divisibility helper; sum all 9 swaps, subtract 7D, combine two relations, cancel 10^i by explicit Bezout coprimality. Valid all versions. 273 tokens, 4943.684 primary heartbeats, score 88.595833.
Next: focus simp/ring and avoid elaborating numeric powers during algebra.
2. Replaced both broad simp invocations with exact simp-only lists. All valid: 295 tokens, 2305.980 HB, score 93.312441 (best).
3. Merged swap identity into divisibility helper H via convert. All valid: 242 tokens, 2294.108 HB, score 93.766955 (best).
4. Replaced final hn/ring derivation with omega after splitting sub_mul at local pointwise hypotheses. Valid but slower: 213 tokens, 3029.599 HB, score 92.638368. Reverted.
5. Combined two divisibility subtractions and kept one ring call. All valid: 226 tokens, 2042.014 HB, score 94.365452 (best).
6. Replaced final ring with sub_mul + omega on equality. All valid, slower: 232 tokens, 2467.349 HB, score 93.526983. Reverted.
7. Abstracted 10^i before final ring1. Valid: 235 tokens, 2021.435 HB, score 94.330212. Negligible HB gain not worth extra tokens; reverted.
8. H uses difference of weighted digits instead of weighted difference. Removes distributivity/zero simp rules. Valid: 221 tokens, 1969.633 HB, score 94.540606 (best).
9. Summation hypothesis rewritten in place and refolded digits with congr_fun (no whole simpa). Valid: 220 tokens, 1773.077 HB, score 94.913615 (best).
10. Expanded 9 as 7+1+1 then used simp/abel instead of ring. Valid but slower and longer: 243 tokens, 1988.465 HB, score 94.326132. Reverted.
11. Substituted digits_to_num and used local N abbreviation instead of refolding sums. Valid but worse: 237 tokens, 1959.655 HB, score 94.428568. Reverted.
12. H uses directed rw for function definition and sum subtraction before focused simp. Valid: 222 tokens, 1704.781 HB, score 95.024067 (best).
13. Inlined the once-used second helper instance; left the sum coefficient as nsmul for ring1 to handle. Valid: 214 tokens, 1650.954 HB, score 95.189260 (best).
14. Combined sum rewrites and used term-style symmetric sub/add equality. Valid but essentially tied, slightly worse: 212 tokens, 1661.662 HB, score 95.185704. Retain #13.
Stopping: shared weighted-digit invariant plus one summation/coprimality argument is verified in all versions; tested omega, abel, abstraction, and focused rewrite alternatives. Remaining microchanges have negligible expected benefit.
