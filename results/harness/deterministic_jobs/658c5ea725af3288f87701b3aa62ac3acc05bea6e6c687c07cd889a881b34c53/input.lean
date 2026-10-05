lemma time_deriv_time_deriv_electricField_of_isExtrema {A : ElectromagneticPotential d}
    {𝓕 : FreeSpace}
    (hA : ContDiff ℝ ∞ A) (J : LorentzCurrentDensity d)
    (hJ : ContDiff ℝ ∞ J) (h : IsExtrema 𝓕 A J)
    (t : Time) (x : Space d) (i : Fin d) :
    ∂ₜ (∂ₜ (A.electricField 𝓕.c · x i)) t =
      𝓕.c ^ 2 * ∑ j, (∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x) -
      𝓕.c ^ 2 / 𝓕.ε₀ * ∂[i] (J.chargeDensity 𝓕.c t ·) x -
      𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ (J.currentDensity 𝓕.c · x i) t := by
  have hEs (j : Fin d) : ContDiff ℝ 2 (A.electricField 𝓕.c t · j) :=
    electricField_apply_contDiff_space (hA.of_le (right_eq_inf.mp rfl)) t
  have hEd (j k : Fin d) := Space.deriv_differentiable (hEs j) k
  have hB (j : Fin d) : ContDiff ℝ 2 ↿(fun s y => A.magneticFieldMatrix 𝓕.c s y (j, i)) :=
    magneticFieldMatrix_contDiff _ (hA.of_le (right_eq_inf.mp rfl)) _
  have hBt (j : Fin d) := Space.space_deriv_differentiable_time (i := j) (hB j) x
  have hJt := LorentzCurrentDensity.currentDensity_apply_differentiable_time
    (c := 𝓕.c) (hJ.differentiable (by decide)) x i
  have hρ := LorentzCurrentDensity.chargeDensity_differentiable_space
    (c := 𝓕.c) (hJ.differentiable (by decide)) t
  have hg : ∑ j, ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x =
      𝓕.ε₀⁻¹ * ∂[i] (J.chargeDensity 𝓕.c t ·) x := by
    have hg := congrArg (fun f : Space d → ℝ => fderiv ℝ f x (Space.basis i))
      (funext fun y => ((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1)
    change fderiv ℝ (fun y => ∑ j, ∂[j] (A.electricField 𝓕.c t · j) y) x (Space.basis i) = _ at hg
    rw [fderiv_fun_sum (fun j _ => (hEd j j).differentiableAt)] at hg
    simpa only [div_eq_mul_inv, fderiv_mul_const hρ.differentiableAt,
      _root_.sum_apply, _root_.smul_apply, smul_eq_mul, ← Space.deriv_eq_fderiv_basis] using hg
  have hb (j : Fin d) :
      ∂ₜ (fun s => ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x) t =
      ∂[j] (∂[j] (A.electricField 𝓕.c t · i)) x -
      ∂[i] (∂[j] (A.electricField 𝓕.c t · j)) x := by
    rw [Space.time_deriv_comm_space_deriv (hB j)]
    simp_rw [time_deriv_magneticFieldMatrix A (hA.of_le (right_eq_inf.mp rfl))]
    rw [Space.fun_deriv_sub _ _ (hEd i j) (hEd j i), Space.deriv_commute _ (hEs j)]
  have he : ∂ₜ (A.electricField 𝓕.c · x i) = fun s =>
      1 / (𝓕.μ₀ * 𝓕.ε₀) * ∑ j, ∂[j] (A.magneticFieldMatrix 𝓕.c s · (j, i)) x -
      1 / 𝓕.ε₀ * J.currentDensity 𝓕.c s x i := by
    funext s
    rw [Time.deriv_euclid (electricField_differentiable_time
      (hA.of_le (right_eq_inf.mp rfl)) x), time_deriv_electricField_of_isExtrema hA J hJ h]
  rw [he, Time.deriv_eq,
    fderiv_fun_sub ((Differentiable.fun_sum fun j _ => hBt j).const_mul _).differentiableAt
      (hJt.const_mul _).differentiableAt,
    fderiv_const_mul (Differentiable.fun_sum fun j _ => hBt j).differentiableAt,
    fderiv_const_mul hJt.differentiableAt,
    fderiv_fun_sum (fun j _ => (hBt j).differentiableAt)]
  simp only [_root_.sub_apply, _root_.smul_apply, smul_eq_mul, _root_.sum_apply, ← Time.deriv_eq]
  simp_rw [hb]
  rw [Finset.sum_sub_distrib, hg, FreeSpace.c_sq]
  field_simp