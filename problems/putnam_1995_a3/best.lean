-- Warm-up problem: putnam_1995_a3
-- Variant: best; primary Lean version: v4.25.0
-- Target starts at the TARGET DECLARATION marker below.
-- Source context: benchmark header
-- Proof provenance and scores: ../manifest.json

import Mathlib
import Aesop

-- Match the local evaluator elaboration settings; no heartbeat measurement here.
set_option maxHeartbeats 0
set_option Elab.async false

set_option maxHeartbeats 0

open Filter Topology Real



-- TARGET DECLARATION BEGIN: putnam_1995_a3
theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have step {a b} (hab : relation a b) (i : Fin 9) :
      7 ∣ b i * 10 ^ i.1 - a i * 10 ^ i.1 + digits_to_num a := by
    convert (hrelation a b).mp hab |>.2 i using 1
    symm
    apply sub_eq_iff_eq_add.mp
    rw [hdigits_to_num, ← Finset.sum_sub_distrib]
    simp only [ite_mul, ite_sub,
      sub_self, Fintype.sum_ite_eq']
  have hs := Finset.dvd_sum (s := Finset.univ) (fun i _ => step h.1 i)
  simp only [Finset.sum_add_distrib, Finset.sum_sub_distrib, Fin.sum_const,
    ← congrFun hdigits_to_num e, ← congrFun hdigits_to_num d] at hs
  intro i
  apply (show IsCoprime (7 : ℤ) 10 from ⟨3, -2, by decide⟩).pow_right (n := i.1) |>.dvd_of_dvd_mul_right
  convert dvd_sub (dvd_sub hs (dvd_add (step h.1 i) (step h.2 i)))
    ⟨digits_to_num d, rfl⟩ using 1 <;> ring
-- TARGET DECLARATION END: putnam_1995_a3
