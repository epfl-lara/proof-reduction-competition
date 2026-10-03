theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have hreplace (x y : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j : Fin 9 => if j = i then y j else x j) =
        digits_to_num x + (y i - x i) * (10 : ℤ) ^ (i : ℕ) := by
    rw [hdigits_to_num]
    calc
      (∑ j : Fin 9, (if j = i then y j else x j) * (10 : ℤ) ^ (j : ℕ)) =
          ∑ j : Fin 9, (x j * (10 : ℤ) ^ (j : ℕ) +
            (if j = i then (y j - x j) else 0) * (10 : ℤ) ^ (j : ℕ)) := by
        apply Finset.sum_congr rfl
        intro j hj
        by_cases hji : j = i <;> simp [hji] <;> ring
      _ = (∑ j : Fin 9, x j * (10 : ℤ) ^ (j : ℕ)) +
          ∑ j : Fin 9, (if j = i then (y j - x j) else 0) * (10 : ℤ) ^ (j : ℕ) := by
        rw [Finset.sum_add_distrib]
      _ = (∑ j : Fin 9, x j * (10 : ℤ) ^ (j : ℕ)) +
          (y i - x i) * (10 : ℤ) ^ (i : ℕ) := by
        simp [Finset.sum_ite_eq']
  have hnum (x y : Fin 9 → ℤ) :
      digits_to_num y = digits_to_num x +
        ∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ) := by
    rw [hdigits_to_num]
    calc
      (∑ i : Fin 9, y i * (10 : ℤ) ^ (i : ℕ)) =
          ∑ i : Fin 9, (x i + (y i - x i)) * (10 : ℤ) ^ (i : ℕ) := by
        apply Finset.sum_congr rfl
        intro i hi
        ring
      _ = ∑ i : Fin 9, (x i * (10 : ℤ) ^ (i : ℕ) +
          (y i - x i) * (10 : ℤ) ^ (i : ℕ)) := by
        apply Finset.sum_congr rfl
        intro i hi
        ring
      _ = (∑ i : Fin 9, x i * (10 : ℤ) ^ (i : ℕ)) +
          ∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ) := by
        rw [Finset.sum_add_distrib]
  have aggregate (x y : Fin 9 → ℤ)
      (hxy : ∀ i : Fin 9, 7 ∣ digits_to_num (fun j : Fin 9 => if j = i then y j else x j)) :
      7 ∣ digits_to_num x + digits_to_num y := by
    have ht : ∀ i : Fin 9, 7 ∣ (y i - x i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num x := by
      intro i
      have hh := hxy i
      rw [hreplace x y i] at hh
      simpa [add_comm] using hh
    have hs : 7 ∣ ∑ i : Fin 9,
        ((y i - x i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num x) := by
      apply Finset.dvd_sum
      intro i hi
      exact ht i
    have hs' : 7 ∣ (∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ)) +
        9 * digits_to_num x := by
      have heq : (∑ i : Fin 9,
          ((y i - x i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num x)) =
          (∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ)) + 9 * digits_to_num x := by
        rw [Finset.sum_add_distrib]
        simp [Finset.sum_const, Finset.card_fin] <;> ring <;> norm_num
      rw [heq] at hs
      exact hs
    have hs2 : 7 ∣ (∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ)) +
        2 * digits_to_num x := by
      have h7x : 7 ∣ (7 : ℤ) * digits_to_num x := ⟨digits_to_num x, by ring⟩
      have heq : (∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ)) +
          2 * digits_to_num x =
          ((∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ)) +
            9 * digits_to_num x) - 7 * digits_to_num x := by ring
      rw [heq]
      exact dvd_sub hs' h7x
    rw [hnum x y]
    have heq : digits_to_num x + (digits_to_num x +
        ∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ)) =
        (∑ i : Fin 9, (y i - x i) * (10 : ℤ) ^ (i : ℕ)) + 2 * digits_to_num x := by ring
    rw [heq]
    exact hs2
  intro d e f h i
  have hde : ∀ i : Fin 9, 7 ∣ digits_to_num (fun j : Fin 9 => if j = i then e j else d j) :=
    ((hrelation d e).mp h.1).2
  have hef : ∀ i : Fin 9, 7 ∣ digits_to_num (fun j : Fin 9 => if j = i then f j else e j) :=
    ((hrelation e f).mp h.2).2
  have hsumde : 7 ∣ digits_to_num d + digits_to_num e := aggregate d e hde
  have hsumef : 7 ∣ digits_to_num e + digits_to_num f := aggregate e f hef
  have h1 : 7 ∣ (e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d := by
    have hh := hde i
    rw [hreplace d e i] at hh
    simpa [add_comm] using hh
  have h2 : 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e := by
    have hh := hef i
    rw [hreplace e f i] at hh
    simpa [add_comm] using hh
  have hsub : 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d := by
    have hh := dvd_sub h2 hsumde
    convert hh using 1 <;> ring
  have hprod : 7 ∣ (f i - d i) * (10 : ℤ) ^ (i : ℕ) := by
    have hh := dvd_add hsub h1
    convert hh using 1 <;> ring
  have hp : Nat.Prime 7 := by decide
  have hpow : ¬ (7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) := by
    intro hh
    have hn : (7 : ℕ) ∣ (10 : ℕ) ^ (i : ℕ) := by
      norm_cast at hh ⊢
      <;> simpa [Int.coe_nat_dvd_left] using hh
    have h7 : (7 : ℕ) ∣ 10 := hp.dvd_of_dvd_pow hn
    norm_num at h7
  have hfactor := (Int.prime_iff_natAbs_prime.mpr (by decide)).dvd_mul.mp hprod
  have hfd : (7 : ℤ) ∣ f i - d i := by
    rcases hfactor with hfactor | hfactor
    · exact hfactor
    · exact False.elim (hpow hfactor)
  have hneg : (7 : ℤ) ∣ -(f i - d i) := dvd_neg.mpr hfd
  convert hneg using 1 <;> ring
