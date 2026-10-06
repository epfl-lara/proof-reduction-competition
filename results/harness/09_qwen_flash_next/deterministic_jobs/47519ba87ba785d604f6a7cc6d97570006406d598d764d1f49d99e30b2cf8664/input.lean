theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f ⟨hde, hef⟩
  have hde := ((hrelation d e).mp hde).2
  have hef := ((hrelation e f).mp hef).2
  let w : Fin 9 → ℤ := fun i => 10 ^ i.1
  have hN : ∀ x, digits_to_num x = ∑ i, x i * w i := congrFun hdigits_to_num
  have upd (x y : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j => if j = i then y j else x j) = digits_to_num x + (y i * w i - x i * w i) := by
    rw [hN, hN, ← Fintype.sum_ite_eq' i fun j => y j * w j - x j * w j, ← Finset.sum_add_distrib]
    exact Finset.sum_congr rfl fun j _ => by by_cases h : j = i <;> simp [h]
  have hd := fun i => (upd d e i) ▸ hde i
  have he := fun i => (upd e f i) ▸ hef i
  have hDE : 7 ∣ digits_to_num d + digits_to_num e := by
    refine (Int.dvd_self_mul_add (b := digits_to_num d)).mp ?_
    convert Finset.dvd_sum fun i _ => hd i using 1
    rw [Finset.sum_add_distrib, Finset.sum_sub_distrib, ← hN, ← hN, Finset.sum_const,
      Finset.card_univ, Fintype.card_fin]
    ring
  have hu : IsCoprime (7 : ℤ) (10 : ℤ) := by norm_num
  intro i

  refine (hu.pow_right (n := i)).dvd_of_dvd_mul_right ?_
  convert dvd_sub (dvd_sub hDE (hd i)) (he i) using 1
  ring