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
  have hEd : ∀ j k, Differentiable ℝ (∂[k] (fun y => A.electricField 𝓕.c t y j)) :=
    fun j k => Space.deriv_differentiable (hEs j) k
  have hBt : ∀ j, Differentiable ℝ
      (fun s => ∂[j] (fun y => A.magneticFieldMatrix 𝓕.c s y (j, i)) x) :=
    fun j => Space.space_deriv_differentiable_time (i := j)
      (magneticFieldMatrix_contDiff _ (hA.of_le (right_eq_inf.mp rfl)) (j, i)) x
  have hJt : Differentiable ℝ (fun s => J.currentDensity 𝓕.c s x i) :=
    LorentzCurrentDensity.currentDensity_apply_differentiable_time (hJ.differentiable (by decide)) x i
  have hcurl (j : Fin d) :
      ∂ₜ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t =
        ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x -
        ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x := by
    rw [Space.time_deriv_comm_space_deriv
      (magneticFieldMatrix_contDiff _ (hA.of_le (right_eq_inf.mp rfl)) (j, i))]
    simp_rw [time_deriv_magneticFieldMatrix _ (hA.of_le (ENat.LEInfty.out))]
    rw [Space.deriv_eq_fderiv_basis,
      fderiv_fun_sub (hEd i j).differentiableAt (hEd j i).differentiableAt]
    simp only [_root_.sub_apply, ← Space.deriv_eq_fderiv_basis]
    rw [Space.deriv_commute _ (hEs j)]
  have hρ : (∑ j, ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x) =
      𝓕.ε₀⁻¹ * ∂[i] (J.chargeDensity 𝓕.c t ·) x := by
    have hg := congrArg (fun f : Space d → ℝ => fderiv ℝ f x (Space.basis i))
      (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
    change fderiv ℝ (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) x (Space.basis i) =
      fderiv ℝ (fun y => J.chargeDensity 𝓕.c t y / 𝓕.ε₀) x (Space.basis i) at hg
    simpa only [div_eq_inv_mul,
      fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt),
      fderiv_const_mul (LorentzCurrentDensity.chargeDensity_differentiable_space
        (hJ.differentiable (by decide)) t).differentiableAt,
      _root_.sum_apply, _root_.smul_apply, smul_eq_mul,
      ← Space.deriv_eq_fderiv_basis] using hg
  conv_lhs =>
    enter [1]
    change fun s => ∂ₜ (A.electricField 𝓕.c · x i) s
    enter [s]
    rw [Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le (right_eq_inf.mp rfl)) x),
      time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [Time.deriv_eq,
    fderiv_fun_sub ((Differentiable.fun_sum fun j _ => hBt j).const_mul _).differentiableAt
      (hJt.const_mul _).differentiableAt,
    fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt,
    fderiv_const_mul hJt.differentiableAt,
    fderiv_fun_sum (fun j _ => (hBt j).differentiableAt)]
  simp only [_root_.sub_apply, _root_.smul_apply, _root_.sum_apply, smul_eq_mul,
    ← Time.deriv_eq, hcurl, Finset.sum_sub_distrib, hρ, FreeSpace.c_sq]
  field_simp <;> ring