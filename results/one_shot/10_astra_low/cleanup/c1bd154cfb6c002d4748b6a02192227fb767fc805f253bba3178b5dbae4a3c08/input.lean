theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hor : ∀ A : Set S, A ∈ P ∨ Aᶜ ∈ P := by grind
  have hnot : ∀ A : Set S, A ∈ P → Aᶜ ∉ P := by
    intro A hA hc
    exact hPP A hA Aᶜ hc (Set.inter_compl_self A)
  let Q := (Finset.univ : Finset (Set S)) \ P
  have heq : P.card = Q.card := by
    have h₂ : ∀ A : Set S, A ∈ P → Aᶜ ∈ Q := by grind
    have h₃ : ∀ A : Set S, A ∈ Q → Aᶜ ∈ P := by grind
    apply Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
    <;> simp_all
  have hsum : P.card + Q.card = 2 ^ Fintype.card S := by
    have : P.card + Q.card = (Finset.univ : Finset (Set S)).card := by grind
    simpa only [Finset.card_univ, Fintype.card_set] using this
  have hpos := Fintype.card_pos (α := S)
  have hpow : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel hpos]
  omega