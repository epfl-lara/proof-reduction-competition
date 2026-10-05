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
    LorentzCurrentDensity.currentDensity_apply_differentiable_time (hJ.differentiable (by simp)) x i
  have hd (j : Fin d) :
      ∂ₜ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t =
      ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x -
      ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x := by
    rw [Space.time_deriv_comm_space_deriv
      (magneticFieldMatrix_contDiff _ (hA.of_le (right_eq_inf.mp rfl)) (j, i))]
    simp_rw [time_deriv_magneticFieldMatrix _ (hA.of_le (ENat.LEInfty.out))]
    rw [Space.deriv_eq_fderiv_basis,
      fderiv_fun_sub (hEd _ _).differentiableAt (hEd _ _).differentiableAt]
    change ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x -
      ∂[j] (∂[i] (A.electricField 𝓕.c t · j)) x = _
    rw [Space.deriv_commute _ (hEs j)]
  have hg :
      ∑ j, ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x =
      (1 / 𝓕.ε₀) * ∂[i] (J.chargeDensity 𝓕.c t ·) x := by
    have he : (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) =
        (fun y => (1 / 𝓕.ε₀) * J.chargeDensity 𝓕.c t y) := by
      funext y
      have := ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1
      change (∇ ⬝ (A.electricField 𝓕.c t)) y = _
      simpa only [div_eq_mul_inv, one_div, one_mul, mul_one, mul_comm] using this
    have hs := congrArg (fun f => ∂[i] f x) he
    rw [Space.deriv_eq_fderiv_basis,
      fderiv_fun_sum fun j _ => (hEd j j).differentiableAt,
      Space.deriv_eq_fderiv_basis,
      fderiv_const_mul (LorentzCurrentDensity.chargeDensity_differentiable_space
        (hJ.differentiable (by simp)) t).differentiableAt] at hs
    simpa only [_root_.sum_apply, _root_.smul_apply, smul_eq_mul,
      ← Space.deriv_eq_fderiv_basis] using hs
  calc _
    _= ∂ₜ (fun t =>
      1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, Space.deriv j (fun x => magneticFieldMatrix 𝓕.c A t x (j, i)) x -
      1 / 𝓕.ε₀ * LorentzCurrentDensity.currentDensity 𝓕.c J t x i) t := by
        conv_lhs =>
          enter [1]
          change fun t => ∂ₜ (A.electricField 𝓕.c · x i) t
          enter [t]
          rw [Time.deriv_euclid (electricField_differentiable_time
            (hA.of_le (right_eq_inf.mp rfl)) _),
            time_deriv_electricField_of_isExtrema hA J hJ h]
    _ = 1 / (𝓕.μ₀ * 𝓕.ε₀) *
        ∑ j, ∂ₜ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t -
        1 / 𝓕.ε₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
      rw [Time.deriv_eq,
        fderiv_fun_sub
          ((Differentiable.fun_sum fun j _ => hBt j).const_mul _).differentiableAt
          (hJt.const_mul _).differentiableAt,
        fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt,
        fderiv_const_mul hJt.differentiableAt,
        fderiv_fun_sum fun j _ => (hBt j).differentiableAt]
      simp only [Time.deriv_eq, _root_.sum_apply, _root_.sub_apply,
        _root_.smul_apply, smul_eq_mul]
    _ = _ := by
      simp only [Finset.sum_apply, hd, Finset.sum_sub_distrib, hg, FreeSpace.c_sq]
      field_simp
      <;> ring