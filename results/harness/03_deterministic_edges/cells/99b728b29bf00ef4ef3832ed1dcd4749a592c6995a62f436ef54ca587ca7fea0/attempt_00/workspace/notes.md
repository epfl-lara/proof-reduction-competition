Seed score 47.1427 (1366 body tokens; 40.99% heartbeat reduction).
Replaced long calc with Gauss differentiated once, explicit fderiv rules, and four simp_rw rules.
Valid attempt: 499 tokens, 9448.249 heartbeats, score 76.20435.
Failed initial variants: LEInfty does not synthesize for (2+1); use right_eq_inf.mp rfl. Expanding all spatial derivatives before applying the sum rule prevents simplifier matching. Time/space commutation used as simp rule needs explicit (i := j). Conv indexing after applying fun_deriv_sub is awkward because lambda is not yet beta-reduced.

79.3213: 403 tokens, 8813.162 HB. Use fderiv-congrArg of Gauss + unfold Space.div; dsimp does not unfold its partial application. Replacing main simp_rw with simp only also saved 214 HB.

82.8682: 420 tokens, 5607.756 HB. Final field_simp replaced by rewriting ε*μ to μ*ε and simplifying mul inverses/associativity/cancellation. Broad AC simp did not cancel μ and its inverse because ε stayed between them.

Further outcomes: 415/5391 HB (83.2573), then explicit (n:=2),(c:=...) instead of helper type annotations gives 395/5148 (84.0431). Combining post-fderiv simplifications gives 387/4799 (84.6693). Sharing finite regularity hAn and hJd gives 386/4616 (84.91965). Using decide for all finite bounds slightly worse. Merging fderiv rules into final simp fails from early scalar normalization; separate scalar simp is valid but slightly worse (389/4599,84.8673).

Focused conv for sum summands is valid but worse: 390 tokens/4612 HB, 84.8278. Stopping after checking algebra, regularity, derivative-rule sharing, simplification grouping, and focused rewriting alternatives.
