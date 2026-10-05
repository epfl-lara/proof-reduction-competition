open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  clear h
  apply List.Sublist.subset
  induction post <;>
    repeat' first
    | assumption
    | apply List.nil_sublist
    | apply List.Sublist.append
    | unfold extractOldExprVars; split
    | apply List.Sublist.refl