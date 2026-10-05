theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hb⟩ := boundedu
  let f (n : ℕ) : Fin 4 → Set.Icc B T := fun k => ⟨u (n + k), hb _⟩
  obtain ⟨i, j, hij, he⟩ := Set.finite_univ.exists_lt_map_eq_of_forall_mem
    (f := f) (fun _ => Set.mem_univ _)
  have eqs : ∀ m, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      by_cases hm : m < 4
      · exact congrArg Subtype.val (congrFun he ⟨m, hm⟩)
      · have step (k : ℕ) (hk : 1 ≤ k) (hk' : k ≤ 4) :
            u (i + m - k) = u (j + m - k) := by
          simpa only [Nat.add_sub_assoc (show k ≤ m by omega)] using
            ih (m - k) (by omega)
        apply Int.cast_injective (α := ℝ)
        rw [(hu (i + m) (by omega)).1, (hu (j + m) (by omega)).1,
          step 1 (by decide) (by decide), step 2 (by decide) (by decide),
          step 3 (by decide) (by decide), step 4 (by decide) (by decide)]
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  have h := (eqs (n - i)).symm
  simpa only [Nat.add_sub_of_le hn,
    show j + (n - i) = n + (j - i) by omega] using h