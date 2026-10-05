open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  induction post <;> simp [substOld]
  case fvar =>
    intros x Hin
    simp_all
  case op | const | bvar =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
  case abs ih => exact ih
  case ite cih tih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · apply List.Subset.trans
      apply cih <;> assumption
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    apply List.Subset.app
    · apply List.Subset.trans
      apply tih <;> assumption
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    · apply List.Subset.trans
      apply eih <;> assumption
      intros x Hin
      simp_all
  case app ih1 ih2 =>
    split
    · split
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars, List.Subset]
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars, List.Subset]
    · simp only [Imperative.HasVarsPure.getVars, imp_false, Lambda.LExpr.LExpr.getVars] at *
      apply List.Subset.app
      · apply List.Subset.trans
        apply ih1 <;> assumption
        intros x Hin
        simp_all
        cases Hin <;> simp_all
      · apply List.Subset.trans
        apply ih2 <;> assumption
        intros x Hin
        simp_all
  case quant ih1 ih2 | eq ih1 ih2 =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · apply List.Subset.trans
      apply ih1 <;> assumption
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    · apply List.Subset.trans
      apply ih2 <;> assumption
      intros x Hin
      simp_all