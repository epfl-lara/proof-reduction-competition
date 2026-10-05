open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  induction post <;> simp [substOld]
  case fvar | op | const | bvar =>
    intros x Hin
    simp_all [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
  case abs ih => exact ih
  case ite cih tih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · apply List.Subset.trans cih
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    apply List.Subset.app
    · apply List.Subset.trans tih
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    · apply List.Subset.trans eih
      intros x Hin
      simp_all
  case app ih1 ih2 =>
    split
    · split <;> (intros x Hin; simp_all [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars])
    · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
      apply List.Subset.app
      · apply List.Subset.trans ih1
        intros x Hin
        simp_all
        cases Hin <;> simp_all
      · apply List.Subset.trans ih2
        intros x Hin
        simp_all
  case quant trih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · apply List.Subset.trans trih
      intros x Hin
      simp_all [List.append_assoc]
      cases Hin <;> simp_all
    · apply List.Subset.trans eih
      intros x Hin
      simp_all
  case eq ih1 ih2 =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · apply List.Subset.trans ih1
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    · apply List.Subset.trans ih2
      intros x Hin
      simp_all
