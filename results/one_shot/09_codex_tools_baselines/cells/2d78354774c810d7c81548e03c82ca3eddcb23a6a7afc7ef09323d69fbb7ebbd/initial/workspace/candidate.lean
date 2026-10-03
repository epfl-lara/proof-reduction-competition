theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have ha := (hrelation d e).mp h.1 |>.2
  have hb := (hrelation e f).mp h.2 |>.2
  have expand (x y : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j => if j = i then y j else x j) =
        digits_to_num x + (y i - x i) * (10 : ℤ)^i.1 := by
    rw [hdigits_to_num, hdigits_to_num]
    simp only [Finset.sum_add_distrib]
    have hh : ∀ j : Fin 9, (if j = i then y j else x j) * (10 : ℤ)^j.1 =
        x j * (10 : ℤ)^j.1 + (if j = i then (y j - x j) * (10 : ℤ)^j.1 else 0) := by
      intro j
      split <;> simp_all <;> ring
    simp_rw [hh, Finset.sum_add_distrib, Finset.sum_ite_eq']
    simp
  have ha' : ∀ i, 7 ∣ (e i-d i)*(10:ℤ)^i.1 + digits_to_num d := by
    intro i
    have := ha i
    rw [expand d e i] at this
    have : digits_to_num d + (e i-d i)*(10:ℤ)^i.1 = (e i-d i)*(10:ℤ)^i.1 + digits_to_num d := by ring
    rwa [this]
  have hb' : ∀ i, 7 ∣ (f i-e i)*(10:ℤ)^i.1 + digits_to_num e := by
    intro i
    have := hb i
    rw [expand e f i] at this
    have : digits_to_num e + (f i-e i)*(10:ℤ)^i.1 = (f i-e i)*(10:ℤ)^i.1 + digits_to_num e := by ring
    rwa [this]
  have sumA : 7 ∣ ∑ i : Fin 9, (e i-d i)*(10:ℤ)^i.1 + 9*digits_to_num d := by
    have q : 7 ∣ ∑ i : Fin 9, ((e i-d i)*(10:ℤ)^i.1 + digits_to_num d) := Finset.dvd_sum fun i _ => ha' i
    convert q using 1 <;> simp [Finset.sum_add_distrib] <;> ring
  have numE : digits_to_num e = digits_to_num d + ∑ i : Fin 9, (e i-d i)*(10:ℤ)^i.1 := by
    rw [hdigits_to_num, hdigits_to_num]
    simp_rw [show ∀ i : Fin 9, e i*(10:ℤ)^i.1 = d i*(10:ℤ)^i.1 + (e i-d i)*(10:ℤ)^i.1 by intro i; ring]
    rw [Finset.sum_add_distrib]
  have both : 7 ∣ digits_to_num e + digits_to_num d := by
    rw [numE]
    have q := sumA
    have r : 7 ∣ 7*digits_to_num d := ⟨digits_to_num d, rfl⟩
    have := dvd_sub q r
    convert this using 1 <;> ring
  intro i
  have q := hb' i
  have r := both
  have s : 7 ∣ (f i-e i)*(10:ℤ)^i.1 - digits_to_num d := by
    have := dvd_sub q r
    convert this using 1 <;> ring
  have t := dvd_add s (ha' i)
  have u : (f i-e i)*(10:ℤ)^i.1 - digits_to_num d + ((e i-d i)*(10:ℤ)^i.1 + digits_to_num d) = (f i-d i)*(10:ℤ)^i.1 := by ring
  rw [u] at t
  have prime : (7:ℤ).Prime := by norm_num
  have notpow : ¬ (7:ℤ) ∣ (10:ℤ)^i.1 := by
    intro z
    have z' : (7:ℕ) ∣ (10:ℕ)^i.1 := by norm_cast at z ⊢
    have zz : (7:ℕ) ∣ 10 := Nat.Prime.dvd_of_dvd_pow (by norm_num) z'
    norm_num at zz
  have v : (7:ℤ) ∣ f i-d i ∨ (7:ℤ) ∣ (10:ℤ)^i.1 := prime.dvd_mul.mp t
  have w : (7:ℤ) ∣ f i-d i := v.resolve_right notpow
  simpa using dvd_neg.mpr w
