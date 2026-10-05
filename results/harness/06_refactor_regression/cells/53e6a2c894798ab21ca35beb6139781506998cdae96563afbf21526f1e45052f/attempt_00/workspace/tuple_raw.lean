theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n)  := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  obtain ⟨i, j, hij, h⟩ := (Set.finite_Icc (B, B, B, B) (T, T, T, T)).exists_lt_map_eq_of_forall_mem
    (f := f) (by
      intro n
      exact ⟨⟨(hB n).1, (hB (n + 1)).1, (hB (n + 2)).1, (hB (n + 3)).1⟩,
        ⟨(hB n).2, (hB (n + 1)).2, (hB (n + 2)).2, (hB (n + 3)).2⟩⟩)
  have hs : ∀ m, f (i + m) = f (j + m) := by
    intro m
    induction m with
    | zero => exact h
    | succ m ih =>
      simp only [f, Prod.mk.injEq] at ih ⊢
      refine ⟨ih.2.1, ih.2.2.1, ih.2.2.2, ?_⟩
      change u (i + m + 4) = u (j + m + 4)
      apply Int.cast_injective (α := ℝ)
      rw [(hu (i + m + 4) (by omega)).1, (hu (j + m + 4) (by omega)).1]
      simp only [Nat.reduceSubDiff, ih.1, ih.2.1, ih.2.2.1, ih.2.2.2]
  refine ⟨i, j - i, by omega, ?_⟩
  intro n hn
  have h0 := congrArg Prod.fst (hs (n - i))
  change u (i + (n - i)) = u (j + (n - i)) at h0
  simpa only [show i + (n - i) = n by omega,
    show j + (n - i) = n + (j - i) by omega] using h0.symm
