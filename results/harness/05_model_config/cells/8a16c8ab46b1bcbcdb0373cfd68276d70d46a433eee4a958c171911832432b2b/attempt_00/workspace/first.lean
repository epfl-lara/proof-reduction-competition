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
  rw [← hc, Fintype.card_set] at ht
  have hn := Fintype.card_pos (α := S)
  have hp : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel hn]
  omega
