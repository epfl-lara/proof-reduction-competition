theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have hs (a b : Fin 9 → ℤ) (h : relation a b) (i : Fin 9) :
      7 ∣ (b i - a i) * 10 ^ i.val + digits_to_num a := by
    have he : digits_to_num (fun j => if j = i then b j else a j) - digits_to_num a =
        (b i - a i) * 10 ^ i.val := by
      rw [hdigits_to_num, ← Finset.sum_sub_distrib]
      simp only [ite_mul, ite_sub, sub_self, ← sub_mul,
        Finset.sum_ite_eq', Finset.mem_univ, if_true]
    rw [← he, sub_add_cancel]
    exact ((hrelation a b).mp h).2 i
  intro d e f h i
  have hd := hs d e h.1
  have he := hs e f h.2
  have ht := Finset.dvd_sum (s := Finset.univ) (fun j _ => hd j)
  simp only [Finset.sum_add_distrib, sub_mul, Finset.sum_sub_distrib,
    Finset.sum_const, Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul,
    Nat.cast_ofNat, ← congrFun hdigits_to_num] at ht
  have ht' : 7 ∣ digits_to_num e + digits_to_num d := by omega
  have hw : 7 ∣ (d i - f i) * 10 ^ i.val := by
    convert dvd_sub ht' (dvd_add (hd i) (he i)) using 1 <;> ring
  have hc : IsCoprime (7 : ℤ) 10 := ⟨3, -2, by decide⟩
  exact hc.pow_right.dvd_of_dvd_mul_right hw
