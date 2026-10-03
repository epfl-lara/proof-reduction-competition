theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  classical
  obtain ⟨B, T, hB⟩ := boundedu
  let f : ℕ → ℤ × ℤ × ℤ × ℤ := fun n => (u n, u (n+1), u (n+2), u (n+3))
  have hfin : (Set.range f).Finite := by
    apply Set.Finite.subset (Set.finite_Icc (B,B,B,B) (T,T,T,T))
    rintro x ⟨n, rfl⟩
    have h0 := hB n
    have h1 := hB (n+1)
    have h2 := hB (n+2)
    have h3 := hB (n+3)
    simp_all [f, Set.mem_Icc, Prod.le_def]
  have hpair : ∃ i j, i < j ∧ f i = f j := by
    by_contra! h
    have hinj : Function.Injective f := by
      intro i j hij
      by_contra hne
      rcases lt_or_gt_of_ne hne with hlt | hlt
      · exact (h i j hlt hij).elim
      · exact (h j i hlt hij.symm).elim
    exact Set.not_infinite.mpr hfin (Set.infinite_range_of_injective hinj)
  obtain ⟨i, j, hij, heq⟩ := hpair
  have e0 : u i = u j := congrArg Prod.fst heq
  have e1 : u (i+1) = u (j+1) := congrArg Prod.fst (congrArg Prod.snd heq)
  have e2 : u (i+2) = u (j+2) := congrArg Prod.fst (congrArg Prod.snd (congrArg Prod.snd heq))
  have e3 : u (i+3) = u (j+3) := congrArg Prod.snd (congrArg Prod.snd (congrArg Prod.snd heq))
  have hrec (s k : ℕ) :
      (u (s+(k+4)) : ℝ) =
        ((u (s+(k+3)) + u (s+(k+2)) + u (s+(k+1))*u (s+k) : ℝ) /
          (u (s+(k+3))*u (s+(k+2)) + u (s+(k+1)) + u (s+k))) := by
    have h := (hu (s+(k+4)) (by omega)).1
    have h1 : s+(k+4)-1 = s+(k+3) := by omega
    have h2 : s+(k+4)-2 = s+(k+2) := by omega
    have h3 : s+(k+4)-3 = s+(k+1) := by omega
    have h4 : s+(k+4)-4 = s+k := by omega
    simpa only [h1, h2, h3, h4] using h
  have shift : ∀ m, u (i+m) = u (j+m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      cases m with
      | zero => simpa using e0
      | succ m =>
        cases m with
        | zero => simpa using e1
        | succ m =>
          cases m with
          | zero => simpa using e2
          | succ m =>
            cases m with
            | zero => simpa using e3
            | succ k =>
              have q0 : u (i+k) = u (j+k) := ih k (by omega)
              have q1 : u (i+(k+1)) = u (j+(k+1)) := ih (k+1) (by omega)
              have q2 : u (i+(k+2)) = u (j+(k+2)) := ih (k+2) (by omega)
              have q3 : u (i+(k+3)) = u (j+(k+3)) := ih (k+3) (by omega)
              have hcast : (u (i+(k+4)) : ℝ) = (u (j+(k+4)) : ℝ) := by
                rw [hrec i k, hrec j k, q3, q2, q1, q0]
              exact_mod_cast hcast
  refine ⟨i, j-i, by omega, ?_⟩
  intro n hn
  have h := shift (n-i)
  have hi : i+(n-i) = n := by omega
  have hj : j+(n-i) = n+(j-i) := by omega
  rw [hi, hj] at h
  exact h.symm
