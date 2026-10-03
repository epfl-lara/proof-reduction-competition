theorem putnam_1995_a3
(relation : (Fin 9 → ℤ) → (Fin 9 → ℤ) → Prop)
(digits_to_num : (Fin 9 → ℤ) → ℤ)
(hdigits_to_num : digits_to_num = fun dig => ∑ i : Fin 9, (dig i) * 10^i.1)
(hrelation : ∀ d e : (Fin 9 → ℤ), relation d e ↔ (∀ i : Fin 9, d i < 10 ∧ d i ≥ 0 ∧ e i < 10 ∧ e i ≥ 0) ∧ (∀ i : Fin 9, 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j))))
: ∀ d e f : (Fin 9 → ℤ), ((relation d e) ∧ (relation e f)) → (∀ i : Fin 9, 7 ∣ d i - f i) := by
  intro d e f h
  have h₁ : relation d e := h.1
  have h₂ : relation e f := h.2
  have h₃ : ∀ (i : Fin 9), 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j)) := by
    exact (hrelation d e).mp h₁ |>.2
  have h₄ : ∀ (i : Fin 9), 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then f j else e j)) := by
    exact (hrelation e f).mp h₂ |>.2
  
  have h₅ : ∀ (i : Fin 9), 7 ∣ (e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d := by
    intro i
    have h₆ : 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then e j else d j)) := h₃ i
    have h₇ : (digits_to_num (fun j : Fin 9 => if j = i then e j else d j)) = digits_to_num d + (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
      calc
        (digits_to_num (fun j : Fin 9 => if j = i then e j else d j)) = ∑ j : Fin 9, (if j = i then e j else d j) * (10 : ℤ) ^ (j : ℕ) := by
          simp only [hdigits_to_num]
          
        _ = ∑ j : Fin 9, (if j = i then e j else d j) * (10 : ℤ) ^ (j : ℕ) := rfl
        _ = (∑ j : Fin 9, d j * (10 : ℤ) ^ (j : ℕ)) + (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
          calc
            (∑ j : Fin 9, (if j = i then e j else d j) * (10 : ℤ) ^ (j : ℕ)) = ∑ j : Fin 9, (d j * (10 : ℤ) ^ (j : ℕ) + (if j = i then (e j - d j) else 0) * (10 : ℤ) ^ (j : ℕ)) := by
              apply Finset.sum_congr rfl
              intro j _
              by_cases h : j = i
              · simp only [h, ↓reduceIte]
                <;> ring
              · simp only [h, ↓reduceIte, zero_mul, add_zero]
                
            _ = (∑ j : Fin 9, d j * (10 : ℤ) ^ (j : ℕ)) + ∑ j : Fin 9, (if j = i then (e j - d j) else 0) * (10 : ℤ) ^ (j : ℕ) := by
              rw [Finset.sum_add_distrib]
            _ = (∑ j : Fin 9, d j * (10 : ℤ) ^ (j : ℕ)) + (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by simp only [ite_mul, zero_mul, Finset.sum_ite_eq', Finset.mem_univ, ↓reduceIte]
              
              
        _ = digits_to_num d + (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
          simp only [hdigits_to_num]
          
    have h₈ : 7 ∣ digits_to_num d + (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
      rw [h₇] at h₆
      exact h₆
    
    have h₁₀ : (e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d = digits_to_num d + (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by ring
    rw [h₁₀]
    exact h₈
  
  have h₆ : ∀ (i : Fin 9), 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e := by
    intro i
    have h₇ : 7 ∣ (digits_to_num (fun j : Fin 9 => if j = i then f j else e j)) := h₄ i
    have h₈ : (digits_to_num (fun j : Fin 9 => if j = i then f j else e j)) = digits_to_num e + (f i - e i) * (10 : ℤ) ^ (i : ℕ) := by
      calc
        (digits_to_num (fun j : Fin 9 => if j = i then f j else e j)) = ∑ j : Fin 9, (if j = i then f j else e j) * (10 : ℤ) ^ (j : ℕ) := by
          simp only [hdigits_to_num]
          
        _ = ∑ j : Fin 9, (if j = i then f j else e j) * (10 : ℤ) ^ (j : ℕ) := rfl
        _ = (∑ j : Fin 9, e j * (10 : ℤ) ^ (j : ℕ)) + (f i - e i) * (10 : ℤ) ^ (i : ℕ) := by
          calc
            (∑ j : Fin 9, (if j = i then f j else e j) * (10 : ℤ) ^ (j : ℕ)) = ∑ j : Fin 9, (e j * (10 : ℤ) ^ (j : ℕ) + (if j = i then (f j - e j) else 0) * (10 : ℤ) ^ (j : ℕ)) := by
              apply Finset.sum_congr rfl
              intro j _
              by_cases h : j = i
              · simp only [h, ↓reduceIte]
                <;> ring
              · simp only [h, ↓reduceIte, zero_mul, add_zero]
                
            _ = (∑ j : Fin 9, e j * (10 : ℤ) ^ (j : ℕ)) + ∑ j : Fin 9, (if j = i then (f j - e j) else 0) * (10 : ℤ) ^ (j : ℕ) := by
              rw [Finset.sum_add_distrib]
            _ = (∑ j : Fin 9, e j * (10 : ℤ) ^ (j : ℕ)) + (f i - e i) * (10 : ℤ) ^ (i : ℕ) := by simp only [ite_mul, zero_mul, Finset.sum_ite_eq', Finset.mem_univ, ↓reduceIte]
              
              
        _ = digits_to_num e + (f i - e i) * (10 : ℤ) ^ (i : ℕ) := by
          simp only [hdigits_to_num]
          
    have h₉ : 7 ∣ digits_to_num e + (f i - e i) * (10 : ℤ) ^ (i : ℕ) := by
      rw [h₈] at h₇
      exact h₇
    
    have h₁₁ : (f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e = digits_to_num e + (f i - e i) * (10 : ℤ) ^ (i : ℕ) := by ring
    rw [h₁₁]
    exact h₉
  
  have h₇ : 7 ∣ digits_to_num e + digits_to_num d := by
    have h₈ : digits_to_num e = digits_to_num d + ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
      calc
        digits_to_num e = ∑ i : Fin 9, e i * (10 : ℤ) ^ (i : ℕ) := by exact congrFun hdigits_to_num e
        _ = ∑ i : Fin 9, (d i + (e i - d i)) * (10 : ℤ) ^ (i : ℕ) := by
          apply Finset.sum_congr rfl
          intro i _
          ring
        _ = ∑ i : Fin 9, (d i * (10 : ℤ) ^ (i : ℕ) + (e i - d i) * (10 : ℤ) ^ (i : ℕ)) := by
          apply Finset.sum_congr rfl
          intro i _
          ring
        _ = (∑ i : Fin 9, d i * (10 : ℤ) ^ (i : ℕ)) + ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
          rw [Finset.sum_add_distrib]
        _ = digits_to_num d + ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
          simp only [hdigits_to_num]
          
    
    have h₁₀ : 7 ∣ ∑ i : Fin 9, ((e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d) := by
      apply Finset.dvd_sum
      intro i _
      exact h₅ i
    have h₁₁ : ∑ i : Fin 9, ((e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d) = ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) + 9 * digits_to_num d := by
      calc
        ∑ i : Fin 9, ((e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d) = ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) + ∑ i : Fin 9, digits_to_num d := by
          rw [Finset.sum_add_distrib]
        _ = ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) + 9 * digits_to_num d := by
          simp only [Finset.sum_const, Finset.card_univ, Fintype.card_fin, Int.nsmul_eq_mul, Nat.cast_ofNat]
          
          
    have h₁₂ : 7 ∣ ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) + 9 * digits_to_num d := by
      rw [h₁₁] at h₁₀
      exact h₁₀
    have h₁₄ : digits_to_num e + digits_to_num d = 2 * digits_to_num d + ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) := by
      omega
    rw [h₁₄]
    
    have h₁₈ : (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) + 9 * digits_to_num d) = (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 9 * digits_to_num d := by ring
    rw [h₁₈] at h₁₂
    
    
    
    
    
    have h₁₉ : 7 ∣ (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 2 * digits_to_num d := by
      
      
      
      
      have h₂₁ : 7 ∣ 7 * digits_to_num d := by
        use digits_to_num d
        
      have h₂₃ : (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 2 * digits_to_num d = ((∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 9 * digits_to_num d) - 7 * digits_to_num d := by ring
      rw [h₂₃]
      exact dvd_sub h₁₂ h₂₁
    
    have h₂₁ : 2 * digits_to_num d + ∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ) = (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 2 * digits_to_num d := by ring
    rw [h₂₁]
    exact h₁₉
  
  have h₈ : ∀ (i : Fin 9), 7 ∣ (f i - d i) * (10 : ℤ) ^ (i : ℕ) := by
    intro i
    
    
    
    
    
    have h₁₂ : 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d := by
      
      
      have h₁₃ : 7 ∣ (f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e := h₆ i
      
      
      have h₁₅ : 7 ∣ ((f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e) - (digits_to_num e + digits_to_num d) := by
        exact dvd_sub h₁₃ h₇
      
      have h₁₆ : ((f i - e i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num e) - (digits_to_num e + digits_to_num d) = (f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d := by
        ring
      rw [h₁₆] at h₁₅
      exact h₁₅
    
    
    
    have h₁₅ : 7 ∣ (e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d := h₅ i
    
    have h₁₆ : 7 ∣ ((f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d) + ((e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d) := by
      exact dvd_add h₁₂ h₁₅
    
    have h₁₇ : ((f i - e i) * (10 : ℤ) ^ (i : ℕ) - digits_to_num d) + ((e i - d i) * (10 : ℤ) ^ (i : ℕ) + digits_to_num d) = (f i - d i) * (10 : ℤ) ^ (i : ℕ) := by
      ring
    rw [h₁₇] at h₁₆
    exact h₁₆
  
  have h₉ : ∀ (i : Fin 9), 7 ∣ d i - f i := by
    intro i
    have h₁₀ : 7 ∣ (f i - d i) * (10 : ℤ) ^ (i : ℕ) := h₈ i
    have h₁₁ : 7 ∣ (f i - d i) := by
      
      
      
      have h₁₃ : (7 : ℕ).Prime := by decide
      have h₁₄ : ¬(7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) := by
        
        intro h
        have h₁₅ : (7 : ℕ) ∣ (10 : ℕ) ^ (i : ℕ) := by
          norm_cast at h ⊢
          
        have h₁₆ : (7 : ℕ) ∣ 10 := by
          
          exact Nat.Prime.dvd_of_dvd_pow h₁₃ h₁₅
        norm_num at h₁₆
        
      
      
      
      
      
      
      have h₂₁ : (7 : ℤ) ∣ (f i - d i) ∨ (7 : ℤ) ∣ (10 : ℤ) ^ (i : ℕ) := by
        
        
        apply (Int.prime_iff_natAbs_prime.mpr (by decide)).dvd_mul.mp
        exact h₁₀
      cases h₂₁ with
      | inl h₂₁ =>
        exact h₂₁
      | inr h₂₁ =>
        exfalso
        exact h₁₄ h₂₁
    
    
    
    have h₁₄ : 7 ∣ -(f i - d i) := by
      exact dvd_neg.mpr h₁₁
    have h₁₅ : -(f i - d i) = d i - f i := by ring
    rw [h₁₅] at h₁₄
    exact h₁₄
  
  intro i
  exact h₉ i
