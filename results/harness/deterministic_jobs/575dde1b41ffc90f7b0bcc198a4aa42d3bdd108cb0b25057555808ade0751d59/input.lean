open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have append2 {a b c d : List Expression.Ident}
      (ha : a ⊆ c ++ [h1]) (hb : b ⊆ d ++ [h1]) :
      a ++ b ⊆ c ++ d ++ [h1] := by
    intro x hx
    rcases List.mem_append.mp hx with hx | hx
    · rcases List.mem_append.mp (ha hx) with hc | hh
      · simp [hc]
      · simp at hh; simp [hh]
    · rcases List.mem_append.mp (hb hx) with hd | hh
      · simp [hd]
      · simp at hh; simp [hh]
  have append3 {a b c d e f : List Expression.Ident}
      (ha : a ⊆ d ++ [h1]) (hb : b ⊆ e ++ [h1])
      (hc : c ⊆ f ++ [h1]) :
      a ++ b ++ c ⊆ d ++ e ++ f ++ [h1] := by
    intro x hx
    rcases List.mem_append.mp hx with hx | hx
    · rcases List.mem_append.mp hx with hx | hx
      · rcases List.mem_append.mp (ha hx) with hd | hh
        · simp [hd]
        · simp at hh; simp [hh]
      · rcases List.mem_append.mp (hb hx) with he | hh
        · simp [he]
        · simp at hh; simp [hh]
    · rcases List.mem_append.mp (hc hx) with hf | hh
      · simp [hf]
      · simp at hh; simp [hh]
  induction post <;> simp [substOld]
  case fvar => intros x Hin; simp_all
  case op => intros x Hin; simp_all
  case const => intros x Hin; simp_all
  case bvar => intros x Hin; simp_all
  case abs ih => exact ih
  case ite cih tih eih =>
    simp only [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    exact append3 cih tih eih
  case app ih1 ih2 =>
    split
    · split
      · simp only [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        simp_all
      · simp only [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        exact ih2 Hin
    · simp only [Imperative.HasVarsPure.getVars, imp_false, Lambda.LExpr.LExpr.getVars] at *
      exact append2 ih1 ih2
  case quant trih eih =>
    simp only [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    exact append2 trih eih
  case eq ih1 ih2 =>
    simp only [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    exact append2 ih1 ih2