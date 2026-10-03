theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  classical
  let f : ℕ → (ℤ × ℤ × ℤ × ℤ) := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have h₂ : Set.Finite (Set.range f) := by
    have h₃ : Set.range f ⊆ Set.Icc (B, B, B, B) (T, T, T, T) := by
      intro x hx
      rcases hx with ⟨n, rfl⟩
      have h₄ := hB n
      have h₅ := hB (n + 1)
      have h₆ := hB (n + 2)
      have h₇ := hB (n + 3)
      simp only at h₄ h₅ h₆ h₇ ⊢
      constructor <;>
      (try constructor) <;>
      (try constructor) <;>
      (try constructor) <;>
      (try simp_all only [and_self, f])
    
    have h₄ : Set.Finite (Set.Icc (B, B, B, B) (T, T, T, T)) := by
      apply Set.Finite.subset (Set.finite_mem_finset (Finset.Icc (B, B, B, B) (T, T, T, T)))
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
        | inl h₈ => exact (h₄ i j h₈ h₆).elim
        | inr h₈ => exact (h₄ j i h₈ (h₆.symm)).elim
    exact Set.not_infinite.mpr h₂ (Set.infinite_range_of_injective h₅)
  obtain ⟨i, j, hij, h_eq⟩ := h₃
  simp only [Prod.mk.injEq, f] at h_eq
  have h₁ : ∀ m : ℕ, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      match m with
      | 0 => exact h_eq.1
      | 1 => exact h_eq.2.1
      | 2 => exact h_eq.2.2.1
      | 3 => exact h_eq.2.2.2
      | m + 4 =>
        have h₄ := hu (i + (m + 4)) (by omega)
        have h₅ := hu (j + (m + 4)) (by omega)
        have h₆ : (i + (m + 4) - 1 : ℕ) = i + (m + 3) := by omega
        have h₇ : (i + (m + 4) - 2 : ℕ) = i + (m + 2) := by omega
        have h₈ : (i + (m + 4) - 3 : ℕ) = i + (m + 1) := by omega
        have h₉ : (i + (m + 4) - 4 : ℕ) = i + m := by omega
        have h₁₀ : (j + (m + 4) - 1 : ℕ) = j + (m + 3) := by omega
        have h₁₁ : (j + (m + 4) - 2 : ℕ) = j + (m + 2) := by omega
        have h₁₂ : (j + (m + 4) - 3 : ℕ) = j + (m + 1) := by omega
        have h₁₃ : (j + (m + 4) - 4 : ℕ) = j + m := by omega
        have h₁₄ : (u (i + (m + 4)) : ℝ) = ((u (i + (m + 3)) + u (i + (m + 2)) + u (i + (m + 1)) * u (i + m)) : ℝ) / (u (i + (m + 3)) * u (i + (m + 2)) + u (i + (m + 1)) + u (i + m)) := by
          rw [h₄.1, h₆, h₇, h₈, h₉]
        have h₁₅ : (u (j + (m + 4)) : ℝ) = ((u (j + (m + 3)) + u (j + (m + 2)) + u (j + (m + 1)) * u (j + m)) : ℝ) / (u (j + (m + 3)) * u (j + (m + 2)) + u (j + (m + 1)) + u (j + m)) := by
          rw [h₅.1, h₁₀, h₁₁, h₁₂, h₁₃]
        have h₁₆ : (u (i + (m + 4)) : ℝ) = (u (j + (m + 4)) : ℝ) := by
          rw [h₁₄, h₁₅]
          congr 1 <;> congr 1 <;>
            (try rw [ih (m + 3) (by omega)]) <;>
            (try rw [ih (m + 2) (by omega)]) <;>
            (try rw [ih (m + 1) (by omega)]) <;>
            (try rw [ih m (by omega)])
        norm_cast at h₁₆ ⊢
  use i, (j - i)
  constructor
  · omega
  · intro n hn
    have h₅ : u (i + (n - i)) = u (j + (n - i)) := h₁ (n - i)
    have h₆ : i + (n - i) = n := by omega
    have h₇ : j + (n - i) = n + (j - i) := by omega
    rw [h₆, h₇] at h₅
    exact h₅.symm