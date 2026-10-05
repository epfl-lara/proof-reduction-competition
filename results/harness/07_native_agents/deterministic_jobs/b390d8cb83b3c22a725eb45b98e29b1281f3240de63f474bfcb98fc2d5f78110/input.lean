open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have h : ∀ {a b c d t : List Expression.Ident}, a ⊆ b ++ t → c ⊆ d ++ t → a ++ c ⊆ b ++ d ++ t := by
    grind
  induction post
  case abs => assumption
  case quant ihtr ihe => exact h ihtr ihe
  case app ih1 ih2 =>
      unfold substOld
      split
      split
      apply List.subset_append_right
      apply List.subset_append_left
      exact h ih1 ih2
  case ite ihc iht ihf => exact h (h ihc iht) ihf
  case eq ih1 ih2 => exact h ih1 ih2
  all_goals apply List.subset_append_left