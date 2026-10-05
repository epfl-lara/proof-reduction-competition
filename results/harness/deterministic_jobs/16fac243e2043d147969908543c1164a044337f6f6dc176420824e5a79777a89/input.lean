theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h i
  have repl (a b : Fin 9 → ℤ) (j : Fin 9) :
      (∑ k : Fin 9, if k = j then b k else a k) = b j - a j + ∑ k : Fin 9, a k := by
    rw [← sub_eq_iff_eq_add, ← Finset.sum_sub_distrib]
    simp only [ite_sub, sub_self, Finset.sum_ite_eq', Finset.mem_univ, if_true]
  have hr (a b : Fin 9 → ℤ) (h : relation a b) (j : Fin 9) :
      7 ∣ b j * 10 ^ j.1 - a j * 10 ^ j.1 + digits_to_num a := by
    simpa only [hdigits_to_num, ite_mul, repl] using ((hrelation a b).mp h).2 j
  have hs := Finset.dvd_sum (fun j (_ : j ∈ Finset.univ) => hr d e h.1 j)
  simp only [Finset.sum_add_distrib, Finset.sum_sub_distrib, Finset.sum_const,
    Finset.card_univ, Fintype.card_fin,
    ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d] at hs
  change 7 ∣ digits_to_num e - digits_to_num d + 9 * digits_to_num d at hs
  have he : 7 ∣ digits_to_num e + digits_to_num d := by omega
  have hi := dvd_add (hr e f h.2 i) (hr d e h.1 i)
  rw [add_add_add_comm, sub_add_sub_cancel, dvd_add_left he] at hi
  apply ((show IsCoprime (7 : ℤ) 10 from ⟨3, -2, rfl⟩).pow_right
    (n := i.1)).dvd_of_dvd_mul_right
  rwa [sub_mul, dvd_sub_comm]