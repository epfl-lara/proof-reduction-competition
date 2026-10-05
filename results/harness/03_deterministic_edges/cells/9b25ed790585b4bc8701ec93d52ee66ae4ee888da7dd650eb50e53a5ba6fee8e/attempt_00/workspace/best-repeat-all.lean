open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  refine List.Sublist.subset ?_
  induction h
  case' app =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
  repeat' first
  | assumption
  | apply List.nil_sublist
  | apply List.Sublist.append
