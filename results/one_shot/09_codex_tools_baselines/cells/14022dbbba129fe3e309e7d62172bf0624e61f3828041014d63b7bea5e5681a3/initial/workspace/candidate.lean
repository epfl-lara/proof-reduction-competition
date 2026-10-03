theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h i
  have hchange : ∀ x y : Fin 9 → ℤ, ∀ k : Fin 9,
      digits_to_num (fun j => if j = k then y j else x j) =
        digits_to_num x + (y k - x k) * (10 : ℤ) ^ (k : ℕ) := by
    intro x y k
    simp only [hdigits_to_num]
    calc
      (∑ j : Fin 9, (if j = k then y j else x j) * (10 : ℤ) ^ (j : ℕ)) =
          ∑ j : Fin 9, (x j * (10 : ℤ) ^ (j : ℕ) +
            (if j = k then (y j - x j) else 0) * (10 : ℤ) ^ (j : ℕ)) := by
        apply Finset.sum_congr rfl
        intro j _
        by_cases hj : j = k <;> simp [hj] <;> ring
      _ = (∑ j : Fin 9, x j * (10 : ℤ) ^ (j : ℕ)) +
          ∑ j : Fin 9, (if j = k then (y j - x j) else 0) * (10 : ℤ) ^ (j : ℕ) := by
        rw [Finset.sum_add_distrib]
      _ = (∑ j : Fin 9, x j * (10 : ℤ) ^ (j : ℕ)) +
          (y k - x k) * (10 : ℤ) ^ (k : ℕ) := by
        simp [Finset.sum_ite_eq', Finset.mem_univ]
  have ha : ∀ k : Fin 9, 7 ∣ (e k - d k) * (10 : ℤ) ^ (k : ℕ) + digits_to_num d := by
    intro k
    have := (hrelation d e).mp h.1 |>.2 k
    rw [hchange] at this
    convert this using 1 <;> ring
  have hb : ∀ k : Fin 9, 7 ∣ (f k - e k) * (10 : ℤ) ^ (k : ℕ) + digits_to_num e := by
    intro k
    have := (hrelation e f).mp h.2 |>.2 k
    rw [hchange] at this
    convert this using 1 <;> ring
  have hnum : digits_to_num e = digits_to_num d +
      ∑ k : Fin 9, (e k - d k) * (10 : ℤ) ^ (k : ℕ) := by
    simp only [hdigits_to_num]
    calc
      (∑ k : Fin 9, e k * (10 : ℤ) ^ (k : ℕ)) =
          ∑ k : Fin 9, (d k * (10 : ℤ) ^ (k : ℕ) +
            (e k - d k) * (10 : ℤ) ^ (k : ℕ)) := by
        apply Finset.sum_congr rfl
        intro k _
        ring
      _ = (∑ k : Fin 9, d k * (10 : ℤ) ^ (k : ℕ)) +
          ∑ k : Fin 9, (e k - d k) * (10 : ℤ) ^ (k : ℕ) := by
        rw [Finset.sum_add_distrib]
  let S : ℤ := ∑ k : Fin 9, (e k - d k) * (10 : ℤ) ^ (k : ℕ)
  have hsum : 7 ∣ S + 9 * digits_to_num d := by
    have hs : 7 ∣ ∑ k : Fin 9,
        ((e k - d k) * (10 : ℤ) ^ (k : ℕ) + digits_to_num d) :=
      Finset.dvd_sum fun k _ => ha k
    have heq : (∑ k : Fin 9,
        ((e k - d k) * (10 : ℤ) ^ (k : ℕ) + digits_to_num d)) =
        S + 9 * digits_to_num d := by
      simp [S, Finset.sum_add_distrib]
    rw [heq] at hs
    exact hs
  have hde : 7 ∣ digits_to_num e + digits_to_num d := by
    have hdvd : 7 ∣ (S + 9 * digits_to_num d) - 7 * digits_to_num d :=
      dvd_sub hsum (⟨digits_to_num d, by ring⟩)
    have heq : (S + 9 * digits_to_num d) - 7 * digits_to_num d =
      digits_to_num e + digits_to_num d := by
      rw [hnum]
      dsimp [S]
      ring
    rw [heq] at hdvd
    exact hdvd
  have hprod : 7 ∣ (f i - d i) * (10 : ℤ) ^ (i : ℕ) := by
    have hx : 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d := by
      have := dvd_sub (hb i) hde
      convert this using 1 <;> ring
    have hy := dvd_add hx (ha i)
    convert hy using 1 <;> ring
  have hpow : ¬ (7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) := by
    intro hh
    have hn : (7 : ℕ) ∣ (10 : ℕ) ^ (i : ℕ) := by
      norm_cast at hh ⊢
      simpa [Int.coe_nat_dvd_left] using hh
    have hp : (7 : ℕ).Prime := by decide
    have : (7 : ℕ) ∣ 10 := hp.dvd_of_dvd_pow hn
    norm_num at this
  have hdiv : (7 : ℤ) ∣ f i - d i := by
    have hp : (7 : ℕ).Prime := by decide
    have hor : (7 : ℤ) ∣ f i - d i ∨ (7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) :=
      (Int.prime_iff_natAbs_prime.mpr (by decide)).dvd_mul.mp hprod
    exact hor.resolve_right hpow
  have hn := dvd_neg.mpr hdiv
  convert hn using 1 <;> ring
