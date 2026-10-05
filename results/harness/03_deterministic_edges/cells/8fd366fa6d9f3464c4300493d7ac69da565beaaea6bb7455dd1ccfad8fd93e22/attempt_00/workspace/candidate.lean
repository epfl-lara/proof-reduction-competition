theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hcomp : ∀ A : Set S, A ∈ P ↔ Aᶜ ∉ P := by
    intro A
    constructor <;> grind
  have hcard : P.card = Pᶜ.card := by
    apply Finset.card_bijective Set.compl compl_involutive.bijective
    intro A
    simpa using hcomp A
  have hsum : P.card + Pᶜ.card = 2 ^ Fintype.card S := by
    rw [Finset.card_add_card_compl, Fintype.card_set]
  have hp : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel Fintype.card_pos]
  omega
