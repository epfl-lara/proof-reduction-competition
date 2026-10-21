-- Warm-up problem: putnam_1964_b2
-- Variant: one_sweep; primary Lean version: v4.25.0
-- Target starts at the TARGET DECLARATION marker below.
-- Source context: benchmark header
-- Proof provenance and scores: ../one_sweep_manifest.json

import Mathlib
import Aesop

-- Match the local evaluator elaboration settings; no heartbeat measurement here.
set_option maxHeartbeats 0
set_option Elab.async false

set_option maxHeartbeats 0

open Set Function Filter Topology



-- TARGET DECLARATION BEGIN: putnam_1964_b2
theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by 
  
  
  have h_subset_or_compl : ∀ (A : Set S), A ∈ P ∨ Aᶜ ∈ P := by grind only [= mem_compl_iff, = mem_empty_iff_false, = mem_inter_iff]
  
  have h_not_both : ∀ (A : Set S), A ∈ P → Aᶜ ∉ P := by
    intro A hA
    by_contra h
    have h₂ : A ∩ Aᶜ = ∅ := by
      ext x
      simp
      
    have h₃ : A ∩ Aᶜ ≠ ∅ := hPP A hA Aᶜ h
    contradiction
  
  classical
  
  let Q : Finset (Set S) := (Finset.univ : Finset (Set S)) \ P
  
  have h₁ : P.card = Q.card := by
    
    have h₂ : ∀ (A : Set S), A ∈ P → Aᶜ ∈ Q := by
      intro A hA
      have h₃ : Aᶜ ∈ (Finset.univ : Finset (Set S)) := Finset.mem_univ _
      have h₄ : Aᶜ ∉ P := h_not_both A hA
      simp only [Finset.mem_sdiff, Q] at *
      tauto
    have h₃ : ∀ (A : Set S), A ∈ Q → Aᶜ ∈ P := by
      intro A hA
      have h₄ : A ∈ (Finset.univ : Finset (Set S)) := by
        simp only [Finset.mem_sdiff, Q] at hA
        tauto
      have h₅ : A ∉ P := by
        simp only [Finset.mem_sdiff, Q] at hA
        tauto
      
      cases (h_subset_or_compl A) <;> grind
    
    have h₆ : ∀ (A : Set S), A ∈ P → Aᶜ ∈ Q := h₂
    have h₇ : ∀ (A : Set S), A ∈ Q → Aᶜ ∈ P := h₃
    
    have h₈ : P.card = Q.card := by
      
      apply Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
      <;> simp_all
      
      
      
      
    exact h₈
  
  have h₂ : P.card + Q.card = 2 ^ Fintype.card S := by
    have h₃ : P.card + Q.card = (Finset.univ : Finset (Set S)).card := by first |
                                                                            grind only [usr Finset.card_union_add_card_inter, = Finset.card_sdiff_of_subset, ← Finset.mem_univ,
                                                                            = Finset.subset_iff, = Finset.card_sdiff, usr Finset.card_ne_zero_of_mem, usr Finset.le_card_sdiff,
                                                                            usr Finset.card_sdiff_add_card_inter, = Finset.card_univ, cases Or]
    have h₄ : (Finset.univ : Finset (Set S)).card = 2 ^ Fintype.card S := by
      simp only [Finset.card_univ, Fintype.card_set]
      
      
      
      
      
    linarith
  
  have h₃ : P.card * 2 = 2 ^ Fintype.card S := by
    have h₄ : P.card + Q.card = 2 ^ Fintype.card S := h₂
    have h₅ : P.card = Q.card := h₁
    linarith
  
  have h₄ : Fintype.card S ≥ 1 := by
    have h₆ : 0 < Fintype.card S := by
      apply Fintype.card_pos_iff.mpr
      exact ⟨Classical.choice inferInstance⟩
    omega
  have h₆ : P.card * 2 = 2 ^ Fintype.card S := h₃
  have h₇ : Fintype.card S ≥ 1 := h₄
  have h₈ : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    have h₉ : Fintype.card S - 1 + 1 = Fintype.card S := by
      have h₁₀ : Fintype.card S ≥ 1 := h₄
      omega
    calc
      2 ^ (Fintype.card S - 1) * 2 = 2 ^ (Fintype.card S - 1) * 2 ^ 1 := by norm_num
      _ = 2 ^ ((Fintype.card S - 1) + 1) := by
        rw [← pow_add]
      _ = 2 ^ Fintype.card S := by
        rw [h₉]
        
  have h₁₀ : P.card * 2 = 2 ^ Fintype.card S := h₃
  
  have h₁₂ : P.card = 2 ^ (Fintype.card S - 1) := by
    nlinarith
  exact h₁₂
-- TARGET DECLARATION END: putnam_1964_b2
