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
  have hA3 : ContDiff ℝ 3 A := hA.of_le (right_eq_inf.mp rfl)
  have hdJ : Differentiable ℝ J := hJ.differentiable (by simp)
  have hc : 1 / (𝓕.μ₀ * 𝓕.ε₀) = 𝓕.c ^ 2 := by rw [mul_comm, FreeSpace.c_sq]
  have he : 1 / 𝓕.ε₀ = 𝓕.c ^ 2 * 𝓕.μ₀ := by rw [FreeSpace.c_sq]; simp [mul_comm, mul_assoc, mul_left_comm]
  let B : Fin d → Time → Space d → ℝ := fun j s y => A.magneticFieldMatrix 𝓕.c s y (j, i)
  have hB : ∀ j, ContDiff ℝ 2 ↿ (B j) := fun j => magneticFieldMatrix_contDiff _ hA3 (j, i)
  let E : Fin d → Space d → ℝ := fun k y => A.electricField 𝓕.c t y k
  have hE : ∀ j, ContDiff ℝ 2 (E j) := fun j => electricField_apply_contDiff_space hA3 t
  let F : Time → ℝ := fun s => ∑ j, ∂[j] (B j s) x
  let G : Time → ℝ := fun s => J.currentDensity 𝓕.c s x i
  have hF : Differentiable ℝ F :=
    Differentiable.fun_sum fun j _ => Space.space_deriv_differentiable_time (hB j) x
  have hG : Differentiable ℝ G :=
    LorentzCurrentDensity.currentDensity_apply_differentiable_time hdJ x i
  have h1 : ∂ₜ (A.electricField 𝓕.c · x i) = fun s => 𝓕.c ^ 2 * F s - 𝓕.c ^ 2 * 𝓕.μ₀ * G s := by
    funext s
    rw [← he, ← hc]
    exact (Time.deriv_euclid (electricField_differentiable_time hA2 x) s).trans
      (time_deriv_electricField_of_isExtrema hA J hJ h s x i)
  have h2 : ∂ₜ (fun s => 𝓕.c ^ 2 * F s - 𝓕.c ^ 2 * 𝓕.μ₀ * G s) t
      = 𝓕.c ^ 2 * ∂ₜ F t - 𝓕.c ^ 2 * 𝓕.μ₀ * ∂ₜ G t := by
    rw [Time.deriv_eq, fderiv_fun_sub (hF.differentiableAt.const_mul _)
      (hG.differentiableAt.const_mul _),
      fderiv_const_mul hF.differentiableAt _, fderiv_const_mul hG.differentiableAt _]
    simp only [_root_.sub_apply, _root_.smul_apply, smul_eq_mul, ← Time.deriv_eq]
  have h3 : ∂ₜ F t = ∑ j, ∂[j] (fun y => ∂ₜ (B j · y) t) x :=
    (Time.deriv_fun_sum Finset.univ (fun j s => ∂[j] (B j s) x)
      (fun j _ => (Space.space_deriv_differentiable_time (hB j) x).differentiableAt)).trans
      (Finset.sum_congr rfl fun j _ => Space.time_deriv_comm_space_deriv (hB j) t x)
  have h4 : ∑ j, ∂[j] (fun y => ∂ₜ (B j · y) t) x = ∑ j, ∂[j] (∂[j] (E i) - ∂[i] (E j)) x :=
    Finset.sum_congr rfl fun j _ => congrArg (fun f => ∂[j] f x)
      (funext fun y => time_deriv_magneticFieldMatrix A hA2 t y j i)
  have h5 : ∑ j, ∂[j] (∂[j] (E i) - ∂[i] (E j)) x
      = ∑ j, ∂[j] (∂[j] (E i)) x - ∑ j, ∂[j] (∂[i] (E j)) x := by
    rw [← Finset.sum_sub_distrib]
    exact Finset.sum_congr rfl fun j _ =>
      congrFun (Space.deriv_sub _ _ (Space.deriv_differentiable (hE i) j)
        (Space.deriv_differentiable (hE j) i)) x
  have h6 : ∑ j, ∂[j] (∂[i] (E j)) x = ∂[i] (fun y => ∑ j, ∂[j] (E j) y) x := by
    refine (Finset.sum_congr rfl fun j _ => congrFun (Space.deriv_commute _ (hE j)) x).trans ?_
    rw [Space.deriv_eq_fderiv_basis,
      fderiv_fun_sum fun j _ => (Space.deriv_differentiable (hE j) j).differentiableAt]
    simp only [FunLike.coe_sum, Finset.sum_apply, ← Space.deriv_eq_fderiv_basis]
  have h7 : ∂[i] (fun y => ∑ j, ∂[j] (E j) y) x
      = 1 / 𝓕.ε₀ * ∂[i] (fun y => J.chargeDensity 𝓕.c t y) x := by
    have hd : (fun y => ∑ j, ∂[j] (E j) y) = (1 / 𝓕.ε₀) • (fun y => J.chargeDensity 𝓕.c t y) := by
      funext y
      show (∇ ⬝ (A.electricField 𝓕.c t)) y = (1 / 𝓕.ε₀) * J.chargeDensity 𝓕.c t y
      rw [((isExtrema_iff_gauss_ampere_magneticFieldMatrix hA J hJ).mp h t y).1, div_eq_mul_inv]
      ring
    rw [hd, Space.deriv_const_smul (1 / 𝓕.ε₀)
      (LorentzCurrentDensity.chargeDensity_differentiable_space hdJ t),
      Pi.smul_apply, smul_eq_mul]
  rw [h1, h2, h3, h4, h5, h6, h7, ← he]
  simp only [div_eq_mul_inv]
  ring