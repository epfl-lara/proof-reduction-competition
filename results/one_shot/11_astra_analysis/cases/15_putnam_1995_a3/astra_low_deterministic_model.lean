theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have step (a b : Fin 9 → ℤ) (h : relation a b) (i : Fin 9) :
      7 ∣ (b i - a i) * (10 : ℤ)^i.1 + digits_to_num a := by
    have eqn : digits_to_num (fun j => if j = i then b j else a j) =
        (b i - a i) * (10 : ℤ)^i.1 + digits_to_num a := by
      rw [hdigits_to_num]
      change (∑ j : Fin 9, (if j = i then b j else a j) * (10 : ℤ)^j.1) = _
      calc
        _ = ∑ j : Fin 9, ((if j = i then (b j - a j) * (10 : ℤ)^j.1 else 0) + a j * (10 : ℤ)^j.1) := by
          apply Finset.sum_congr rfl
          intro j _
          split_ifs <;> ring
        _ = _ := by simp only [Finset.sum_add_distrib, Finset.sum_ite_eq', Finset.mem_univ, if_true]
    rw [← eqn]
    exact ((hrelation a b).mp h).2 i
  intro d e f h
  have hd := step d e h.1
  have he := step e f h.2
  have hs : 7 ∣ digits_to_num e + digits_to_num d := by
    have hh := Finset.dvd_sum (s := Finset.univ) (fun i _ => hd i)
    have eqn : (∑ i : Fin 9, ((e i - d i) * (10 : ℤ)^i.1 + digits_to_num d)) =
        digits_to_num e - digits_to_num d + 9 * digits_to_num d := by
      simp only [Finset.sum_add_distrib, sub_mul, Finset.sum_sub_distrib,
        Finset.sum_const, Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul, Nat.cast_ofNat]
      rw [hdigits_to_num]
    rw [eqn] at hh
    omega
  intro i
  have hm := dvd_sub (dvd_add (hd i) (he i)) hs
  have eqn : ((e i - d i) * (10 : ℤ)^i.1 + digits_to_num d) +
      ((f i - e i) * (10 : ℤ)^i.1 + digits_to_num e) -
      (digits_to_num e + digits_to_num d) = (f i - d i) * (10 : ℤ)^i.1 := by ring
  rw [eqn] at hm
  have hn : ¬ (7 : ℤ) ∣ (10 : ℤ)^i.1 := by
    intro hh
    have hh' : (7 : ℕ) ∣ (10 : ℕ)^i.1 := by exact_mod_cast hh
    have := Nat.Prime.dvd_of_dvd_pow (by decide : Nat.Prime 7) hh'
    norm_num at this
  have hf := ((Int.prime_iff_natAbs_prime.mpr (by decide) : Prime (7 : ℤ)).dvd_mul.mp hm).resolve_right hn
  exact dvd_sub_comm.mp hf
