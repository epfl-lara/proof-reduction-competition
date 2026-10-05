open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  clear h
  apply List.Sublist.subset
  induction post <;> unfold extractOldExprVars <;> (try split) <;>
    repeat' first
    | assumption
    | apply List.nil_sublist
    | apply List.Sublist.append
    | apply List.Sublist.refl