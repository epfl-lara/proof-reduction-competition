theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  classical
  obtain ⟨B, T, hb⟩ := boundedu
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hf : Set.Finite (Set.range f) := by
    apply (Set.finite_Icc (B, B, B, B) (T, T, T, T)).subset
    rintro x ⟨n, rfl⟩
    exact ⟨⟨(hb n).1, (hb (n+1)).1, (hb (n+2)).1, (hb (n+3)).1⟩,
      ⟨(hb n).2, (hb (n+1)).2, (hb (n+2)).2, (hb (n+3)).2⟩⟩
  have hc : ∃ i j, i < j ∧ f i = f j := by
    by_contra! h
    have hi : Function.Injective f := by
      intro i j he
      rcases lt_trichotomy i j with hij | hij | hij
      · exact False.elim (h i j hij he)
      · exact hij
      · exact False.elim (h j i hij he.symm)
    exact Set.not_infinite.mpr hf (Set.infinite_range_of_injective hi)
  obtain ⟨i, j, hij, he⟩ := hc
  have heq : u i = u j ∧ u (i+1) = u (j+1) ∧ u (i+2) = u (j+2) ∧ u (i+3) = u (j+3) := by
    simpa only [f, Prod.mk.injEq] using he
  have hall : ∀ m, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      by_cases hm : m < 4
      · interval_cases m
        · simpa only [Nat.add_zero] using heq.1
        · exact heq.2.1
        · exact heq.2.2.1
        · exact heq.2.2.2
      · have hp : ∀ k, 0 < k → k ≤ 4 → u (i+m-k) = u (j+m-k) := by
          intro k hk hk4
          have h := ih (m-k) (by omega)
          simpa only [Nat.add_sub_assoc (show k ≤ m by omega)] using h
        have hr : (u (i+m) : ℝ) = (u (j+m) : ℝ) := by
          rw [(hu (i+m) (by omega)).1, (hu (j+m) (by omega)).1,
            hp 1 (by omega) (by omega), hp 2 (by omega) (by omega),
            hp 3 (by omega) (by omega), hp 4 (by omega) (by omega)]
        exact_mod_cast hr
  refine ⟨i, j-i, by omega, ?_⟩
  intro n hn
  have h := (hall (n-i)).symm
  simpa only [show i + (n-i) = n by omega,
    show j + (n-i) = n + (j-i) by omega] using h
