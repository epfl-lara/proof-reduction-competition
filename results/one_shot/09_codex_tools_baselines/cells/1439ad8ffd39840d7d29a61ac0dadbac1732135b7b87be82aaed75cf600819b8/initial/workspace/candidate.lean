theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have hde := (hrelation d e).mp h.1 |>.2
  have hef := (hrelation e f).mp h.2 |>.2
  have perturb (a b : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j : Fin 9 => if j = i then b j else a j) =
        digits_to_num a + (b i - a i) * (10 : ℤ) ^ (i : ℕ) := by
    calc
      digits_to_num (fun j : Fin 9 => if j = i then b j else a j) =
          ∑ j : Fin 9, (if j = i then b j else a j) * (10 : ℤ) ^ (j : ℕ) :=
            congrFun hdigits_to_num _
      _ = ∑ j : Fin 9, (a j * (10 : ℤ) ^ (j : ℕ) +
              (if j = i then b j - a j else 0) * (10 : ℤ) ^ (j : ℕ)) := by
            apply Finset.sum_congr rfl
            intro j hj
            by_cases q : j = i <;> simp [q] <;> ring
      _ = (∑ j : Fin 9, a j * (10 : ℤ) ^ (j : ℕ)) +
            (b i - a i) * (10 : ℤ) ^ (i : ℕ) := by
            rw [Finset.sum_add_distrib]
            simp
      _ = digits_to_num a + (b i - a i) * (10 : ℤ) ^ (i : ℕ) := by
            exact congrArg (fun x : ℤ => x + (b i - a i) * (10 : ℤ) ^ (i : ℕ))
              (congrFun hdigits_to_num a).symm
  have ha : ∀ i : Fin 9, 7 ∣ (e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d := by
    intro i
    have := hde i
    rw [perturb d e i] at this
    convert this using 1 <;> (try ring)
  have hb : ∀ i : Fin 9, 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e := by
    intro i
    have := hef i
    rw [perturb e f i] at this
    convert this using 1 <;> (try ring)
  have hsum : digits_to_num e = digits_to_num d +
      ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
    rw [hdigits_to_num]
    calc
      (∑ i : Fin 9, e i * (10 : ℤ) ^ (i : ℕ)) =
          ∑ i : Fin 9, (d i * (10 : ℤ) ^ (i : ℕ) +
            (e i - d i) * (10 : ℤ) ^ (i : ℕ)) := by
        apply Finset.sum_congr rfl
        intro i hi
        ring
      _ = _ := by
        rw [Finset.sum_add_distrib]
        exact congrArg (fun x : ℤ => x + ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ))
          (congrFun hdigits_to_num d).symm
  have hdiv : 7 ∣ ∑ i : Fin 9,
      ((e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d) :=
    Finset.dvd_sum fun i hi => ha i
  have hconstant : (∑ i : Fin 9,
      ((e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d)) =
      (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 9 * digits_to_num d := by
    rw [Finset.sum_add_distrib]
    simp
  have hsumdiv : 7 ∣ (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) +
      9 * digits_to_num d := by rw [← hconstant]; exact hdiv
  have hnediv : 7 ∣ digits_to_num e + digits_to_num d := by
    have q : 7 ∣ (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) +
        2 * digits_to_num d := by
      have := dvd_sub hsumdiv (show 7 ∣ 7 * digits_to_num d from ⟨digits_to_num d, by ring⟩)
      convert this using 1 <;> ring
    have heq : digits_to_num e + digits_to_num d =
        (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 2 * digits_to_num d := by
      rw [hsum]
      ring
    rw [heq]
    exact q
  intro i
  have q : 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d := by
    have := dvd_sub (hb i) hnediv
    convert this using 1 <;> (try ring)
  have q' : 7 ∣ (f i - d i) * (10 : ℤ) ^ (i : ℕ) := by
    have := dvd_add q (ha i)
    convert this using 1 <;> (try ring)
  have hp : (7 : ℕ).Prime := by decide
  have hpow : ¬ (7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) := by
    intro hh
    have hh' : (7 : ℕ) ∣ (10 : ℕ) ^ (i : ℕ) := by norm_cast at hh ⊢
    have hh'' : (7 : ℕ) ∣ 10 := Nat.Prime.dvd_of_dvd_pow hp hh'
    norm_num at hh''
  have hdvd : (7 : ℤ) ∣ f i - d i :=
    (Int.prime_iff_natAbs_prime.mpr (by decide)).dvd_mul.mp q' |>.resolve_right hpow
  exact (dvd_neg.mpr hdvd).trans (by norm_num)
