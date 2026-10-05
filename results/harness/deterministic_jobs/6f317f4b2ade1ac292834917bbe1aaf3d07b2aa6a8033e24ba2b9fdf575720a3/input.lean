theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have step (a b : Fin 9 → ℤ) (h : relation a b) (i : Fin 9) :
      7 ∣ (b i - a i) * 10^i.1 + digits_to_num a := by
    have hs := (hrelation a b).mp h |>.2 i
    simp only [hdigits_to_num] at hs ⊢
    have eq : (∑ j : Fin 9, (if j = i then b j else a j) * 10^j.1) =
        (∑ j : Fin 9, a j * 10^j.1) + (b i - a i) * 10^i.1 := by
      calc
        _ = ∑ j : Fin 9, (a j * 10^j.1 + if j = i then (b j - a j) * 10^j.1 else 0) := by
          apply Finset.sum_congr rfl
          intro j _
          split <;> ring
        _ = _ := by rw [Finset.sum_add_distrib]; simp
    rw [eq] at hs
    rwa [add_comm]
  intro d e f h i
  have hd := step d e h.1
  have he := step e f h.2
  have hs := Finset.dvd_sum (s := Finset.univ) (fun j _ => hd j)
  have heq : (∑ j : Fin 9, ((e j - d j) * 10^j.1 + digits_to_num d)) =
      digits_to_num e + 8 * digits_to_num d := by
    simp only [sub_mul, Finset.sum_add_distrib, Finset.sum_sub_distrib,
      Finset.sum_const, Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul,
      Nat.cast_ofNat]
    rw [← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d]
    ring
  rw [heq] at hs
  have ht : 7 ∣ (f i - d i) * 10^i.1 := by
    convert dvd_add (dvd_sub (dvd_add (hd i) (he i)) hs)
      (dvd_mul_right 7 (digits_to_num d)) using 1 <;> ring
  have hp : Prime (7 : ℤ) := Int.prime_iff_natAbs_prime.mpr (by decide)
  have hn : ¬ (7 : ℤ) ∣ 10^i.1 := by
    intro hh
    have := hp.dvd_of_dvd_pow hh
    norm_num at this
  exact dvd_sub_comm.mp ((hp.dvd_mul.mp ht).resolve_right hn)