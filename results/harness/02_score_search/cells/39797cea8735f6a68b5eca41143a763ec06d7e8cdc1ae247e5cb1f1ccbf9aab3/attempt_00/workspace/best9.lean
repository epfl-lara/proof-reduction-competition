lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hA2 : ContDiff ℝ 2 A := hA.of_le (right_eq_inf.mp rfl)
  have hEs (j : Fin d) := electricField_apply_contDiff_space
    (n := 2) (c := 𝓕.c) (i := j) (hA.of_le (right_eq_inf.mp rfl)) t
  have hEd (j k : Fin d) := Space.deriv_differentiable (hEs j) k
  have hB (j : Fin d) := magneticFieldMatrix_contDiff
    (n := 2) (c := 𝓕.c) A (hA.of_le (right_eq_inf.mp rfl)) (j, i)
  have hG := congrArg (fun f : Space d → ℝ => fderiv ℝ f x (Space.basis i))
    (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
  change fderiv ℝ (fun y => ∑ j : Fin d, _) x _ = _ at hG
  rw [fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt)] at hG
  simp only [div_eq_mul_inv, fderiv_mul_const
      (LorentzCurrentDensity.chargeDensity_differentiable_space
        (hJ.differentiable (by simp)) t x), _root_.sum_apply,
    _root_.smul_apply, smul_eq_mul, ← Space.deriv_eq_fderiv_basis] at hG
  conv_lhs =>
    enter [1]
    ext s
    rw [Time.deriv_euclid (electricField_differentiable_time hA2 x),
      time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    (((HasFDerivAt.fun_sum (fun j _ => (Space.space_deriv_differentiable_time (i := j) (hB j) x t).hasFDerivAt)).const_mul _).fun_sub
      ((LorentzCurrentDensity.currentDensity_apply_differentiable_time
        (hJ.differentiable (by simp)) x i t).hasFDerivAt.const_mul _)).fderiv]
  simp only [_root_.sub_apply, _root_.smul_apply, _root_.sum_apply, smul_eq_mul,
    ← Time.deriv_eq]
  conv_lhs =>
    enter [1, 2, 2, j]
    rw [Space.time_deriv_comm_space_deriv (hB j)]
    simp only [time_deriv_magneticFieldMatrix A hA2]
    rw [Space.fun_deriv_sub _ _ (hEd i j) (hEd j i), Space.deriv_commute _ (hEs j)]
  rw [Finset.sum_sub_distrib, hG]
  simp [FreeSpace.c_sq, mul_sub, div_eq_mul_inv, mul_assoc, mul_left_comm, mul_comm]
