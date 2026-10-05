theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hb⟩ := boundedu
  let f := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hs := Set.finite_Icc B T
  obtain ⟨i, j, hij, he⟩ := (hs.prod (hs.prod (hs.prod hs))).exists_lt_map_eq_of_forall_mem
    (f := f) (by intro n; exact ⟨hb n, hb (n+1), hb (n+2), hb (n+3)⟩)
  have h : ∀ m, f (i + m) = f (j + m) := by
    intro m
    induction m with
    | zero => exact he
    | succ m ih =>
      simp only [f, Prod.mk.injEq] at ih
      rcases ih with ⟨h0, h1, h2, h3⟩
      refine Prod.ext h1 (Prod.ext h2 (Prod.ext h3 ?_))
      change u (i+m+4) = u (j+m+4)
      apply Int.cast_injective (α := ℝ)
      rw [(hu (i+m+4) (Nat.le_add_left 4 _)).1, (hu (j+m+4) (Nat.le_add_left 4 _)).1]
      simp only [Nat.add_sub_assoc, Nat.reduceLeDiff, Nat.reduceSubDiff, Nat.add_zero, h0, h1, h2, h3]
  refine ⟨i, j-i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  simpa only [f, Nat.add_sub_of_le hn, show j+(n-i) = n+(j-i) by omega] using
    (congrArg Prod.fst (h (n-i))).symm