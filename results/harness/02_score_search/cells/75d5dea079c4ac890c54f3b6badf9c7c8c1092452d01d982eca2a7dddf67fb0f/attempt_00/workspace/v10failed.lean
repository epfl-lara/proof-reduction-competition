theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  simp only [ne_eq, ← Set.disjoint_iff_inter_eq_empty] at hPP hPS
  apply Nat.eq_of_mul_eq_mul_left Nat.two_pos
  rw [mul_pow_sub_one Fintype.card_ne_zero, ← Fintype.card_set,
    ← Set.Intersecting.is_max_iff_card_eq hPP]
  intro Q hQ hPQ
  apply Finset.Subset.antisymm hPQ
  grind only [Set.Intersecting, Finset.subset_iff]
