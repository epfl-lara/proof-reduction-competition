theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  refine Nat.eq_of_mul_eq_mul_left Nat.two_pos
    (((Set.Intersecting.is_max_iff_card_eq
      (fun A hA B hB => Set.disjoint_iff_inter_eq_empty.not.mpr (hPP A hA B hB))).mp ?_).trans
      (Fintype.card_set.trans (mul_pow_sub_one Fintype.card_ne_zero 2).symm))
  intro Q hQ hPQ
  apply hPQ.antisymm
  intro A hA
  by_contra hn
  exact hPS ⟨A, hn, fun U hU => Set.disjoint_iff_inter_eq_empty.not.mp (hQ hA (hPQ hU))⟩
