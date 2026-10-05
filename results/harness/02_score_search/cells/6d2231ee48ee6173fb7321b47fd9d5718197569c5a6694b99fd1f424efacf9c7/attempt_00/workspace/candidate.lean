theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  classical
  let f : ℕ → (ℤ × ℤ × ℤ × ℤ) := fun n => (u n, u (n + 1), u (n + 2), u (n + 3))
  have hf : Set.Finite (Set.range f) := by
    have hs : Set.range f ⊆ Set.Icc (B, B, B, B) (T, T, T, T) := by
      intro x hx
      rcases hx with ⟨n, rfl⟩
      simp only [f, Set.mem_Icc, Prod.le_def]
      exact ⟨⟨(hB n).1, (hB (n+1)).1, (hB (n+2)).1, (hB (n+3)).1⟩,
        ⟨(hB n).2, (hB (n+1)).2, (hB (n+2)).2, (hB (n+3)).2⟩⟩
    exact (Set.finite_Icc _ _).subset hs
  obtain ⟨i,j,hij,hij'⟩ : ∃ i j : ℕ, i < j ∧ f i = f j :=
    Set.Finite.exists_lt_map_eq_of_forall_mem (f := f) (t := Set.range f)
      (fun n => ⟨n, rfl⟩) hf
  have heq := hij'
  have hstep : ∀ k l : ℕ, 4 ≤ k → 4 ≤ l →
      u (k-1) = u (l-1) → u (k-2) = u (l-2) → u (k-3) = u (l-3) → u (k-4) = u (l-4) → u k = u l := by
    intro k l hk hl h1 h2 h3 h4
    have hreal : (u k : ℝ) = (u l : ℝ) :=
      (hu k hk).1.trans (by rw [h1, h2, h3, h4]; exact (hu l hl).1.symm)
    exact_mod_cast hreal
  have hshift : ∀ m : ℕ, u (i+m) = u (j+m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      match m with
      | 0 => simpa [f] using congrArg (fun x => x.1) heq
      | 1 => simpa [f] using congrArg (fun x => x.2.1) heq
      | 2 => simpa [f] using congrArg (fun x => x.2.2.1) heq
      | 3 => simpa [f] using congrArg (fun x => x.2.2.2) heq
      | m+4 =>
        have ebefore : ∀ r, 0 < r → r ≤ 4 →
            u (i+(m+4)-r) = u (j+(m+4)-r) := by
          intro r hr hr4
          have q := ih (m+(4-r)) (by omega)
          have a : i+(m+4)-r = i+(m+(4-r)) := by omega
          have b : j+(m+4)-r = j+(m+(4-r)) := by omega
          simpa only [a,b] using q
        have e1 := ebefore 1 (by omega) (by omega)
        have e2 := ebefore 2 (by omega) (by omega)
        have e3 := ebefore 3 (by omega) (by omega)
        have e4 := ebefore 4 (by omega) (by omega)
        exact hstep _ _ (by omega) (by omega) e1 e2 e3 e4
  refine ⟨i,j-i,by omega,?_⟩
  intro n hn
  have h := hshift (n-i)
  have hi : i+(n-i)=n := by omega
  have hj : j+(n-i)=n+(j-i) := by omega
  simpa only [hi,hj] using h.symm
