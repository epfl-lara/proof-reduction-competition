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
  have hBt := fun j => Space.space_deriv_differentiable_time (i := j) (hB j) x
  have hJt := LorentzCurrentDensity.currentDensity_apply_differentiable_time
    (hJ.differentiable (by decide)) x i (c := 𝓕.c)
  have hρ := LorentzCurrentDensity.chargeDensity_differentiable_space
    (hJ.differentiable (by decide)) t (c := 𝓕.c)
  have hg : (∑ j, ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x) =
      ∂[i] (J.chargeDensity 𝓕.c t ·) x / 𝓕.ε₀ := by
    calc
      _ = ∂[i] (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) x := by
        symm
        rw [Space.deriv_eq_fderiv_basis,
          fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt)]
        simp only [_root_.sum_apply, ← Space.deriv_eq_fderiv_basis]
      _ = ∂[i] (fun y => J.chargeDensity 𝓕.c t y / 𝓕.ε₀) x :=
        congrArg (fun f : Space d → ℝ => ∂[i] f x)
          (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
      _ = _ := by
        simp only [div_eq_mul_inv]
        rw [Space.deriv_eq_fderiv_basis, fderiv_mul_const hρ.differentiableAt]
        exact mul_comm _ _
  conv_lhs =>
    enter [1, s]
    rw [Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le (right_eq_inf.mp rfl)) _) _, time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    fderiv_fun_sub ((Differentiable.fun_sum fun j _ => hBt j).const_mul _).differentiableAt
      (hJt.const_mul _).differentiableAt,
    fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt,
    fderiv_const_mul hJt.differentiableAt,
    fderiv_fun_sum (fun j _ => (hBt j).differentiableAt)]
  simp only [_root_.sub_apply, _root_.smul_apply, _root_.sum_apply,
    smul_eq_mul, ← Time.deriv_eq]
  conv_lhs =>
    enter [1, 2, 2, j]
    rw [Space.time_deriv_comm_space_deriv (hB j)]
    trace_state
    enter [2, y]
    rw [time_deriv_magneticFieldMatrix A (hA.of_le (right_eq_inf.mp rfl))]
  conv_lhs =>
    enter [1, 2, 2, j]
    rw [Space.fun_deriv_sub _ _ (hEd i j) (hEd j i)]
    trace_state
    enter [2]
    rw [Space.deriv_commute _ (hEs j)]
  rw [Finset.sum_sub_distrib, hg, mul_sub, FreeSpace.c_sq]
  field_simp
