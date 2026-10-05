open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have appendMono {a b c : List Expression.Ident} (H : a ⊆ b) :
      a ++ c ⊆ b ++ c := by
    intro x hx
    simp only [List.mem_append] at hx ⊢
    rcases hx with hx | hx
    · exact Or.inl (H hx)
    · exact Or.inr hx
  have appendLeft {a b : List Expression.Ident} : a ⊆ a ++ b := by
    intro x hx
    exact List.mem_append.mpr (Or.inl hx)
  have appendRight {a b : List Expression.Ident} : b ⊆ a ++ b := by
    intro x hx
    exact List.mem_append.mpr (Or.inr hx)
  have appendFirst3 {a b c : List Expression.Ident} : a ⊆ a ++ b ++ c :=
    List.Subset.trans appendLeft (appendLeft (a := a ++ b) (b := c))
  have appendMiddle3 {a b c : List Expression.Ident} : b ⊆ a ++ b ++ c :=
    List.Subset.trans appendRight (appendLeft (a := a ++ b) (b := c))
  have appendLast3 {a b c : List Expression.Ident} : c ⊆ a ++ b ++ c :=
    appendRight (a := a ++ b) (b := c)
  induction post <;> simp [substOld]
  case fvar => intros x Hin; simp_all
  case op => exact List.Subset.empty
  case const => exact List.Subset.empty
  case bvar => intros x Hin; contradiction
  case abs ih => exact ih
  case ite cih tih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · exact List.Subset.trans cih (appendMono (appendFirst3 (a := _) (b := _) (c := _)))
    apply List.Subset.app
    · exact List.Subset.trans tih (appendMono (appendMiddle3 (a := _) (b := _) (c := _)))
    · exact List.Subset.trans eih (appendMono (appendLast3 (a := _) (b := _) (c := _)))
  case app ih1 ih2 =>
    split
    · split
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        simp_all
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
        intros x Hin
        exact ih2 Hin
    · simp only [Imperative.HasVarsPure.getVars, imp_false, Lambda.LExpr.LExpr.getVars] at *
      apply List.Subset.app
      · exact List.Subset.trans ih1 (appendMono appendLeft)
      · exact List.Subset.trans ih2 (appendMono appendRight)
  case quant trih eih =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · exact List.Subset.trans trih (appendMono appendLeft)
    · exact List.Subset.trans eih (appendMono appendRight)
  case eq ih1 ih2 =>
    simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars] at *
    apply List.Subset.app
    · exact List.Subset.trans ih1 (appendMono appendLeft)
    · exact List.Subset.trans ih2 (appendMono appendRight)
