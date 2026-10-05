theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have change (a b : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j : Fin 9 => if j = i then b j else a j) =
        digits_to_num a + (b i - a i) * (10 : ℤ) ^ (i : ℕ) := by
    rw [hdigits_to_num]
    calc
      (∑ j : Fin 9, (if j = i then b j else a j) * (10 : ℤ) ^ (j : ℕ)) =
          ∑ j : Fin 9, (a j * (10 : ℤ) ^ (j : ℕ) +
            (if j = i then (b j - a j) else 0) * (10 : ℤ) ^ (j : ℕ)) := by
        apply Finset.sum_congr rfl
        intro j _
        by_cases hj : j = i <;> simp [hj] <;> ring
      _ = (∑ j : Fin 9, a j * (10 : ℤ) ^ (j : ℕ)) +
          ∑ j : Fin 9, (if j = i then (b j - a j) else 0) * (10 : ℤ) ^ (j : ℕ) :=
        Finset.sum_add_distrib
      _ = _ := by simp only [ite_mul, zero_mul, Finset.sum_ite_eq', Finset.mem_univ, ↓reduceIte]
  have hde := (hrelation d e).mp h.1 |>.2
  have hef := (hrelation e f).mp h.2 |>.2
  have h₁ : ∀ i : Fin 9, 7 ∣ (e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d := by
    intro i
    have := hde i
    rw [change d e i] at this
    convert this using 1 <;> ring
  have h₂ : ∀ i : Fin 9, 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e := by
    intro i
    have := hef i
    rw [change e f i] at this
    convert this using 1 <;> abel
  let A : ℤ := ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)
  have hsum : 7 ∣ A + 9 * digits_to_num d := by
    have hs := Finset.dvd_sum (s := Finset.univ) (fun i _ => h₁ i)
    simpa [A, Finset.sum_add_distrib] using hs
  have hnum : digits_to_num e = digits_to_num d + A := by
    rw [hdigits_to_num]
    dsimp [A]
    calc
      (∑ i : Fin 9, e i * (10 : ℤ) ^ (i : ℕ)) =
          ∑ i : Fin 9, (d i * (10 : ℤ) ^ (i : ℕ) + (e i - d i) * (10 : ℤ) ^ (i : ℕ)) := by
        apply Finset.sum_congr rfl
        intro i _
        ring
      _ = _ := by rw [Finset.sum_add_distrib]
  have h7d : 7 ∣ (7 : ℤ) * digits_to_num d := ⟨digits_to_num d, by ring⟩
  have hsum' : 7 ∣ A + 2 * digits_to_num d := by
    have := dvd_sub hsum h7d
    convert this using 1 <;> ring
  have htotal : 7 ∣ digits_to_num e + digits_to_num d := by
    rw [hnum]
    convert hsum' using 1 <;> ring
  have hprod : ∀ i : Fin 9, 7 ∣ (f i - d i) * (10 : ℤ) ^ (i : ℕ) := by
    intro i
    have hleft : 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d := by
      have := dvd_sub (h₂ i) htotal
      convert this using 1 <;> ring
    have := dvd_add hleft (h₁ i)
    convert this using 1 <;> ring
  intro i
  have hp : (7 : ℕ).Prime := by decide
  have hpow : ¬ (7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) := by
    intro h
    have hn : (7 : ℕ) ∣ 10 ^ (i : ℕ) := by norm_cast at h ⊢
    have : (7 : ℕ) ∣ 10 := Nat.Prime.dvd_of_dvd_pow hp hn
    norm_num at this
  have hsplit : (7 : ℤ) ∣ f i - d i ∨ (7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) := by
    exact (Int.prime_iff_natAbs_prime.mpr (by norm_num : Nat.Prime (Int.natAbs (7 : ℤ)))).dvd_mul.mp (hprod i)
  rcases hsplit with hdiv | hdiv
  · have hn : 7 ∣ -(f i - d i) := dvd_neg.mpr hdiv
    convert hn using 1 <;> ring
  · exact (False.elim (hpow hdiv))