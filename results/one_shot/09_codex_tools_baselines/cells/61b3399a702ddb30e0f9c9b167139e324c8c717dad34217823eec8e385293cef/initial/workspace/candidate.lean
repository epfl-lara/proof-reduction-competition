theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := by
  intro Hup Hinit
  refine ⟨updatedStates σ ks' vs', rfl, ?_, ?_⟩
  have Hlen := InitStatesLength Hinit
  have Hnd := InitStatesNodup Hinit
  have Hnot := InitStatesNotDefined Hinit
  have Hdef := UpdateStatesDefined Hup
  induction Hup generalizing σ'' with
  | update_none =>
      constructor
      · exact updatedStatesInit Hlen Hnot Hnd
      · simpa [InitStatesUpdated Hinit] using (show UpdateStates σ [] [] σ'' from Hinit |> fun _ => by
          cases Hinit
          constructor)
  | @update_some _ σ x v σ₀ xs vs σ₁ h hs ih =>
      constructor
      · exact updatedStatesInit Hlen
          (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' Hnot hs) h) Hnd
      · apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')
        · simp [UpdateStateUpdated h, updatedStates]
          rw [← updatedStateComm']
          · have hd := UpdateStateDefined' h
            simp [isDefined, Option.isSome] at hd
            split at hd <;> simp_all
            next val heq =>
              apply updatedStateUpdate (v':=val)
              exact InitStatesSomeMonotone heq (updatedStatesInit Hlen (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' Hnot hs) h) Hnd)
          · rw [List.unzip_zip] <;> simp_all
            simp [isNotDefined, isDefined] at *
            intro Hin
            exact Hnot _ Hin
        · exact (ih Hinit (by simp [isDefined] at *; simp_all) (by simp_all)).2.2
