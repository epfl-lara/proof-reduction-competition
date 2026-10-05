open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  clear h
  apply List.Sublist.subset
  induction post <;> unfold extractOldExprVars <;>
    (try split) <;>
    solve
    | exact List.nil_sublist _
    | exact List.Sublist.refl _
    | assumption
    | apply List.Sublist.append <;>
        first | assumption | exact List.Sublist.append ‹_› ‹_›