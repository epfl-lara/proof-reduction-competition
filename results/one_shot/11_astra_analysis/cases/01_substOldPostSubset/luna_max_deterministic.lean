open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  induction post <;> simp_all [substOld, Imperative.HasVarsPure.getVars,
    Lambda.LExpr.LExpr.getVars]
  case fvar => simp [List.Subset]
  case ite cih tih eih =>
    repeat' apply List.Subset.app
    all_goals
      apply List.Subset.trans
      · assumption
      · intros x hx
        grind
        all_goals cases hx <;> simp_all
  case quant trih eih =>
    repeat' apply List.Subset.app
    all_goals
      apply List.Subset.trans
      · assumption
      · intros x hx
        simp_all
        all_goals cases hx <;> simp_all
  case eq ih1 ih2 =>
    repeat' apply List.Subset.app
    all_goals
      apply List.Subset.trans
      · assumption
      · intros x hx
        simp_all
        all_goals cases hx <;> simp_all
  case app ih1 ih2 =>
    split
    · split
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        simp_all
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        exact ih2 Hin
    · simp only [imp_false] at *
      apply List.Subset.app
      · apply List.Subset.trans ih1
        intros x hx
        grind
        all_goals cases hx <;> simp_all
      · apply List.Subset.trans ih2
        intros x hx
        simp_all
        all_goals cases hx <;> simp_all
