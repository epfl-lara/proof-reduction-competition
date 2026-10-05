theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  have swap (a b : Fin 9 → ℤ) (i : Fin 9) :
      digits_to_num (fun j => if j = i then b j else a j) =
        (b i - a i) * 10 ^ i.1 + digits_to_num a := by
    apply sub_eq_iff_eq_add.mp
    simp [hdigits_to_num, ← Finset.sum_sub_distrib, ← sub_mul, ite_sub, ite_mul]
  have H (a b : Fin 9 → ℤ) (h : relation a b) (i : Fin 9) :
      7 ∣ (b i - a i) * 10 ^ i.1 + digits_to_num a := by
    rw [← swap]
    exact ((hrelation a b).mp h).2 i
  intro d e f h i
  have hd := H d e h.1
  have he := H e f h.2
  have ht : 7 ∣ digits_to_num e - digits_to_num d + 9 * digits_to_num d := by
    simpa [hdigits_to_num, sub_mul, Finset.sum_add_distrib, Finset.sum_sub_distrib]
      using Finset.dvd_sum (fun j (_ : j ∈ Finset.univ) => hd j)
  have hn : 7 ∣ digits_to_num e + digits_to_num d := by
    convert dvd_sub ht (dvd_mul_right (7 : ℤ) (digits_to_num d)) using 1 <;> ring
  apply (show IsCoprime (7 : ℤ) 10 from ⟨3, -2, by decide⟩).pow_right.dvd_of_dvd_mul_right
    (z := (10 : ℤ) ^ i.1)
  convert dvd_sub hn (dvd_add (hd i) (he i)) using 1 <;> ring
