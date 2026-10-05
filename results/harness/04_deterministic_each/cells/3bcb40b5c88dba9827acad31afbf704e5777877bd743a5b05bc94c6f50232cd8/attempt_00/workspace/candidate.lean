theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hc : ∀ A : Set S, Aᶜ ∈ P ↔ A ∉ P := by
    grind
  have he : P.card = Pᶜ.card := by
    apply Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
    <;> simp only [compl_compl, Finset.mem_compl, hc, not_not, implies_true, imp_self]
  have hn := Finset.card_add_card_compl P
  have hp := Fintype.card_pos (α := S)
  have hw : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel hp]
  simp only [Fintype.card_set] at hn
  omega
