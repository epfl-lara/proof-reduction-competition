theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have hr {d e} (h : relation d e) i :
      7 ∣ e i * 10 ^ i.1 - d i * 10 ^ i.1 + digits_to_num d := by
    refine (((hrelation d e).mp h).2 i).trans (dvd_of_eq ?_)
    rw [← sub_eq_iff_eq_add, hdigits_to_num, ← Finset.sum_sub_distrib]
    simp only [ite_mul, ite_sub, sub_self, Fintype.sum_ite_eq']
  intro d e f h
  have hs := Finset.dvd_sum (s := Finset.univ) (fun i _ => hr h.1 i)
  simp only [Finset.sum_add_distrib, Finset.sum_sub_distrib, Fin.sum_const,
    Int.nsmul_eq_mul, ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d] at hs
  intro i
  apply ((show IsCoprime (7 : ℤ) 10 from ⟨3, -2, rfl⟩).pow_right
    (n := i.1)).dvd_of_dvd_mul_right
  refine (dvd_sub (dvd_sub (dvd_sub hs (dvd_mul_right 7 (digits_to_num d)))
    (hr h.1 i)) (hr h.2 i)).trans (dvd_of_eq ?_)
  ring1