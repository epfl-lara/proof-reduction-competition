open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have H {A B C D E : List CoreIdent} : C ⊆ HAppend.hAppend D E → A ⊆ HAppend.hAppend B E → HAppend.hAppend A C ⊆ HAppend.hAppend B D ++ E := by
    grind
  induction post
  iterate 4 apply List.subset_append_left
  assumption
  rotate_left
  unfold substOld
  split
  split
  apply List.subset_append_right
  apply List.subset_append_left
  rotate_left
  apply H
  assumption
  all_goals apply H <;> assumption