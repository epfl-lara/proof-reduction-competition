theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  obtain ⟨i, j, hij, he⟩ :=
    (Set.finite_Icc (B, B, B, B) (T, T, T, T)).exists_lt_map_eq_of_forall_mem
      (f := f) (by
        intro n
        exact ⟨⟨(hB _).1, (hB _).1, (hB _).1, (hB _).1⟩,
        ⟨(hB _).2, (hB _).2, (hB _).2, (hB _).2⟩⟩)
  have step (a b : ℕ) (h : f a = f b) : f (a + 1) = f (b + 1) := by
    simp only [f, Prod.mk.injEq] at h ⊢
    rcases h with ⟨h0, h1, h2, h3⟩
    refine ⟨h1, h2, h3, ?_⟩
    have e := (hu (a + 4) (by omega)).1
    have e' := (hu (b + 4) (by omega)).1
    norm_num only [Nat.add_sub_assoc, Nat.add_zero] at e e'
    rw [h0, h1, h2, h3] at e
    exact Int.cast_injective (e.trans e'.symm)
  have eqs (m : ℕ) : f (i + m) = f (j + m) := by
    induction m with
    | zero => exact he
    | succ m ih => exact step (i + m) (j + m) ih
  refine ⟨i, j - i, by omega, ?_⟩
  intro n hn
  obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hn
  simpa only [f, show i + m + (j - i) = j + m by omega] using
    (congrArg Prod.fst (eqs m)).symm
