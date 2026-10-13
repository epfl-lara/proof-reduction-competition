theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hb⟩ := boundedu
  obtain ⟨i, j, hij, h⟩ :=
    (Set.Finite.pi' (fun _ => Set.finite_Icc B T)).exists_lt_map_eq_of_forall_mem
      (f := fun n => fun k : Fin 4 => u (n + k))
      (by
        repeat intro
        apply hb)
  have hs m : u (i + m) = u (j + m) := by
    clear hij
    induction m using Nat.strong_induction_on
    rename_i m ih
    by_cases hm : 4 ≤ m
    · apply @Int.cast_injective ℝ
      simp (disch := omega) only [hu, Nat.add_sub_assoc, ih]
    · exact congrFun h ⟨m, lt_of_not_ge hm⟩
  use i, j - i, Nat.sub_pos_of_lt hij
  intro n hn
  rw [← Nat.add_sub_of_le hn, Nat.add_right_comm, Nat.add_sub_of_le hij.le, hs]