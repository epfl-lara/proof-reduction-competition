theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hI : (P : Set (Set S)).Intersecting := by
    intro A hA B hB h
    exact hPP A hA B hB (Set.disjoint_iff_inter_eq_empty.mp h)
  have hC := hI.is_max_iff_card_eq.mp (by
    intro Q hQ hPQ
    apply Finset.Subset.antisymm hPQ
    intro A hA
    by_contra hn
    exact hPS ⟨A, hn, fun U hU he =>
      hQ hA (hPQ hU) (Set.disjoint_iff_inter_eq_empty.mpr he)⟩)
  rw [Fintype.card_set] at hC
  have hp := mul_pow_sub_one (Fintype.card_ne_zero (α := S)) (2 : ℕ)
  omega
