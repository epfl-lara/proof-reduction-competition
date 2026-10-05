theorem putnam_1964_a4
(u : ℕ → ℤ)
(boundedu : ∃ B T : ℤ, ∀ n : ℕ, B ≤ u n ∧ u n ≤ T)
(hu : ∀ n ≥ 4, u n = ((u (n - 1) + u (n - 2) + u (n - 3) * u (n - 4)) : ℝ) / (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ∧ (u (n - 1) * u (n - 2) + u (n - 3) + u (n - 4)) ≠ 0)
: (∃ N c : ℕ, c > 0 ∧ ∀ n ≥ N, u (n + c) = u n)  := by
  obtain ⟨B, T, hb⟩ := boundedu
  let f (n : ℕ) (k : Fin 4) : Set.Icc B T := ⟨u (n + k), hb _⟩
  obtain ⟨a, b, hab, he⟩ := Finite.exists_ne_map_eq_of_infinite f
  have collision : ∃ i j, i < j ∧ f i = f j := by
    rcases lt_or_gt_of_ne hab with h | h
    · exact ⟨a, b, h, he⟩
    · exact ⟨b, a, h, he.symm⟩
  obtain ⟨i, j, hij, he⟩ := collision
  have h : ∀ m, u (i + m) = u (j + m) := by
    intro m
    induction m using Nat.strong_induction_on with
    | h m ih =>
      by_cases hm : m < 4
      · exact congrArg Subtype.val (congrFun he ⟨m, hm⟩)
      · have step (k : ℕ) (hk : k ≤ m) (hp : 0 < k) :
            u (i + m - k) = u (j + m - k) := by
          simpa only [Nat.add_sub_assoc hk] using ih (m - k) (by omega)
        apply Int.cast_injective (α := ℝ)
        rw [(hu (i + m) (by omega)).1, (hu (j + m) (by omega)).1,
          step 1 (by omega) (by omega), step 2 (by omega) (by omega),
          step 3 (by omega) (by omega), step 4 (by omega) (by omega)]
  refine ⟨i, j - i, by omega, ?_⟩
  intro n hn
  have he := (h (n - i)).symm
  convert he using 1 <;> congr 1 <;> omega
