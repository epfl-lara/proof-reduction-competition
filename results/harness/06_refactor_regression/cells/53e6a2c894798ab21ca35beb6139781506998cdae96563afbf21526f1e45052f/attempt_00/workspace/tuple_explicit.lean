theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n)  := by
  obtain ⟨B, T, hB⟩ := boundedu
  let v : ℕ → Set.Icc B T := fun n => ⟨u n, hB n⟩
  let f := fun n : ℕ => (v n, v (n + 1), v (n + 2), v (n + 3))
  obtain ⟨i, j, hij, h⟩ := Set.finite_univ.exists_lt_map_eq_of_forall_mem
    (f := f) (fun _ => Set.mem_univ _)
  obtain ⟨c, rfl⟩ := Nat.exists_eq_add_of_le hij.le
  have hs : ∀ n ≥ i, f (n + c) = f n := by
    intro n hn
    induction n, hn using Nat.le_induction with
    | base => exact h.symm
    | succ n hn ih =>
      rw [Nat.add_right_comm n 1 c]
      simp only [f, Prod.mk.injEq, Subtype.ext_iff, v] at ih ⊢
      refine ⟨ih.2.1, ih.2.2.1, ih.2.2.2, ?_⟩
      change u (n + c + 4) = u (n + 4)
      apply Int.cast_injective (α := ℝ)
      rw [(hu (n + c + 4) (Nat.le_add_left ..)).1, (hu (n + 4) (Nat.le_add_left ..)).1]
      simp only [Nat.reduceSubDiff, ih.1, ih.2.1, ih.2.2.1, ih.2.2.2]
  exact ⟨i, c, Nat.pos_of_lt_add_right hij, fun n hn => congrArg (fun t => t.1.val) (hs n hn)⟩
