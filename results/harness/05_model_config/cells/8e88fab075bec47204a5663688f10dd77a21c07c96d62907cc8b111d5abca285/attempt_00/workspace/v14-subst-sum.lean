theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  subst digits_to_num
  let N (a : Fin 9 → ℤ) : ℤ := ∑ i, a i * 10 ^ i.1
  have swap (a b : Fin 9 → ℤ) (i : Fin 9) :
      (∑ j, (if j = i then b j else a j) * 10 ^ j.1) =
        b i * 10 ^ i.1 - a i * 10 ^ i.1 + N a := by
    apply eq_add_of_sub_eq
    simp only [N, ← Finset.sum_sub_distrib, ite_mul, ite_sub,
      sub_self, Finset.sum_ite_eq', Finset.mem_univ, ite_true]
  intro d e f h i
  have hd := ((hrelation d e).mp h.1).2
  have he := ((hrelation e f).mp h.2).2
  simp only [swap] at hd he
  have hs : 7 ∣ N e - N d + 9 * N d := by
    simpa only [N, Finset.sum_add_distrib, Finset.sum_sub_distrib,
      Fin.sum_const, Int.nsmul_eq_mul, Nat.cast_ofNat] using (Finset.dvd_sum (fun j (_ : j ∈ Finset.univ) => hd j))
  have hc : IsCoprime (7 : ℤ) 10 := ⟨3, -2, rfl⟩
  apply (hc.pow_right (n := i.1)).dvd_of_dvd_mul_right
  convert dvd_sub hs (dvd_add (dvd_add (hd i) (he i))
    (dvd_mul_right (7 : ℤ) (N d))) using 1 <;> ring1
