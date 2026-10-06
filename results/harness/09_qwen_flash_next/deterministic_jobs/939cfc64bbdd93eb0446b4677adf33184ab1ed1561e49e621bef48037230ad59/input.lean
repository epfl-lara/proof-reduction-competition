theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have W : ∀ dig : Fin 9 → ℤ, digits_to_num dig = ∑ i : Fin 9, dig i * (10 : ℤ) ^ (i : ℕ) :=
    congrFun hdigits_to_num
  have key (x y : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j => if j = i then x j else y j) =
        digits_to_num y + (x i - y i) * (10 : ℤ) ^ (i : ℕ) := by
    have h₁ : (fun j : Fin 9 => (if j = i then x j else y j) * (10 : ℤ) ^ (j : ℕ))
        = fun j => y j * (10 : ℤ) ^ (j : ℕ) + (if j = i then (x j - y j) * (10 : ℤ) ^ (j : ℕ) else 0) := by
      funext j
      by_cases h : j = i
      · rw [if_pos h, if_pos h]; ring
      · rw [if_neg h, if_neg h]; ring
    simp only [W]
    rw [h₁, Finset.sum_add_distrib, Fintype.sum_ite_eq']
  have hd : ∀ i : Fin 9, 7 ∣ digits_to_num d + (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
    intro i
    rw [← key e d i]
    exact ((hrelation d e).mp h.1).2 i
  have he : ∀ i : Fin 9, 7 ∣ digits_to_num e + (f i - e i) * (10 : ℤ) ^ (i : ℕ) := by
    intro i
    rw [← key f e i]
    exact ((hrelation e f).mp h.2).2 i
  have sum_sub (x y : Fin 9 → ℤ) :
      ∑ i : Fin 9, (x i - y i) * (10 : ℤ) ^ (i : ℕ) = digits_to_num x - digits_to_num y := by
    simp only [W, sub_mul, Finset.sum_sub_distrib]
  have sum_div (x y : Fin 9 → ℤ)
      (hxy : ∀ i : Fin 9, 7 ∣ digits_to_num y + (x i - y i) * (10 : ℤ) ^ (i : ℕ)) :
      7 ∣ digits_to_num x + digits_to_num y := by
    have h₁ : 7 ∣ ∑ i : Fin 9, (digits_to_num y + (x i - y i) * (10 : ℤ) ^ (i : ℕ)) :=
      Finset.dvd_sum fun i _ => hxy i
    have h₂ : ∑ i : Fin 9, (digits_to_num y + (x i - y i) * (10 : ℤ) ^ (i : ℕ))
        = 8 * digits_to_num y + digits_to_num x := by
      rw [Finset.sum_add_distrib, sum_sub, Finset.sum_const, Finset.card_univ, Fintype.card_fin,
        Int.nsmul_eq_mul, Nat.cast_ofNat]
      ring
    rw [h₂] at h₁
    rw [show digits_to_num x + digits_to_num y = (8 * digits_to_num y + digits_to_num x) - 7 * digits_to_num y from by ring]
    exact dvd_sub h₁ (dvd_mul_right 7 _)
  have cd : 7 ∣ digits_to_num e + digits_to_num d := sum_div e d hd
  intro i
  have hc : IsCoprime (7 : ℤ) ((10 : ℤ) ^ (i : ℕ)) :=
    IsCoprime.pow_right (n := (i : ℕ)) (⟨3, -2, by norm_num⟩ : IsCoprime (7 : ℤ) (10 : ℤ))
  have h₄ : 7 ∣ (d i - f i) * (10 : ℤ) ^ (i : ℕ) := by
    rw [show (d i - f i) * (10 : ℤ) ^ (i : ℕ)
        = (digits_to_num e + digits_to_num d) - (digits_to_num d + (e i - d i) * (10 : ℤ) ^ (i : ℕ))
          - (digits_to_num e + (f i - e i) * (10 : ℤ) ^ (i : ℕ)) from by ring]
    exact dvd_sub (dvd_sub cd (hd i)) (he i)
  exact IsCoprime.dvd_of_dvd_mul_right hc h₄