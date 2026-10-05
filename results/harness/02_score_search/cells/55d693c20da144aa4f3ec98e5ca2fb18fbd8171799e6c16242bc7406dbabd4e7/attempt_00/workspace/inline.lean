theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n)  := by
  obtain ⟨B, T, hB⟩ := boundedu
  obtain ⟨i, j, hij, heq⟩ := Set.finite_univ.exists_lt_map_eq_of_forall_mem
    (f := fun n (k : Fin 4) => (⟨u (n + k), hB _⟩ : Set.Icc B T))
    (fun _ => Set.mem_univ _)
  have h (m) : u (i + m) = u (j + m) := by
    induction m using Nat.strong_induction_on with
    | h m ih =>
      by_cases hm : m < 4
      · exact congrArg (fun v => (v ⟨m, hm⟩).val) heq
      · apply Int.cast_injective (α := ℝ)
        simp (disch := omega) only [(hu (i + m) (by omega)).1,
          (hu (j + m) (by omega)).1, Nat.add_sub_assoc, ih]
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  convert (h (n - i)).symm using 1 <;> congr 1 <;> omega
