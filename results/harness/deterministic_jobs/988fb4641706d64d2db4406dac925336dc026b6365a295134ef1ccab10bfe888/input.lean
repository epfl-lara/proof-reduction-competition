theorem fold_advances_evaluation_poly
  (i : Fin (ℓ)) (h_i_succ_lt : i + 1 < ℓ + 𝓡)
  (coeffs : Fin (2 ^ (ℓ - ↑i)) → L) (r_chal : L) :
  let P_i : L[X] := intermediateEvaluationPoly 𝔽q β h_ℓ_add_R_rate (i := ⟨i, by
    exact Nat.lt_trans (n := i) (k := ℓ+1) (m := ℓ) (h₁ := i.isLt) (by exact Nat.lt_add_one ℓ)
  ⟩) coeffs
  let f_i := fun (x : (sDomain 𝔽q β h_ℓ_add_R_rate)
      ⟨i, by exact Nat.lt_trans (n := i) (k := r) (m := ℓ) (h₁ := by omega) (by omega)⟩) =>
    P_i.eval (x.val : L)
  let f_i_plus_1 := fold (i := ⟨i, by omega⟩) (h_i := by omega) (f := f_i) (r_chal := r_chal)
  let new_coeffs := fun j : Fin (2^(ℓ - (i + 1))) =>
    (1 - r_chal) * (coeffs ⟨j.val * 2, by
      rw [←Nat.add_zero (j.val * 2)]
      apply mul_two_add_bit_lt_two_pow (c := ℓ - i) (a := j) (b := ℓ - (↑i + 1))
        (i := 0) (by omega) (by omega)
    ⟩) +
    r_chal * (coeffs ⟨j.val * 2 + 1, by
      apply mul_two_add_bit_lt_two_pow (c := ℓ - i) (a := j) (b := ℓ - (↑i + 1))
        (i := 1) (by omega) (by omega)
    ⟩)
  let P_i_plus_1 :=
    intermediateEvaluationPoly 𝔽q β h_ℓ_add_R_rate (i := ⟨i+1, by omega⟩) new_coeffs
  ∀ (y : (sDomain 𝔽q β h_ℓ_add_R_rate)
    ⟨i+1, by omega⟩), f_i_plus_1 y = P_i_plus_1.eval y.val := by
  intro P_i f_i f_i_plus_1 new_coeffs P_i_plus_1 y
  let x := qMap_total_fiber 𝔽q β (i := ⟨i, by omega⟩) (steps := 1)
    (h_i_add_steps := h_i_succ_lt) y
  let P₀ := evenRefinement 𝔽q β h_ℓ_add_R_rate i coeffs
  let P₁ := oddRefinement 𝔽q β h_ℓ_add_R_rate i coeffs
  have hq (k : Fin 2) : (AdditiveNTT.qMap 𝔽q β ⟨i, by omega⟩).eval (x k).val = y.val := by
    have h := generates_quotient_point_if_is_fiber_of_y 𝔽q β i 1 (by omega)
      (x k) y ⟨k, rfl⟩
    rw [iteratedQuotientMap_k_eq_1_is_qMap] at h
    exact congrArg Subtype.val h.symm
  have hd : (x 1).val = 1 + (x 0).val := by
    dsimp only [x]
    rw [qMap_total_fiber_one_level_eq 𝔽q β i (by omega),
      qMap_total_fiber_one_level_eq 𝔽q β i (by omega)]
    simp [Fin2ToF2, get_sDomain_first_basis_eq_1]
  have hs (k : Fin 2) : P_i.eval (x k).val = P₀.eval y.val + (x k).val * P₁.eval y.val := by
    simp only [P_i, evaluation_poly_split_identity 𝔽q β h_ℓ_add_R_rate i coeffs,
      Polynomial.eval_add, Polynomial.eval_mul, Polynomial.eval_X, eval_comp, hq, P₀, P₁]
  change P_i.eval (x 0).val * ((1 - r_chal) * (x 1).val - r_chal) +
    P_i.eval (x 1).val * (r_chal - (1 - r_chal) * (x 0).val) = _
  rw [hs 0, hs 1]
  calc
    _ = (1 - r_chal) * P₀.eval y.val + r_chal * P₁.eval y.val := by rw [hd]; ring
    _ = P_i_plus_1.eval y.val := by
      simp only [P_i_plus_1, new_coeffs, intermediateEvaluationPoly, P₀, P₁,
        evenRefinement, oddRefinement, Nat.sub_add_eq, Polynomial.eval_finset_sum,
        Polynomial.eval_mul, Polynomial.eval_C, mul_sum, ←sum_add_distrib]
      apply Finset.sum_congr rfl
      intro j hj
      ring