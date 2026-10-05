open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  apply List.Sublist.subset
  induction h <;> first
  | exact List.nil_sublist _
  | assumption
  | exact List.Sublist.append ‹_› ‹_›
  | exact List.Sublist.append (List.Sublist.append ‹_› ‹_›) ‹_›
  | skip
  next hnfn hne hwf ih1 ih2 =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · next h =>
      cases hwf .oldPred
      exact False.elim (h _ _ _ rfl)
    · exact ih1.append ih2
