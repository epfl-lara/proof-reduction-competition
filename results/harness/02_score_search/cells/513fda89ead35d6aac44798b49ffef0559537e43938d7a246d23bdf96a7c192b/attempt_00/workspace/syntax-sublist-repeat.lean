open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  clear h
  apply List.Sublist.subset
  induction post <;>
    repeat first | assumption | exact List.nil_sublist _ | apply List.Sublist.append
  next ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · exact List.nil_sublist _
    · exact ihfn.append ihe
