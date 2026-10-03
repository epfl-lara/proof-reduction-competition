open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have appendSub {a b c d : List Expression.Ident}
      (ha : a.Subset (c ++ [h1])) (hb : b.Subset (d ++ [h1])) :
      (a ++ b).Subset (c ++ d ++ [h1]) := by
    intro x hx
    simp only [List.mem_append] at hx
    rcases hx with hx | hx
    · have hx' := ha hx
      simp only [List.mem_append] at hx'
      rcases hx' with hc | hh
      · simp only [List.mem_append]
        exact Or.inl (Or.inl hc)
      · simp only [List.mem_append]
        exact Or.inr hh
    · have hx' := hb hx
      simp only [List.mem_append] at hx'
      rcases hx' with hd | hh
      · simp only [List.mem_append]
        exact Or.inl (Or.inr hd)
      · simp only [List.mem_append]
        exact Or.inr hh
  have appendSub3 {a b c d e f : List Expression.Ident}
      (ha : a.Subset (d ++ [h1])) (hb : b.Subset (e ++ [h1]))
      (hc : c.Subset (f ++ [h1])) :
      (a ++ b ++ c).Subset (d ++ e ++ f ++ [h1]) := by
    intro x hx
    simp only [List.mem_append] at hx ⊢
    rcases hx with hx | hx
    · rcases hx with hx | hx
      · have hy := ha hx
        simp only [List.mem_append] at hy
        rcases hy with hy | hy
        · exact Or.inl (Or.inl (Or.inl hy))
        · exact Or.inr hy
      · have hy := hb hx
        simp only [List.mem_append] at hy
        rcases hy with hy | hy
        · exact Or.inl (Or.inl (Or.inr hy))
        · exact Or.inr hy
    · have hy := hc hx
      simp only [List.mem_append] at hy
      rcases hy with hy | hy
      · exact Or.inl (Or.inr hy)
      · exact Or.inr hy
  induction post <;> simp [substOld]
  case fvar =>
    intro x Hin
    simp_all [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
  case op =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
  case const =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
  case bvar =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
  case abs ih => exact ih
  case ite cih tih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    simpa [List.append_assoc] using appendSub3 cih tih eih
  case app ih1 ih2 =>
    split
    · split
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intro x Hin
        simp_all
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intro x Hin
        simp_all
    · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
      simpa [List.append_assoc] using appendSub ih1 ih2
  case quant trih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    simpa [List.append_assoc] using appendSub trih eih
  case eq ih1 ih2 =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    simpa [List.append_assoc] using appendSub ih1 ih2
