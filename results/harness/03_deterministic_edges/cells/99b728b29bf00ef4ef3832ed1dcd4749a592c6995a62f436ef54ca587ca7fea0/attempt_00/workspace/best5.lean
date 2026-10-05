lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hEs : ∀ j, ContDiff ℝ 2 (fun y => A.electricField 𝓕.c t y j) :=
    fun j => electricField_apply_contDiff_space (i := j) (hA.of_le (right_eq_inf.mp rfl)) t
  have hEd := fun j k => Space.deriv_differentiable (hEs j) k
  have hB : ∀ j, ContDiff ℝ 2 ↿(fun s y => A.magneticFieldMatrix 𝓕.c s y (j, i)) :=
    fun j => magneticFieldMatrix_contDiff A (hA.of_le (right_eq_inf.mp rfl)) (j, i)
  have hBt := fun j => Space.space_deriv_differentiable_time (i := j) (hB j) x t
  have hs := DifferentiableAt.fun_sum (u := Finset.univ) (fun j _ => hBt j)
  have hJt := LorentzCurrentDensity.currentDensity_apply_differentiable_time
    (hJ.differentiable (by decide)) x i (c := 𝓕.c) t
  have hρ := LorentzCurrentDensity.chargeDensity_differentiable_space
    (hJ.differentiable (by decide)) t (c := 𝓕.c) x
  have hg := congrArg (fun f : Space d → ℝ => fderiv ℝ f x (Space.basis i))
    (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
  unfold Space.div at hg
  simp only [div_eq_mul_inv, fderiv_fun_sum (fun j _ => hEd j j x),
    fderiv_mul_const hρ, _root_.sum_apply, _root_.smul_apply,
    smul_eq_mul, ← Space.deriv_eq_fderiv_basis] at hg
  conv_lhs =>
    enter [1, s]
    rw [Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le (right_eq_inf.mp rfl)) _) _, time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    fderiv_fun_sub (hs.const_mul _) (hJt.const_mul _),
    fderiv_const_mul hs,
    fderiv_const_mul hJt,
    fderiv_fun_sum (fun j _ => hBt j)]
  simp only [_root_.sub_apply, _root_.smul_apply, _root_.sum_apply,
    smul_eq_mul, ← Time.deriv_eq]
  simp only [fun j => Space.time_deriv_comm_space_deriv (i := j) (hB j) t x,
    time_deriv_magneticFieldMatrix A (hA.of_le (right_eq_inf.mp rfl)),
    fun j => Space.fun_deriv_sub (u := j) _ _ (hEd i j) (hEd j i),
    fun j => Space.deriv_commute (u := j) (v := i) _ (hEs j)]
  rw [Finset.sum_sub_distrib, hg, mul_sub, FreeSpace.c_sq, mul_comm 𝓕.ε₀ 𝓕.μ₀]
  simp only [div_eq_mul_inv, one_mul, mul_inv_rev, mul_assoc,
    inv_mul_cancel_left₀ 𝓕.μ₀_ne_zero]
