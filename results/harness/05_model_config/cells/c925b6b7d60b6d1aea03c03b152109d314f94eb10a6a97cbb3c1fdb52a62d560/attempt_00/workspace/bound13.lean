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
  dsimp only [fold]
  intro y
  let x := qMap_total_fiber 𝔽q β (i := ⟨i, fin_ℓ_lt_r (h_ℓ_add_R_rate := h_ℓ_add_R_rate) i⟩) (steps := 1)
    (h_i_add_steps := h_i_succ_lt) y
  have hx : (x 1).val = (x 0).val + 1 := by
    simp only [x, qMap_total_fiber_one_level_eq 𝔽q β i (Nat.succ_le_of_lt i.isLt) y,
      Fin2ToF2, Fin.isValue, one_ne_zero, ↓reduceIte, zero_smul, one_smul,
      Submodule.coe_add, Submodule.coe_zero, zero_add, get_sDomain_first_basis_eq_1]
    exact add_comm _ _
  have hq (k : Fin 2) := congrArg Subtype.val
    (generates_quotient_point_if_is_fiber_of_y 𝔽q β i 1 (Nat.succ_le_of_lt i.isLt) (x k) y ⟨k, rfl⟩)
  simp only [x, iteratedQuotientMap_k_eq_1_is_qMap] at hq
  let P₀ := evenRefinement 𝔽q β h_ℓ_add_R_rate i coeffs
  let P₁ := oddRefinement 𝔽q β h_ℓ_add_R_rate i coeffs
  simp only [evaluation_poly_split_identity 𝔽q β h_ℓ_add_R_rate i coeffs,
    Polynomial.eval_add, Polynomial.eval_mul, Polynomial.eval_X, eval_comp, ←hq]
  calc
    _ = (1 - r_chal) * P₀.eval y.val + r_chal * P₁.eval y.val := by rw [hx]; ring1
    _ = _ := by
      simp only [P₀, P₁, evenRefinement, oddRefinement, intermediateEvaluationPoly,
        Polynomial.eval_finset_sum, Polynomial.eval_mul, Polynomial.eval_C, Fin.eta, Nat.sub_add_eq,
        add_mul, mul_assoc, mul_sum, sum_add_distrib]
      rfl
