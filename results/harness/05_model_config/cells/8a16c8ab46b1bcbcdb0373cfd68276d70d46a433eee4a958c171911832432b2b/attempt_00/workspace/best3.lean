theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have h : ∀ A : Set S, A ∈ P ↔ Aᶜ ∉ P := by
    grind
  have hc : P.card = Pᶜ.card :=
    Finset.card_bijective compl compl_bijective (by simpa using h)
  have ht := P.card_add_card_compl
  rw [← hc, Fintype.card_set,
    ← Nat.sub_add_cancel (show 1 ≤ Fintype.card S from Fintype.card_pos), pow_succ] at ht
  omega
