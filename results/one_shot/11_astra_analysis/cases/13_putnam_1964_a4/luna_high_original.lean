theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  classical
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n+1), u (n+2), u (n+3))
  have hf : Set.Finite (Set.range f) := by
    obtain ⟨B, T, h⟩ := boundedu
    apply (Set.finite_Icc (B,B,B,B) (T,T,T,T)).subset
    rintro x ⟨n, rfl⟩
    exact ⟨⟨(h n).1, (h (n+1)).1, (h (n+2)).1, (h (n+3)).1⟩,
      ⟨(h n).2, (h (n+1)).2, (h (n+2)).2, (h (n+3)).2⟩⟩
  have hp : ∃ i j, i < j ∧ f i = f j := by
    by_contra! h
    apply Set.not_infinite.mpr hf
    apply Set.infinite_range_of_injective
    intro i j e
    rcases lt_trichotomy i j with hij | hij | hij
    · exact False.elim (h i j hij e)
    · exact hij
    · exact False.elim (h j i hij e.symm)
  obtain ⟨i, j, hij, he⟩ := hp
  have he' : u i = u j ∧ u (i+1) = u (j+1) ∧ u (i+2) = u (j+2) ∧ u (i+3) = u (j+3) := by
    simpa only [f, Prod.mk.injEq] using he
  have hall : ∀ m, u (i+m) = u (j+m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      match m with
      | 0 => exact he'.1
      | 1 => exact he'.2.1
      | 2 => exact he'.2.2.1
      | 3 => exact he'.2.2.2
      | m+4 =>
        have hi := (hu (i+(m+4)) (by omega)).1
        have hj := (hu (j+(m+4)) (by omega)).1
        have e1 : u (i+(m+4)-1) = u (j+(m+4)-1) := ih (m+3) (by omega)
        have e2 : u (i+(m+4)-2) = u (j+(m+4)-2) := ih (m+2) (by omega)
        have e3 : u (i+(m+4)-3) = u (j+(m+4)-3) := ih (m+1) (by omega)
        have e4 : u (i+(m+4)-4) = u (j+(m+4)-4) := ih m (by omega)
        rw [e1, e2, e3, e4] at hi
        exact_mod_cast hi.trans hj.symm
  refine ⟨i, j-i, by omega, ?_⟩
  intro n hn
  have h := (hall (n-i)).symm
  have h1 : i+(n-i) = n := by omega
  have h2 : j+(n-i) = n+(j-i) := by omega
  simpa only [h1, h2] using h
