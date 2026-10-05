theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have step (d e : Fin 9 → ℤ) (h : relation d e) (i : Fin 9) :
      7 ∣ digits_to_num d + (e i - d i) * 10^i.1 := by
    have hi := ((hrelation d e).mp h).2 i
    convert hi using 1
    have hs : (∑ j : Fin 9, if j = i then (e j - d j) * (10 : ℤ)^j.1 else 0) =
        (e i - d i) * 10^i.1 := by simp
    rw [hdigits_to_num, ← hs]
    rw [← Finset.sum_add_distrib]
    apply Finset.sum_congr rfl
    intro j _
    dsimp only
    split_ifs <;> ring
  intro d e f h i
  have hs := Finset.dvd_sum (s := Finset.univ) (fun j _ => step d e h.1 j)
  have he : 7 ∣ digits_to_num d + digits_to_num e := by
    simp only [Finset.sum_add_distrib, Finset.sum_const, Finset.card_univ,
      Fintype.card_fin, Int.nsmul_eq_mul, Nat.cast_ofNat, sub_mul,
      Finset.sum_sub_distrib] at hs
    have hd := congrFun hdigits_to_num d
    have he := congrFun hdigits_to_num e
    rw [← hd, ← he] at hs
    omega
  have hh := dvd_sub (dvd_add (step d e h.1 i) (step e f h.2 i)) he
  have hm : 7 ∣ (d i - f i) * (10 : ℤ)^i.1 := by
    convert dvd_neg.mpr hh using 1 <;> ring
  have hp : Prime (7 : ℤ) := Int.prime_iff_natAbs_prime.mpr (by decide)
  rcases hp.dvd_mul.mp hm with hh | hh
  · exact hh
  · have hn := hp.dvd_of_dvd_pow hh
    norm_num at hn