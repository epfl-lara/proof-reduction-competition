theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let f n (k : Fin 4) := u (n + k)
  obtain ⟨i, j, hij, he⟩ :=
    (Set.finite_Icc (fun _ : Fin 4 => B) (fun _ => T)).exists_lt_map_eq_of_forall_mem
      (f := f) (fun n => forall_and.mp (fun k : Fin 4 => hB (n + k)))
  have eqs : ∀ m, f (i + m) = f (j + m) := Nat.rec he (fun m ih => by
      funext k
      fin_cases k
      · exact congrFun ih 1
      · exact congrFun ih 2
      · exact congrFun ih 3
      · have e := (hu (i + m + 4) (Nat.le_add_left ..)).1
        have e' := (hu (j + m + 4) (Nat.le_add_left ..)).1
        simp only [f, funext_iff, Fin.forall_iff] at ih
        simp only [Nat.add_sub_assoc, Nat.reduceSub, Nat.reduceLeDiff, Nat.reduceLT, ih] at e e'
        exact Int.cast_injective (e.trans e'.symm))
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hn
  simpa only [f, Nat.add_right_comm i m (j - i), Nat.add_sub_of_le hij.le] using
    (congrFun (eqs m) 0).symm
