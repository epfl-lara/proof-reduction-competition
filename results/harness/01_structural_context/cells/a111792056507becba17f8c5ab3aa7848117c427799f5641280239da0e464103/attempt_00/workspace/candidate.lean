theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  classical
  obtain ⟨B, T, hb⟩ := boundedu
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n+1), u (n+2), u (n+3))
  have hf : (Set.range f).Finite := by
    apply (Set.finite_Icc (B,B,B,B) (T,T,T,T)).subset
    rintro x ⟨n, rfl⟩
    exact ⟨⟨(hb n).1, (hb (n+1)).1, (hb (n+2)).1, (hb (n+3)).1⟩,
      ⟨(hb n).2, (hb (n+1)).2, (hb (n+2)).2, (hb (n+3)).2⟩⟩
  have he : ∃ i j, i < j ∧ f i = f j := by
    by_contra! h
    apply (Set.infinite_range_of_injective (f := f) ?_) hf
    intro i j e
    rcases lt_trichotomy i j with hij | hij | hij
    · exact False.elim (h i j hij e)
    · exact hij
    · exact False.elim (h j i hij e.symm)
  obtain ⟨i, j, hij, he⟩ := he
  have heq : u i = u j ∧ u (i+1) = u (j+1) ∧ u (i+2) = u (j+2) ∧ u (i+3) = u (j+3) := by
    simpa only [f, Prod.mk.injEq] using he
  have hp : ∀ m, u (i+m) = u (j+m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      by_cases hm : m < 4
      · interval_cases m <;> simp_all only [Nat.add_zero]
      · have hm : 4 ≤ m := by omega
        have hs (k : ℕ) (hk : 1 ≤ k) (hk' : k ≤ 4) :
            u (i+m-k) = u (j+m-k) := by
          rw [Nat.add_sub_assoc (by omega : k ≤ m), Nat.add_sub_assoc (by omega : k ≤ m)]
          exact ih (m-k) (by omega)
        apply Int.cast_injective (α := ℝ)
        rw [(hu (i+m) (by omega)).1, (hu (j+m) (by omega)).1,
          hs 1 (by decide) (by decide), hs 2 (by decide) (by decide),
          hs 3 (by decide) (by decide), hs 4 (by decide) (by decide)]
  refine ⟨i, j-i, by omega, ?_⟩
  intro n hn
  have h := (hp (n-i)).symm
  simpa only [show i+(n-i) = n by omega,
    show j+(n-i) = n+(j-i) by omega] using h
