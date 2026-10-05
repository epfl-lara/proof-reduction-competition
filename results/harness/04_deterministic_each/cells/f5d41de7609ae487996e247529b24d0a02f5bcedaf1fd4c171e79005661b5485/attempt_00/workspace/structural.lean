theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  subst digits_to_num
  intro d e f h i
  let N (a : Fin 9 → ℤ) := ∑ j : Fin 9, a j * 10 ^ j.1
  have hr (a b : Fin 9 → ℤ) (h : relation a b) (j : Fin 9) :
      7 ∣ b j * 10 ^ j.1 - a j * 10 ^ j.1 + N a := by
    have he (k : Fin 9) :
        (if k = j then b k else a k) * 10 ^ k.1 =
          (if k = j then b k * 10 ^ k.1 - a k * 10 ^ k.1 else 0) + a k * 10 ^ k.1 := by
      split_ifs <;> simp
    simpa only [he, Finset.sum_add_distrib, Finset.sum_ite_eq', Finset.mem_univ,
      if_true] using ((hrelation a b).mp h).2 j
  have hs := Finset.dvd_sum (fun j (_ : j ∈ Finset.univ) => hr d e h.1 j)
  simp only [Finset.sum_add_distrib, Finset.sum_sub_distrib, Finset.sum_const,
    Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul, Nat.cast_ofNat] at hs
  change 7 ∣ N e - N d + 9 * N d at hs
  have he : 7 ∣ N e + N d := by
    convert dvd_sub hs (dvd_mul_right 7 (N d)) using 1 <;> ring
  have hi : 7 ∣ (d i - f i) * 10 ^ i.1 := by
    convert dvd_sub he (dvd_add (hr d e h.1 i) (hr e f h.2 i)) using 1 <;> ring
  exact (show IsCoprime (7 : ℤ) 10 from ⟨3, -2, by decide⟩).pow_right.dvd_of_dvd_mul_right hi
