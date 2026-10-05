theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have step (d e : Fin 9 → ℤ) (h : relation d e) (i : Fin 9) :
      7 ∣ digits_to_num d + (e i - d i) * 10^i.1 := by
    have eqn : digits_to_num (fun j => if j = i then e j else d j) =
        digits_to_num d + (e i - d i) * 10^i.1 := by
      rw [hdigits_to_num]
      dsimp only
      have : (fun j : Fin 9 => (if j = i then e j else d j) * 10^j.1) =
          (fun j => d j * 10^j.1 + if j = i then (e j - d j) * 10^j.1 else 0) := by
        funext j
        split_ifs <;> ring
      rw [this, Finset.sum_add_distrib]
      simp
    rw [← eqn]
    exact ((hrelation d e).mp h).2 i
  intro d e f h i
  have hs := Finset.dvd_sum (s := Finset.univ) (fun j _ => step d e h.1 j)
  have sum_eq : (∑ j : Fin 9, (digits_to_num d + (e j - d j) * 10^j.1)) =
      8 * digits_to_num d + digits_to_num e := by
    simp only [sub_mul, Finset.sum_add_distrib, Finset.sum_sub_distrib,
      Finset.sum_const, Finset.card_univ, Fintype.card_fin, nsmul_eq_mul]
    rw [hdigits_to_num]
    ring
  rw [sum_eq] at hs
  have ht : 7 ∣ (d i - f i) * 10^i.1 := by
    have := dvd_sub (dvd_sub hs (step d e h.1 i)) (step e f h.2 i)
    have he : 8 * digits_to_num d + digits_to_num e -
        (digits_to_num d + (e i - d i) * 10^i.1) -
        (digits_to_num e + (f i - e i) * 10^i.1) =
        (d i - f i) * 10^i.1 + 7 * digits_to_num d := by ring
    rw [he] at this
    simpa only [add_sub_cancel_right] using dvd_sub this (dvd_mul_right 7 (digits_to_num d))
  have hp : Prime (7 : ℤ) := Int.prime_iff_natAbs_prime.mpr (by decide)
  exact (hp.dvd_mul.mp ht).resolve_right (fun hn => by
    have := hp.dvd_of_dvd_pow hn
    norm_num at this)
