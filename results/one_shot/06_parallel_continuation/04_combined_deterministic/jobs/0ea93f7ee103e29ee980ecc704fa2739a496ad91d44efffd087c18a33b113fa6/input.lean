theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have replace_eq : ∀ (x y : Fin 9 → ℤ) (i : Fin 9),
      digits_to_num (fun j : Fin 9 => if j = i then y j else x j) =
      digits_to_num x + (y i - x i) * 10^(i:ℕ) := by
    intro x y i
    simp only [hdigits_to_num]
    calc
      ∑ j : Fin 9, (if j = i then y j else x j) * 10^(j:ℕ)
          = ∑ j : Fin 9, (x j * 10^(j:ℕ) + (if j = i then (y j - x j) else 0) * 10^(j:ℕ)) := by
            apply Finset.sum_congr rfl
            intro j _
            by_cases h : j = i
            · simp [h]
              ring
            · simp [h]
      _ = (∑ j : Fin 9, x j * 10^(j:ℕ)) + ∑ j : Fin 9, (if j = i then (y j - x j) else 0) * 10^(j:ℕ) := by
            rw [Finset.sum_add_distrib]
      _ = (∑ j : Fin 9, x j * 10^(j:ℕ)) + (y i - x i) * 10^(i:ℕ) := by
            simp only [ite_mul, zero_mul, Finset.sum_ite_eq', Finset.mem_univ, ↓reduceIte]
  have sum_sub (x y : Fin 9 → ℤ) :
      ∑ i : Fin 9, (y i - x i) * 10^(i:ℕ) = digits_to_num y - digits_to_num x := by
    simp only [hdigits_to_num]
    simp [sub_mul, Finset.sum_sub_distrib]
  have hde_i : ∀ i : Fin 9, 7 ∣ digits_to_num d + (e i - d i) * 10^(i:ℕ) := by
    intro i
    have := ((hrelation d e).mp h.1).2 i
    rwa [replace_eq d e i] at this
  have hef_i : ∀ i : Fin 9, 7 ∣ digits_to_num e + (f i - e i) * 10^(i:ℕ) := by
    intro i
    have := ((hrelation e f).mp h.2).2 i
    rwa [replace_eq e f i] at this
  have hsum : 7 ∣ ∑ i : Fin 9, (digits_to_num d + (e i - d i) * 10^(i:ℕ)) := by
    apply Finset.dvd_sum
    intro i _
    exact hde_i i
  have hsum_eq : ∑ i : Fin 9, (digits_to_num d + (e i - d i) * 10^(i:ℕ)) = digits_to_num e + 8 * digits_to_num d := by
    rw [Finset.sum_add_distrib]
    rw [sum_sub d e]
    simp only [Finset.sum_const, Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul, Nat.cast_ofNat]
    ring
  have hNe_plus_Nd : 7 ∣ digits_to_num e + digits_to_num d := by
    have h1 : 7 ∣ digits_to_num e + 8 * digits_to_num d := by
      rwa [hsum_eq] at hsum
    have h2 : 7 ∣ 7 * digits_to_num d := by
      use digits_to_num d
    have h3 : 7 ∣ (digits_to_num e + 8 * digits_to_num d) - 7 * digits_to_num d := dvd_sub h1 h2
    have h4 : (digits_to_num e + 8 * digits_to_num d) - 7 * digits_to_num d = digits_to_num e + digits_to_num d := by ring
    rwa [h4] at h3
  have hdiff_i : ∀ i : Fin 9, 7 ∣ (f i - d i) * 10^(i:ℕ) := by
    intro i
    have hA : 7 ∣ digits_to_num d + (e i - d i) * 10^(i:ℕ) := hde_i i
    have hB : 7 ∣ digits_to_num e + (f i - e i) * 10^(i:ℕ) := hef_i i
    have hAB : 7 ∣ (digits_to_num d + (e i - d i) * 10^(i:ℕ)) + (digits_to_num e + (f i - e i) * 10^(i:ℕ)) := dvd_add hA hB
    have hC : 7 ∣ digits_to_num d + digits_to_num e := by
      rw [add_comm]
      exact hNe_plus_Nd
    have hD : 7 ∣ ((digits_to_num d + (e i - d i) * 10^(i:ℕ)) + (digits_to_num e + (f i - e i) * 10^(i:ℕ))) - (digits_to_num d + digits_to_num e) := dvd_sub hAB hC
    have hE : ((digits_to_num d + (e i - d i) * 10^(i:ℕ)) + (digits_to_num e + (f i - e i) * 10^(i:ℕ))) - (digits_to_num d + digits_to_num e) = (f i - d i) * 10^(i:ℕ) := by ring
    rwa [hE] at hD
  have hprime_nat : Nat.Prime 7 := by decide
  have hprime_int : Prime (7 : ℤ) := Int.prime_iff_natAbs_prime.mpr hprime_nat
  have h10_not_dvd : ∀ i : Fin 9, ¬ (7 : ℤ) ∣ (10 : ℤ) ^ (i:ℕ) := by
    intro i h
    have hnat : (7 : ℕ) ∣ (10 : ℕ) ^ (i:ℕ) := by
      norm_cast at h ⊢
    have h10 : (7 : ℕ) ∣ 10 := hprime_nat.dvd_of_dvd_pow hnat
    norm_num at h10
  intro i
  have h1 : 7 ∣ (f i - d i) * 10^(i:ℕ) := hdiff_i i
  have h2 : 7 ∣ f i - d i := by
    have := hprime_int.dvd_mul.mp h1
    cases this with
    | inl h => exact h
    | inr h => exfalso; exact h10_not_dvd i h
  have h3 : 7 ∣ -(f i - d i) := dvd_neg.mpr h2
  have h4 : -(f i - d i) = d i - f i := by ring
  rwa [h4] at h3