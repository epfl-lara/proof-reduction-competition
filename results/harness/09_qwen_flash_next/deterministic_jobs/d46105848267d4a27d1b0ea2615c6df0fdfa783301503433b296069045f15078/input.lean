theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f ⟨hde, hef⟩
  obtain ⟨_, hde⟩ := (hrelation d e).mp hde
  obtain ⟨_, hef⟩ := (hrelation e f).mp hef
  let p : Fin 9 → ℤ := fun i => (10 : ℤ) ^ (i : ℕ)
  have hN (x : Fin 9 → ℤ) : digits_to_num x = ∑ i : Fin 9, x i * p i :=
    congrFun hdigits_to_num x
  have upd (x y : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j => if j = i then y j else x j)
        = digits_to_num x + (y i - x i) * p i := by
    have h : (fun j => (if j = i then y j else x j) * p j)
        = (fun j => x j * p j + if j = i then (y j - x j) * p j else 0) := by
      funext j
      by_cases hj : j = i
      · rw [if_pos hj, if_pos hj]; ring
      · rw [if_neg hj, if_neg hj, add_zero]
    rw [hN (fun j => if j = i then y j else x j), hN x, h, Finset.sum_add_distrib, Fintype.sum_ite_eq']
  have hd (i : Fin 9) : 7 ∣ digits_to_num d + (e i - d i) * p i := (upd d e i) ▸ hde i
  have he (i : Fin 9) : 7 ∣ digits_to_num e + (f i - e i) * p i := (upd e f i) ▸ hef i
  have hs : ∑ i : Fin 9, (digits_to_num d + (e i - d i) * p i)
      = 7 * digits_to_num d + (digits_to_num d + digits_to_num e) := by
    rw [Finset.sum_add_distrib]
    simp only [sub_mul, Finset.sum_sub_distrib, ← hN]
    simp only [Finset.sum_const, Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul, Nat.cast_ofNat]
    ring
  have hAB : 7 ∣ digits_to_num d + digits_to_num e := by
    have h := hs ▸ Finset.dvd_sum fun i _ => hd i
    exact Int.dvd_self_mul_add.mp h
  have hu : IsCoprime (7 : ℤ) (10 : ℤ) := ⟨3, -2, by decide⟩
  intro i
  have hz : 7 ∣ (d i - f i) * p i := by
    have h : (d i - f i) * p i
        = (digits_to_num d + digits_to_num e) - (digits_to_num d + (e i - d i) * p i)
          - (digits_to_num e + (f i - e i) * p i) := by ring
    rw [h]
    exact dvd_sub (dvd_sub hAB (hd i)) (he i)
  exact (hu.pow_right (n := (i : ℕ))).dvd_of_dvd_mul_right hz