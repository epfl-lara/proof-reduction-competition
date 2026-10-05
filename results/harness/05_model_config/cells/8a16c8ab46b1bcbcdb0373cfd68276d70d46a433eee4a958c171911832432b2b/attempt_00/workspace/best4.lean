theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hc : P.card = Pᶜ.card := by
    apply Finset.card_bijective compl compl_bijective
    simp only [Finset.mem_compl]
    grind
  have ht := P.card_add_card_compl
  rw [← hc, Fintype.card_set,
    ← Nat.sub_add_cancel (show 1 ≤ Fintype.card S from Fintype.card_pos), pow_succ] at ht
  omega
