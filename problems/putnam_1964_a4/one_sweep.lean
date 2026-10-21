-- Warm-up problem: putnam_1964_a4
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

open Set Function



-- TARGET DECLARATION BEGIN: putnam_1964_a4
theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by 
  have h_main : ∃ (i j : ℕ), i < j ∧ (u i = u j ∧ u (i + 1) = u (j + 1) ∧ u (i + 2) = u (j + 2) ∧ u (i + 3) = u (j + 3)) := by
    obtain ⟨B, T, hB⟩ := boundedu
    classical
    
    let f : ℕ → (ℤ × ℤ × ℤ × ℤ) := fun n => (u n, u $ n + 1, u $ n + 2, u $ n + 3)
    have h₂ : Set.Finite (Set.range f) := by
      have h₃ : Set.range f ⊆ Set.Icc (B, B, B, B) (T, T, T, T) := by
        rintro x ⟨n, rfl⟩
        have h₄ := hB n
        have h₅ := hB $ n + 1
        have h₆ := hB $ n + 2
        have h₇ := hB $ n + 3
        constructor <;>
        (try constructor) <;>
        (try constructor) <;>
        (try constructor) <;>
        (try simp_all only [ and_self, f]) 
      
      have h₄ : Set.Finite (Set.Icc (B, B, B, B) (T, T, T, T)) := by
        apply Set.Finite.subset $ Set.finite_mem_finset (Finset.Icc (B, B, B, B) (T, T, T, T))
        intro x hx
        simp_all only [ge_iff_le, ne_eq, mem_Icc, Finset.mem_Icc, mem_setOf_eq, and_self]
        
      exact Set.Finite.subset h₄ h₃
    
    have h₃ : ∃ (i j : ℕ), i < j ∧ f i = f j := by
      by_contra! h₄
      have h₅ : Function.Injective f := by
        intro i j h₆
        by_cases h₇ : i = j
        · exact h₇
        · have h₈ : i < j ∨ j < i := by omega
          cases h₈ with
          | inl h₈ =>
            have h₉ := h₄ i j h₈
            simp_all only []
          | inr h₈ =>
            have h₉ := h₄ j i h₈
            simp_all only [ge_iff_le, ne_eq, not_true_eq_false]
      exact Set.not_infinite.mpr h₂ $ Set.infinite_range_of_injective h₅
    
    obtain ⟨i, j, h₄, h₅⟩ := h₃
    refine' ⟨i, j, h₄, _⟩
    simp only [Prod.mk.injEq, f] at h₅ ⊢
    <;>
    (try simp_all only [ge_iff_le, and_self])  
  
  obtain ⟨i, j, hij, h_eq⟩ := h_main
  have h₁ : ∀ m : ℕ, u (i + m) = u (j + m) := by
    intro m
    have h₂ : ∀ m : ℕ, u (i + m) = u (j + m) := by
      intro m
      induction m using Nat.strong_induction_on with
      | h m ih =>
        match m with
        | 0 =>
          have h₃ := h_eq.1
          simp at h₃ ⊢
          <;> exact h₃
        | 1 =>
          have h₃ := h_eq.2.1
          simp only at h₃ ⊢
          <;> exact h₃
          
          
        | 2 =>
          have h₃ := h_eq.2.2.1
          simp only at h₃ ⊢
          <;> exact h₃
          
          
        | 3 =>
          have h₃ := h_eq.2.2.2
          simp only at h₃ ⊢
          <;> omega
          
          
        | m + 4 =>
          
          
          
          have h₆ : (i + (m + 4) - 1 : ℕ) = i + (m + 3) := by
            omega
          have h₇ : (i + (m + 4) - 2 : ℕ) = i + (m + 2) := by
            omega
          have h₈ : (i + (m + 4) - 3 : ℕ) = i + (m + 1) := by
            omega
          have h₉ : (i + (m + 4) - 4 : ℕ) = i + m := by
            omega
          have h₁₀ : (j + (m + 4) - 1 : ℕ) = j + (m + 3) := by
            omega
          have h₁₁ : (j + (m + 4) - 2 : ℕ) = j + (m + 2) := by
            omega
          have h₁₂ : (j + (m + 4) - 3 : ℕ) = j + (m + 1) := by
            omega
          have h₁₃ : (j + (m + 4) - 4 : ℕ) = j + m := by
            omega
          have h₁₄ : u (i + (m + 3)) = u (j + (m + 3)) := by
            have h₁₅ := ih (m + 3) $ by omega
            simp only at h₁₅ ⊢
            <;> omega
          have h₁₅ : u (i + (m + 2)) = u (j + (m + 2)) := by
            have h₁₆ := ih (m + 2) $ by omega
            simp only at h₁₆ ⊢
            <;> omega
          have h₁₆ : u (i + (m + 1)) = u (j + (m + 1)) := by
            have h₁₇ := ih (m + 1) $ by omega
            simp only at h₁₇ ⊢
            <;> omega
          have h₁₇ : u (i + m) = u (j + m) := by
            have h₁₈ := ih m $ by omega
            simp only at h₁₈ ⊢
            <;> omega
          have h₁₈ : (u (i + (m + 4)) : ℝ) = (u (j + (m + 4)) : ℝ) := by grind
          norm_cast at h₁₈ ⊢
           
    exact h₂ m
  use i, j - i
  have h₃ : j - i > 0 := by
    omega
  constructor
  · exact h₃
  · intro n hn
    have h₅ : u (i + (n - i)) = u (j + (n - i)) := by
      have h₆ := h₁ $ n - i
      simp only at h₆ ⊢
      <;> omega
    have h₆ : i + (n - i) = n := by
      omega
    have h₇ : j + (n - i) = n + (j - i) := by
      omega
    rw [h₆, h₇] at h₅
    linarith
-- TARGET DECLARATION END: putnam_1964_a4
