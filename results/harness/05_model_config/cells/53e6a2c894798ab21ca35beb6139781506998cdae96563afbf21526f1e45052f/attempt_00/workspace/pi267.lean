theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f (n : ℕ) (k : Fin 4) := u (n + k)
  obtain ⟨i, j, hij, he⟩ :=
    (Set.finite_Icc (fun _ : Fin 4 => B) (fun _ => T)).exists_lt_map_eq_of_forall_mem
      (f := f) (by
        intro n
        exact ⟨fun k => (hB _).1, fun k => (hB _).2⟩)
  have eqs (m : ℕ) : f (i + m) = f (j + m) := by
    induction m with
    | zero => exact he
    | succ m ih =>
      funext k
      fin_cases k
      · exact congrFun ih 1
      · exact congrFun ih 2
      · exact congrFun ih 3
      · have e := (hu (i + m + 4) (by omega)).1
        have e' := (hu (j + m + 4) (by omega)).1
        simp only [f, funext_iff, Fin.forall_iff] at ih
        norm_num only [Nat.add_sub_assoc, ih] at e e'
        exact Int.cast_injective (e.trans e'.symm)
  refine ⟨i, j - i, by omega, ?_⟩
  intro n hn
  obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hn
  simpa only [f, show i + m + (j - i) = j + m by omega] using
    (congrFun (eqs m) 0).symm
