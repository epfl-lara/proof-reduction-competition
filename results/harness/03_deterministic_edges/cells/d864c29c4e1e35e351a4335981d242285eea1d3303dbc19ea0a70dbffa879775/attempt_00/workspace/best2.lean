theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have h : ∀ A : Set S, Aᶜ ∈ P ↔ A ∉ P := by
    intro A
    constructor
    · intro hc ha
      exact hPP A ha Aᶜ hc (Set.inter_compl_self A)
    · grind
  have hc : P.card = Pᶜ.card := by
    apply Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
    <;> simp only [Finset.mem_compl, ← h, compl_compl, implies_true, imp_self, forall_const]
  have hn := P.card_add_card_compl
  rw [← hc, Fintype.card_set] at hn
  have hp := Fintype.card_pos (α := S)
  have he : 2 ^ Fintype.card S = 2 ^ (Fintype.card S - 1) * 2 := by
    rw [← pow_succ]
    congr 1
    omega
  omega
