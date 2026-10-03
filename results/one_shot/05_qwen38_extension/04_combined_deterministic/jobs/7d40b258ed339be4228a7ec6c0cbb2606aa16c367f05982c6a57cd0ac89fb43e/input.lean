open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  induction post <;> simp [substOld]
  case fvar =>
    intros x Hin
    rename_i m name ty2
    simp at m
    simp at name
    simp at ty2

    simp_all
  case op =>
    intros x Hin
    rename_i m name ty2
    simp at m
    simp at name
    simp at ty2
    contradiction
  case const =>
    intros x Hin
    rename_i m name
    simp at m
    contradiction
  case bvar =>
    intros x Hin
    rename_i m d
    simp at m
    contradiction
  case abs ih =>
    exact ih
  case ite cih tih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    . apply List.Subset.trans
      apply cih <;> assumption
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    apply List.Subset.app
    . apply List.Subset.trans
      apply tih <;> assumption
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    . apply List.Subset.trans
      apply eih <;> assumption
      intros x Hin
      simp_all
  case app ih1 ih2 =>
    split
    . split
      . simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        simp_all
      . simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        exact ih2 Hin
    . simp only [Imperative.HasVarsPure.getVars, imp_false, Lambda.LExpr.LExpr.getVars] at *
      apply List.Subset.app
      . apply List.Subset.trans
        apply ih1 <;> assumption
        intros x Hin
        simp_all
        cases Hin <;> simp_all
      . apply List.Subset.trans
        apply ih2 <;> assumption
        intros x Hin
        simp_all
  case quant trih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    . apply List.Subset.trans
      apply trih <;> assumption
      intros x Hin
      rename_i m1 k1 ty1 trigger1 e1
      
      simp_all
      cases Hin <;> simp_all
    . apply List.Subset.trans
      apply eih <;> assumption
      intros x Hin
      simp_all
  case eq ih1 ih2 =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    . apply List.Subset.trans
      apply ih1 <;> assumption
      intros x Hin
      simp_all
      cases Hin <;> simp_all
    . apply List.Subset.trans
      apply ih2 <;> assumption
      intros x Hin
      simp_all