theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hfin : (Set.Icc (B, B, B, B) (T, T, T, T)).Finite := Set.finite_Icc _ _
  have hf : ∀ n, f n ∈ Set.Icc (B, B, B, B) (T, T, T, T) := by
    intro n
    simp only [Set.mem_Icc, Prod.le_def]
    exact ⟨⟨(hB n).1, (hB (n + 1)).1, (hB (n + 2)).1, (hB (n + 3)).1⟩,
           ⟨(hB n).2, (hB (n + 1)).2, (hB (n + 2)).2, (hB (n + 3)).2⟩⟩
  obtain ⟨i, j, hij, h_eq⟩ := Set.Finite.exists_lt_map_eq_of_forall_mem hf hfin
  have h_eq' : u i = u j ∧ u (i + 1) = u (j + 1) ∧ u (i + 2) = u (j + 2) ∧ u (i + 3) = u (j + 3) := by
    simpa [f, Prod.mk.injEq] using h_eq
  have h_period : ∀ m, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      match m with
      | 0 => exact h_eq'.1
      | 1 => exact h_eq'.2.1
      | 2 => exact h_eq'.2.2.1
      | 3 => exact h_eq'.2.2.2
      | m + 4 =>
        have h_i := (hu (i + (m + 4)) (by omega)).1
        have h_j := (hu (j + (m + 4)) (by omega)).1
        have h1 : i + (m + 4) - 1 = i + (m + 3) := by omega
        have h2 : i + (m + 4) - 2 = i + (m + 2) := by omega
        have h3 : i + (m + 4) - 3 = i + (m + 1) := by omega
        have h4 : i + (m + 4) - 4 = i + m := by omega
        have h5 : j + (m + 4) - 1 = j + (m + 3) := by omega
        have h6 : j + (m + 4) - 2 = j + (m + 2) := by omega
        have h7 : j + (m + 4) - 3 = j + (m + 1) := by omega
        have h8 : j + (m + 4) - 4 = j + m := by omega
        rw [h1, h2, h3, h4] at h_i
        rw [h5, h6, h7, h8] at h_j
        have ih0 := ih m (by omega)
        have ih1 := ih (m + 1) (by omega)
        have ih2 := ih (m + 2) (by omega)
        have ih3 := ih (m + 3) (by omega)
        rw [← ih0, ← ih1, ← ih2, ← ih3] at h_j
        have h_real : (u (i + (m + 4)) : ℝ) = (u (j + (m + 4)) : ℝ) := by
          rw [h_i, h_j]
        exact_mod_cast h_real
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  have h1 : u (i + (n - i)) = u (j + (n - i)) := h_period (n - i)
  have h2 : i + (n - i) = n := by omega
  have h3 : j + (n - i) = n + (j - i) := by omega
  rw [h2, h3] at h1
  exact h1.symm