# Lean proof optimization notes

- Replaced the fiber-union cardinal argument by an injection from disagreement points into `Y × Fin (2 ^ steps)`, reconstructed with `is_fiber_iff_generates_quotient_point`; valid on all four versions. This removed much elaboration work.
- Replaced arithmetic `gcongr` uses with `Nat.mul_le_mul_left/right`; heartbeat score improved.
- Reused `Code.distFromCode_le_dist_to_mem`, deriving finiteness of the distance directly from the resulting finite upper bound; valid and faster.
- Factored the two subtraction/exponent equalities into one local `hsub`; replacing those equalities with separate `omega` proofs remained valid but scored worse.
- Used `fin_ℓ_steps_lt_ℓ_add_R` and the supplied `h_i_add_steps` explicitly, avoiding some arithmetic search.
- Tried eliminating the closest-witness image setup by unfolding `fiberwiseDistance`; failed due an unresolved `Nonempty` type. Tried final `omega` and explicit `Fin` constructors; failed. Restored the best valid proof after each.
- Latest valid measured score: length reduction 37.59%, heartbeat reduction 53.80%, compatibility 100%, combined 63.80%.
