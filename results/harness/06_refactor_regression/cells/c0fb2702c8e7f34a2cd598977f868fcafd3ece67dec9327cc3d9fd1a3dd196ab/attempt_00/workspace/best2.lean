theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hi : (P : Set (Set S)).Intersecting := by
    simpa only [Set.Intersecting, Set.disjoint_iff_inter_eq_empty, Finset.mem_coe] using hPP
  have hc := hi.is_max_iff_card_eq.1 (by
    intro Q hQ hPQ
    apply Finset.Subset.antisymm hPQ
    intro A hA
    by_contra hn
    exact hPS ⟨A, hn, fun U hU h =>
      hQ hA (hPQ hU) (Set.disjoint_iff_inter_eq_empty.2 h)⟩)
  rw [Fintype.card_set] at hc
  have hp : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel (Fintype.card_pos : 1 ≤ Fintype.card S)]
  omega
