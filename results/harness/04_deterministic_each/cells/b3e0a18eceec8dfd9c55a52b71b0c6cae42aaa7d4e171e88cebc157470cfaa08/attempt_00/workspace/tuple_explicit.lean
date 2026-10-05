theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hf (n) : f n ∈ Set.Icc (B, B, B, B) (T, T, T, T) :=
    ⟨⟨(hB n).1, (hB (n + 1)).1, (hB (n + 2)).1, (hB (n + 3)).1⟩,
     ⟨(hB n).2, (hB (n + 1)).2, (hB (n + 2)).2, (hB (n + 3)).2⟩⟩
  obtain ⟨i, j, hij, heq⟩ := (Set.finite_Icc _ _).exists_lt_map_eq_of_forall_mem hf
  let g : ℤ × ℤ × ℤ × ℤ → ℝ := fun (a, b, c, d) =>
    ((d : ℝ) + c + b * a) / (d * c + b + a)
  have hg (n) : (u (n + 4) : ℝ) = g (f n) := (hu _ (by omega)).1
  have he (m) : f (i + m) = f (j + m) := by
    induction m with
    | zero => exact heq
    | succ m ih =>
      have hnew := (hg (i + m)).trans ((congrArg g ih).trans (hg (j + m)).symm)
      simp only [f, Prod.mk.injEq] at ih ⊢
      exact ⟨ih.2.1, ih.2.2.1, ih.2.2.2, Int.cast_injective hnew⟩
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  have h := congrArg Prod.fst (he (n - i))
  change u (i + (n - i)) = u (j + (n - i)) at h
  simpa only [Nat.add_sub_of_le hn, show j + (n - i) = n + (j - i) by omega] using h.symm
