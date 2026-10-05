theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n)  := by
  obtain ⟨B, T, hB⟩ := boundedu
  let v : ℕ → Set.Icc B T := fun n => ⟨u n, hB n⟩
  let f : ℕ → Set.Icc B T × Set.Icc B T × Set.Icc B T × Set.Icc B T :=
    fun n => (v n, v (n + 1), v (n + 2), v (n + 3))
  obtain ⟨i, j, hij, h⟩ := Set.finite_univ.exists_lt_map_eq_of_forall_mem
    (f := f) (fun _ => Set.mem_univ _)
  have hs : ∀ m, f (i + m) = f (j + m) := by
    intro m
    induction m with
    | zero => exact h
    | succ m ih =>
      simp only [f, Prod.mk.injEq, Subtype.ext_iff, v] at ih ⊢
      refine ⟨ih.2.1, ih.2.2.1, ih.2.2.2, ?_⟩
      change u (i + m + 4) = u (j + m + 4)
      apply Int.cast_injective (α := ℝ)
      rw [(hu (i + m + 4) (by omega)).1, (hu (j + m + 4) (by omega)).1]
      simp only [Nat.reduceSubDiff, ih.1, ih.2.1, ih.2.2.1, ih.2.2.2]
  refine ⟨i, j - i, by omega, ?_⟩
  intro n hn
  have h0 := congrArg (fun t => t.1.val) (hs (n - i))
  change u (i + (n - i)) = u (j + (n - i)) at h0
  simpa only [show i + (n - i) = n by omega,
    show j + (n - i) = n + (j - i) by omega] using h0.symm
