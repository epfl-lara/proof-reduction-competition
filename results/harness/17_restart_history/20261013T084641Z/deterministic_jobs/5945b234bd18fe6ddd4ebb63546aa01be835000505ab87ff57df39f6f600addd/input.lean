theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let v n : Set.Icc B T := ⟨u n, hB n⟩
  let f n := (v n, v n.succ, v n.succ.succ, v n.succ.succ.succ)
  obtain ⟨i, j, hij, h⟩ := Finite.wellQuasiOrdered Eq f
  obtain ⟨c, hc, rfl⟩ := exists_pos_add_of_lt hij
  have he : ∀ n ≥ i, f (n + c) = f n := Nat.le_induction h.symm (by
      intro n hn ih
      rw [Nat.add_right_comm]
      simp [f, v] at ih ⊢
      simp [ih]
      apply @Int.cast_injective ℝ
      simp only [hu, ge_iff_le, Nat.reduceLeDiff, Nat.reduceSubDiff, ih])
  exact ⟨i, c, hc, fun n hn => congr($(he n hn).1.val)⟩