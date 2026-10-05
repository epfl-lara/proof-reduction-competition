open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have cat {a b c d : List CoreIdent} (h : a.Subset c)
      (k : b.Subset d) :=
    List.Subset.app (fun x hx => List.mem_append_left _ (h hx))
      (fun x hx => List.mem_append_right _ (k hx))
  intro h
  induction h with
  | const | op | bvar | fvar => simp [extractOldExprVars, Lambda.LExpr.LExpr.getVars]
  | abs _ ih => exact ih
  | quant _ _ ih₁ ih₂ => exact cat ih₁ ih₂
  | app _ _ hn ihfn ihe =>
    unfold extractOldExprVars
    split
    · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars, List.Subset]
    · next Hfalse =>
        exfalso
        cases hn .oldPred
        apply Hfalse
        rfl
    · exact cat ihfn ihe
  | ite _ _ _ ih₁ ih₂ ih₃ => exact cat (cat ih₁ ih₂) ih₃
  | eq _ _ ih₁ ih₂ => exact cat ih₁ ih₂
