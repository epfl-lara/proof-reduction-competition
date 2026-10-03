theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  classical
  obtain ⟨B, T, hB⟩ := boundedu
  let f : ℕ → (ℤ × ℤ × ℤ × ℤ) := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hfin : (Set.range f).Finite := by
    refine Set.Finite.subset (Set.finite_Icc (B, B, B, B) (T, T, T, T)) ?_
    rintro x ⟨n, rfl⟩
    exact ⟨⟨(hB n).1, (hB (n+1)).1, (hB (n+2)).1, (hB (n+3)).1⟩,
           ⟨(hB n).2, (hB (n+1)).2, (hB (n+2)).2, (hB (n+3)).2⟩⟩
  obtain ⟨i, j, hij, hfij⟩ := hfin.exists_lt_map_eq_of_forall_mem (fun n => Set.mem_range_self n)
  have h_eq : u i = u j ∧ u (i + 1) = u (j + 1) ∧ u (i + 2) = u (j + 2) ∧ u (i + 3) = u (j + 3) := by
    simpa [f] using hfij
  have h_per : ∀ m, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      match m with
      | 0 => exact h_eq.1
      | 1 => exact h_eq.2.1
      | 2 => exact h_eq.2.2.1
      | 3 => exact h_eq.2.2.2
      | m + 4 =>
        have hi := (hu (i + (m + 4)) (by omega)).1
        have hj := (hu (j + (m + 4)) (by omega)).1
        have h1 : i + (m + 4) - 1 = i + (m + 3) := by rfl
        have h2 : i + (m + 4) - 2 = i + (m + 2) := by rfl
        have h3 : i + (m + 4) - 3 = i + (m + 1) := by rfl
        have h4 : i + (m + 4) - 4 = i + m := by exact rfl
        have h5 : j + (m + 4) - 1 = j + (m + 3) := by exact rfl
        have h6 : j + (m + 4) - 2 = j + (m + 2) := by exact rfl
        have h7 : j + (m + 4) - 3 = j + (m + 1) := by omega
        have h8 : j + (m + 4) - 4 = j + m := by omega
        have hm := ih m (by omega)
        have hm1 := ih (m + 1) (by omega)
        have hm2 := ih (m + 2) (by omega)
        have hm3 := ih (m + 3) (by omega)
        have hreal : (u (i + (m + 4)) : ℝ) = (u (j + (m + 4)) : ℝ) := by
          rw [hi, hj, h1, h2, h3, h4, h5, h6, h7, h8, hm, hm1, hm2, hm3]
        exact_mod_cast hreal
  use i, (j - i)
  have hpos : j - i > 0 := by omega
  refine ⟨hpos, ?_⟩
  intro n hn
  have h5 : u (i + (n - i)) = u (j + (n - i)) := h_per (n - i)
  have h6 : i + (n - i) = n := by omega
  have h7 : j + (n - i) = n + (j - i) := by omega
  rw [h6, h7] at h5
  exact h5.symm