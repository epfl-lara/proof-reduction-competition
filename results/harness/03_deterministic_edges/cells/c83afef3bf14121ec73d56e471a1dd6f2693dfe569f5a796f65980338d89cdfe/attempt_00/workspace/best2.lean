theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f (n : ℕ) (k : Fin 4) : ℤ := u (n + k)
  obtain ⟨i, j, hij, heq⟩ :=
    (Set.Finite.pi' (fun _ : Fin 4 => Set.finite_Icc B T)).exists_lt_map_eq_of_forall_mem
      (f := f) (by intro n k; exact hB (n + k))
  have h : ∀ m, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      by_cases hm : m < 4
      · exact congrFun heq ⟨m, hm⟩
      · have hs : ∀ k : ℕ, 0 < k → k ≤ 4 → u (i + m - k) = u (j + m - k) := by
          intro k hk hk4
          simpa only [Nat.add_sub_assoc (by omega : k ≤ m)] using ih (m - k) (by omega)
        apply Int.cast_injective (α := ℝ)
        rw [(hu (i + m) (by omega)).1, (hu (j + m) (by omega)).1,
          hs 1 (by decide) (by decide), hs 2 (by decide) (by decide),
          hs 3 (by decide) (by decide), hs 4 (by decide) (by decide)]
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  have he := h (n - i)
  rw [show i + (n - i) = n by omega, show j + (n - i) = n + (j - i) by omega] at he
  exact he.symm
