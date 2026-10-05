open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident} (h : a ⊆ c) (k : b ⊆ d) :
      a ++ b ⊆ c ++ d :=
    List.append_subset.mpr
      ⟨List.subset_append_of_subset_left _ h, List.subset_append_of_subset_right _ k⟩
  intro h
  induction h with
  | app hfn he hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl _
    · next hf =>
      cases hn .oldPred
      exact False.elim (hf _ _ _ rfl)
    · exact app ihfn ihe
  | _ => repeat first | assumption | exact List.nil_subset _ | apply app