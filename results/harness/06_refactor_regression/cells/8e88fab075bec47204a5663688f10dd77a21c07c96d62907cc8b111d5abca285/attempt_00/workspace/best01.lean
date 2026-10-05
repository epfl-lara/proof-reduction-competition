theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i)  := by
  have swap (a b : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j => if j = i then b j else a j) =
        (b i - a i) * 10 ^ i.1 + digits_to_num a := by
    apply eq_add_of_sub_eq
    rw [hdigits_to_num, ← Finset.sum_sub_distrib]
    simp only [← sub_mul, ite_sub, sub_self, ite_mul, zero_mul,
      Finset.sum_ite_eq', Finset.mem_univ, if_true]
  intro d e f h
  have hd (i : Fin 9) : 7 ∣ (e i - d i) * 10 ^ i.1 + digits_to_num d := by
    rw [← swap]
    exact ((hrelation d e).mp h.1).2 i
  have he (i : Fin 9) : 7 ∣ (f i - e i) * 10 ^ i.1 + digits_to_num e := by
    rw [← swap]
    exact ((hrelation e f).mp h.2).2 i
  have hs : 7 ∣ ∑ i : Fin 9, ((e i - d i) * 10 ^ i.1 + digits_to_num d) :=
    Finset.dvd_sum fun i _ => hd i
  simp only [Finset.sum_add_distrib, sub_mul, Finset.sum_sub_distrib,
    ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d, Finset.sum_const,
    Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul, Nat.cast_ofNat] at hs
  have hsum : 7 ∣ digits_to_num e + digits_to_num d := by
    convert dvd_sub hs (dvd_mul_right 7 (digits_to_num d)) using 1 <;> ring
  intro i
  apply (show IsCoprime (7 : ℤ) 10 from ⟨3, -2, by decide⟩).pow_right.dvd_of_dvd_mul_right
  convert dvd_sub hsum (dvd_add (hd i) (he i)) using 1 <;> ring
