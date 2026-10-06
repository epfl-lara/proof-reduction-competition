theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have transfer {x y : ℤ} (hx : 7 ∣ x) (hxy : x = y) : 7 ∣ y := hxy ▸ hx
  have step (a b : Fin 9 → ℤ) (hab : relation a b) (i : Fin 9) :
      7 ∣ b i * (10 : ℤ) ^ i.1 - a i * (10 : ℤ) ^ i.1 + digits_to_num a := by
    apply transfer (((hrelation a b).mp hab).2 i)
    apply sub_eq_iff_eq_add.mp
    rw [hdigits_to_num, ← Finset.sum_sub_distrib]
    simp only [ite_mul, ite_sub, sub_self, Fintype.sum_ite_eq']
  have hd := step d e h.1
  have hsum : 7 ∣ digits_to_num d + digits_to_num e := by
    apply transfer (dvd_sub (Finset.dvd_sum (s := Finset.univ) (fun i _ => hd i))
      (dvd_mul_right (7 : ℤ) (digits_to_num d)))
    rw [Finset.sum_add_distrib, Finset.sum_sub_distrib, Finset.sum_const,
      Finset.card_fin,
      ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d]
    ring1
  intro i
  apply ((show IsCoprime (7 : ℤ) 10 from by decide).pow_right (n := i.1)).dvd_of_dvd_mul_right
  apply transfer (dvd_sub hsum (dvd_add (hd i) (step e f h.2 i)))
  ring1