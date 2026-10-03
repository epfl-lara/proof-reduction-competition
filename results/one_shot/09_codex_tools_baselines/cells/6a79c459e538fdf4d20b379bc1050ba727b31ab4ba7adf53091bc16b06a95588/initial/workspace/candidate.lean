theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hf : ∀ n, f n ∈ Set.Icc (B, B, B, B) (T, T, T, T) := fun n =>
    ⟨⟨(hB n).1, (hB (n + 1)).1, (hB (n + 2)).1, (hB (n + 3)).1⟩,
     ⟨(hB n).2, (hB (n + 1)).2, (hB (n + 2)).2, (hB (n + 3)).2⟩⟩
  obtain ⟨i, j, hij, heq⟩ :=
    (Set.finite_Icc (B, B, B, B) (T, T, T, T)).exists_lt_map_eq_of_forall_mem hf
  have h : ∀ k : ℕ, f (i + k) = f (j + k) := by
    intro k
    induction k with
    | zero => exact heq
    | succ k ih =>
      simp only [f, Prod.mk.injEq] at ih ⊢
      refine ⟨ih.2.1, ih.2.2.1, ih.2.2.2, ?_⟩
      apply Int.cast_injective (α := ℝ)
      erw [(hu (i + k + 4) (by omega)).1, (hu (j + k + 4) (by omega)).1]
      erw [ih.1, ih.2.1, ih.2.2.1, ih.2.2.2]
      rfl
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  have he : u (j + (n - i)) = u (i + (n - i)) :=
    congrArg Prod.fst (h (n - i)).symm
  simpa only [show j + (n - i) = n + (j - i) by omega,
    show i + (n - i) = n by omega] using he
