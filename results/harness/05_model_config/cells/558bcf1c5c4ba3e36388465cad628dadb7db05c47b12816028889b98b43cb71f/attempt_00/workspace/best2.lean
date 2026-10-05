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
  have hBc := fun j => magneticFieldMatrix_contDiff (n := 2) (c := 𝓕.c) A
    (hA.of_le (right_eq_inf.mp rfl)) (j, i)
  have hBt := fun j => Space.space_deriv_differentiable_time (i := j) (hBc j) x
  have hJt := LorentzCurrentDensity.currentDensity_apply_differentiable_time
    (c := 𝓕.c) (hJ.differentiable (by decide)) x i
  have hgd := congrArg (fun f => fderiv ℝ f x (Space.basis i))
    (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
  unfold Space.div at hgd
  simp only [div_eq_mul_inv] at hgd
  rw [fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt),
    fderiv_mul_const (LorentzCurrentDensity.chargeDensity_differentiable_space
      (hJ.differentiable (by decide)) t).differentiableAt] at hgd
  simp only [_root_.sum_apply, _root_.smul_apply, smul_eq_mul,
    ← Space.deriv_eq_fderiv_basis] at hgd
  have hb (j) : ∂ₜ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t =
      ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x -
      ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x := by
    rw [Space.time_deriv_comm_space_deriv (hBc j)]
    simp_rw [time_deriv_magneticFieldMatrix A (hA.of_le (ENat.LEInfty.out))]
    rw [Space.fun_deriv_sub _ _ (hEd i j) (hEd j i), Space.deriv_commute _ (hEs j)]
  conv_lhs =>
    enter [1, s]
    rw [Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le (ENat.LEInfty.out)) x), time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    fderiv_fun_sub ((Differentiable.fun_sum fun j _ => hBt j).const_mul _).differentiableAt
      (hJt.const_mul _).differentiableAt,
    fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt,
    fderiv_const_mul hJt.differentiableAt,
    fderiv_fun_sum (fun j _ => (hBt j).differentiableAt)]
  simp only [_root_.sub_apply, _root_.smul_apply, smul_eq_mul, _root_.sum_apply,
    ← Time.deriv_eq, hb, Finset.sum_sub_distrib, hgd, mul_sub, FreeSpace.c_sq]
  field_simp
