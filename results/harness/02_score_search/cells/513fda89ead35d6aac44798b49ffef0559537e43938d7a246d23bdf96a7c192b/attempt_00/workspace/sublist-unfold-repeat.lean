open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  apply List.Sublist.subset
  induction h <;> unfold extractOldExprVars <;> (try split) <;>
    repeat first
    | assumption
    | exact List.nil_sublist _
    | apply List.Sublist.append
    | exact List.Sublist.refl _
