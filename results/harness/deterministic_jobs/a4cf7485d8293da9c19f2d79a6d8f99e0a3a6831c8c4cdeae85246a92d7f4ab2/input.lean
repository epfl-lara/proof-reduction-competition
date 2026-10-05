theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  let v n : Set.Icc B T := ⟨u n, hB n⟩
  let f := fun n => (v n, v (n + 1), v (n + 2), v (n + 3))
  obtain ⟨i, j, hij, heq⟩ := Set.finite_univ.exists_lt_map_eq_of_forall_mem
    (f := f) (fun _ => Set.mem_univ _)
  refine ⟨i, j - i, Nat.sub_pos_of_lt hij, ?_⟩
  intro n hn
  have he : f (j - i + n) = f n := by
    induction n, hn using Nat.le_induction with
    | base => simpa only [Nat.sub_add_cancel hij.le] using heq.symm
    | succ n hn ih =>
      have hnew := (hu (j - i + n + 4) (Nat.le_add_left _ _)).1.trans
        ((congrArg (fun (a, b, c, d) =>
          ((d : ℝ) + c + b * a) / (d * c + b + a)) ih).trans
            (hu (n + 4) (Nat.le_add_left _ _)).1.symm)
      simp only [Prod.mk.injEq, f] at ih ⊢
      exact ⟨ih.2.1, ih.2.2.1, ih.2.2.2, Subtype.ext (Int.cast_injective hnew)⟩
  simpa only [Nat.add_comm] using congrArg (Subtype.val ∘ Prod.fst) he