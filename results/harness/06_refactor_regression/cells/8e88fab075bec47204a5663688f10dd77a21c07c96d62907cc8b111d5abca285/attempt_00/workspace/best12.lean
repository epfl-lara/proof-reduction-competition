theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i)   := by
  have step (a b : Fin 9 → ℤ) (hab : relation a b) (i : Fin 9) :
      7 ∣ b i * 10 ^ i.1 - a i * 10 ^ i.1 + digits_to_num a := by
    convert ((hrelation a b).mp hab).2 i using 1
    symm
    apply eq_add_of_sub_eq
    simp only [hdigits_to_num, ← Finset.sum_sub_distrib, ite_mul, ite_sub, sub_self,
      Finset.sum_ite_eq', Finset.mem_univ, if_true]
  intro d e f h
  have hd := step d e h.1
  have he := step e f h.2
  have hs := Finset.dvd_sum (s := Finset.univ) (fun i _ => hd i)
  simp only [Finset.sum_add_distrib, Finset.sum_sub_distrib,
    ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d, Finset.sum_const,
    Finset.card_univ, Fintype.card_fin] at hs
  intro i
  apply (show IsCoprime (7 : ℤ) 10 from ⟨3, -2, by decide⟩).pow_right.dvd_of_dvd_mul_right
  convert dvd_sub (dvd_sub hs (dvd_add (hd i) (he i)))
    (dvd_mul_right 7 (digits_to_num d)) using 1 <;> ring
