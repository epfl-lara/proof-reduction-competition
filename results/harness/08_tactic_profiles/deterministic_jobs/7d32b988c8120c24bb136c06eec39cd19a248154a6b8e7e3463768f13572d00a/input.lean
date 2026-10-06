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
  intro P f f' new P' y
  let fiber := qMap_total_fiber 𝔽q β ⟨i, by omega⟩ 1 h_i_succ_lt y
  let P₀ := evenRefinement 𝔽q β h_ℓ_add_R_rate i coeffs
  let P₁ := oddRefinement 𝔽q β h_ℓ_add_R_rate i coeffs
  have he (k : Fin 2) : P.eval (fiber k).val =
      P₀.eval y.val + (fiber k).val * P₁.eval y.val := by
    have hq : (qMap 𝔽q β ⟨i, by omega⟩).eval (fiber k).val = y.val := by
      simpa only [iteratedQuotientMap_k_eq_1_is_qMap, Subtype.eq_iff] using
        (generates_quotient_point_if_is_fiber_of_y 𝔽q β i 1 i.isLt
          (fiber k) y ⟨k, rfl⟩).symm
    simp only [P, evaluation_poly_split_identity, Polynomial.eval_add, eval_comp, Polynomial.eval_mul,
      Polynomial.eval_X, hq, P₀, P₁]
  have hp : P'.eval y.val = (1 - r_chal) * P₀.eval y.val + r_chal * P₁.eval y.val := by
    simp only [P', new, P₀, P₁, intermediateEvaluationPoly, evenRefinement, oddRefinement,
      Fin.eta, Polynomial.eval_finset_sum, Polynomial.eval_mul, Polynomial.eval_C, add_mul,
      mul_assoc, mul_sum, Finset.sum_add_distrib]
    rfl
  dsimp only [f', fold, f]
  rw [he, he, hp]
  simp only [fiber, qMap_total_fiber_one_level_eq 𝔽q β i i.isLt,
    Fin2ToF2, Ne.symm Fin.zero_ne_one, ↓reduceIte, Submodule.coe_add, Submodule.coe_smul]
  simp only [zero_smul, one_smul, zero_add, get_sDomain_first_basis_eq_1]
  ring