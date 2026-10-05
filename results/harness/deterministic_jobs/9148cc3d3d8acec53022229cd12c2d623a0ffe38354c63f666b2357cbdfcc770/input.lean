theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hf (n) : f n ∈ Set.Icc (B, B, B, B) (T, T, T, T) := by
    simp only [mem_Icc, Prod.mk_le_mk, hB, and_self, f]
  obtain ⟨i, j, hij, heq⟩ := (Set.finite_Icc _ _).exists_lt_map_eq_of_forall_mem hf
  let g : ℤ × ℤ × ℤ × ℤ → ℝ := fun (a, b, c, d) =>
    ((d : ℝ) + c + b * a) / (d * c + b + a)
  have hg (n) : (u (n + 4) : ℝ) = g (f n) := (hu _ (by omega)).1
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  have he : f (j - i + n) = f n := by
    induction n, hn using Nat.le_induction with
    | base => simpa only [Nat.sub_add_cancel hij.le] using heq.symm
    | succ n hn ih =>
      have hnew := (hg (j - i + n)).trans ((congrArg g ih).trans (hg n).symm)
      simp only [Prod.mk.injEq, f] at ih ⊢
      exact ⟨ih.2.1, ih.2.2.1, ih.2.2.2, Int.cast_injective hnew⟩
  simpa only [f, Nat.add_comm] using congrArg Prod.fst he