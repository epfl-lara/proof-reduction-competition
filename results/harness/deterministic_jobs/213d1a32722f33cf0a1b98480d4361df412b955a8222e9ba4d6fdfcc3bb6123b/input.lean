theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by 
  have h_main : ∃ (i j : ℕ), i < j ∧ (u i = u j ∧ u (i + 1) = u (j + 1) ∧ u (i + 2) = u (j + 2) ∧ u (i + 3) = u (j + 3)) := by
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
          | inl h₈ =>
            
            simp_all only
          | inr h₈ =>
            
            tauto
      have h₆ : Set.Infinite (Set.range f) := Set.infinite_range_of_injective h₅
      exact Set.not_infinite.mpr h₂ h₆
    
    obtain ⟨i, j, h₄, h₅⟩ := h₃
    refine' ⟨i, j, h₄, _⟩
    simp only [Prod.mk.injEq, f] at h₅ ⊢
    <;>
    (try exact h₅)
  
  obtain ⟨i, j, hij, h_eq⟩ := h_main
  have h₁ : ∀ m : ℕ, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      by_cases hm : m < 4
      · have hs : m = 0 ∨ m = 1 ∨ m = 2 ∨ m = 3 := by omega
        rcases hs with hs | hs | hs | hs <;> subst m <;> simp_all
      · obtain ⟨k, hk⟩ : ∃ k, m = k + 4 := ⟨m - 4, by omega⟩
        subst m
        have e0 := ih k (by omega)
        have e1 := ih (k + 1) (by omega)
        have e2 := ih (k + 2) (by omega)
        have e3 := ih (k + 3) (by omega)
        have hi : (u (i + (k + 4)) : ℝ) =
            ((u (i + (k + 3)) + u (i + (k + 2)) + u (i + (k + 1)) * u (i + k)) : ℝ) /
              (u (i + (k + 3)) * u (i + (k + 2)) + u (i + (k + 1)) + u (i + k)) := by
          simpa only [show i + (k + 4) - 1 = i + (k + 3) by omega,
            show i + (k + 4) - 2 = i + (k + 2) by omega,
            show i + (k + 4) - 3 = i + (k + 1) by omega,
            show i + (k + 4) - 4 = i + k by omega] using (hu (i + (k + 4)) (by omega)).1
        have hj : (u (j + (k + 4)) : ℝ) =
            ((u (j + (k + 3)) + u (j + (k + 2)) + u (j + (k + 1)) * u (j + k)) : ℝ) /
              (u (j + (k + 3)) * u (j + (k + 2)) + u (j + (k + 1)) + u (j + k)) := by
          simpa only [show j + (k + 4) - 1 = j + (k + 3) by omega,
            show j + (k + 4) - 2 = j + (k + 2) by omega,
            show j + (k + 4) - 3 = j + (k + 1) by omega,
            show j + (k + 4) - 4 = j + k by omega] using (hu (j + (k + 4)) (by omega)).1
        have r0 : (u (i + k) : ℝ) = u (j + k) := by exact_mod_cast e0
        have r1 : (u (i + (k + 1)) : ℝ) = u (j + (k + 1)) := by exact_mod_cast e1
        have r2 : (u (i + (k + 2)) : ℝ) = u (j + (k + 2)) := by exact_mod_cast e2
        have r3 : (u (i + (k + 3)) : ℝ) = u (j + (k + 3)) := by exact_mod_cast e3
        have hr : (u (i + (k + 4)) : ℝ) = u (j + (k + 4)) := by
          rw [hi, hj, r3, r2, r1, r0]
        exact_mod_cast hr
  use i, (j - i)
  have h₃ : j - i > 0 := by
    omega
  constructor
  · exact h₃
  · intro n hn
    have h₅ : u (i + (n - i)) = u (j + (n - i)) := by
      have h₆ := h₁ (n - i)
      assumption
      <;> omega
    have h₆ : i + (n - i) = n := by
      omega
    have h₇ : j + (n - i) = n + (j - i) := by
      omega
    rw [h₆] at h₅
    rw [h₇] at h₅
    exact id (Eq.symm h₅)