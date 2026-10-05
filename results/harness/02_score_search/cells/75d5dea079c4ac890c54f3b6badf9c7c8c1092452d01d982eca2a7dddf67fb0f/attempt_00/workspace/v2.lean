theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  apply Nat.eq_of_mul_eq_mul_left Nat.two_pos
  rw [mul_pow_sub_one Fintype.card_ne_zero, ← Fintype.card_set]
  refine (Set.Intersecting.is_max_iff_card_eq ?_).mp ?_
  · exact fun A hA B hB h => hPP A hA B hB h.inter_eq
  · intro Q hQ hPQ
    apply Finset.Subset.antisymm hPQ
    intro T hT
    by_contra hn
    exact hPS ⟨T, hn, fun U hU hTU =>
      hQ hT (hPQ hU) (Set.disjoint_iff_inter_eq_empty.mpr hTU)⟩
