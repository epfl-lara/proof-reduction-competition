theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n) := by
  obtain ⟨B, T, hB⟩ := boundedu
  classical
  let f n := (u n, u (n+1), u (n+2), u (n+3))
  have hf : (Set.range f).Finite := Set.Finite.subset
    (Set.finite_Icc (B,B,B,B) (T,T,T,T)) (by
      rintro x ⟨n,rfl⟩
      simp [f, hB])
  have hp : ∃ i j : ℕ, i < j ∧ f i = f j := by
    obtain ⟨i,_,j,_,hne,heq⟩ :=
      Set.Infinite.exists_ne_map_eq_of_mapsTo Set.infinite_univ
        (Set.mapsTo_range f Set.univ) hf
    rcases lt_or_gt_of_ne hne with h | h
    · exact ⟨i,j,h,heq⟩
    · exact ⟨j,i,h,heq.symm⟩
  obtain ⟨i,j,hij,hfij⟩ := hp
  have heq : u i = u j ∧ u (i+1) = u (j+1) ∧ u (i+2) = u (j+2) ∧ u (i+3) = u (j+3) := by
    simpa [f] using hfij
  have hs : ∀ m : ℕ, u (i+m) = u (j+m) ∧ u (i+m+1) = u (j+m+1) ∧
      u (i+m+2) = u (j+m+2) ∧ u (i+m+3) = u (j+m+3) := by
    intro m
    induction m with
    | zero => simpa using heq
    | succ m ih =>
      refine ⟨?_, ?_, ?_, ?_⟩
      · simpa [Nat.add_assoc] using ih.2.1
      · simpa [Nat.add_assoc] using ih.2.2.1
      · simpa [Nat.add_assoc] using ih.2.2.2
      · have ri := (hu (i+(m+4)) (by omega)).1
        have rj := (hu (j+(m+4)) (by omega)).1
        simp [Nat.add_sub_assoc] at ri rj
        have hcast : (u (i+m) : ℝ) = u (j+m) ∧
            (u (i+(m+1)) : ℝ) = u (j+(m+1)) ∧
            (u (i+(m+2)) : ℝ) = u (j+(m+2)) ∧
            (u (i+(m+3)) : ℝ) = u (j+(m+3)) := by
          norm_cast
        have hreal : (u (i+(m+4)) : ℝ) = u (j+(m+4)) := by
          rw [ri, rj]
          simp [hcast.1,hcast.2.1,hcast.2.2.1,hcast.2.2.2]
        exact_mod_cast hreal
  refine ⟨i, j-i, by omega, ?_⟩
  intro n hn
  have h := (hs (n-i)).1
  have hi : i+(n-i) = n := by omega
  have hj : j+(n-i) = n+(j-i) := by omega
  rw [hi,hj] at h
  exact h.symm
