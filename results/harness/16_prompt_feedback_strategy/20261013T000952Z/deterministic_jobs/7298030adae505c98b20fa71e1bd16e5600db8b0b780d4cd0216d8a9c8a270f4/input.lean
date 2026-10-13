theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have step {a b} (hab : relation a b) i :
      7 ∣ b i * 10 ^ i.val - a i * 10 ^ i.val + digits_to_num a := by
    apply Int.dvd_trans (((hrelation a b).mp hab).2 i)
    apply dvd_of_eq
    apply Int.sub_eq_iff_eq_add.mp
    rw [hdigits_to_num, ← Finset.sum_sub_distrib]
    simp only [ite_mul, ite_sub, Int.sub_self, Fintype.sum_ite_eq']
  intro d e f h i
  have hs := Finset.dvd_sum (s := Finset.univ) fun i _ => step h.1 i
  simp only [Finset.sum_add_distrib, Finset.sum_sub_distrib,
    Fin.sum_const,
    ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d] at hs
  apply ((show IsCoprime (7 : ℤ) 10 from by decide).pow_right
    (n := i.val)).dvd_of_dvd_mul_right
  apply Int.dvd_trans (Int.dvd_sub (Int.dvd_sub hs (Int.dvd_mul_right 7 (digits_to_num d)))
    (Int.dvd_add (step h.1 i) (step h.2 i)))
  apply dvd_of_eq
  ring1