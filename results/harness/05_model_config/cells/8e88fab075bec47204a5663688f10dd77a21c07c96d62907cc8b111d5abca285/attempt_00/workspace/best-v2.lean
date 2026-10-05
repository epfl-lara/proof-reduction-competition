theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have swap (a b : Fin 9 → ℤ) (h : relation a b) (i : Fin 9) :
      7 ∣ (b i - a i) * 10 ^ i.1 + digits_to_num a := by
    have hs : digits_to_num (fun j => if j = i then b j else a j) - digits_to_num a =
        (b i - a i) * 10 ^ i.1 := by
      simp only [hdigits_to_num]
      rw [← Finset.sum_sub_distrib, Finset.sum_eq_single i]
      · simp only [ite_true, sub_mul]
      · intro j _ hji
        simp only [if_neg hji, sub_self]
      · simp only [Finset.mem_univ, not_true_eq_false, false_implies]
    rw [← eq_add_of_sub_eq hs]
    exact ((hrelation a b).mp h).2 i
  intro d e f h i
  have hd := swap d e h.1
  have he := swap e f h.2
  have hs : 7 ∣ digits_to_num e - digits_to_num d + 9 * digits_to_num d := by
    simpa only [Finset.sum_add_distrib, sub_mul, Finset.sum_sub_distrib,
      ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d,
      Finset.sum_const, Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul,
      Nat.cast_ofNat] using (Finset.dvd_sum (fun j (_ : j ∈ Finset.univ) => hd j))
  have hc : IsCoprime (7 : ℤ) 10 := ⟨3, -2, by decide⟩
  apply hc.pow_right.dvd_of_dvd_mul_right
  convert dvd_sub hs (dvd_add (dvd_add (hd i) (he i))
    (dvd_mul_right (7 : ℤ) (digits_to_num d))) using 1 <;> ring
