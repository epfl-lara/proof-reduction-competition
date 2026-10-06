theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := fun Hup Hinit =>
  have Hl := InitStatesLength Hinit
  have Hnd := InitStatesNodup Hinit
  ⟨_, rfl, updatedStatesInit Hl (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hup) Hnd, by
    induction Hup
    next =>
      cases InitStatesUpdated Hinit
      constructor
    next Hup Hups ih =>
      have Hnotdef := UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup
      refine .update_some ?_ (ih Hinit)
      simp [UpdateStateUpdated Hup, updatedStates]
      rcases Hup with ⟨Hold⟩
      rewrite [← updatedStateComm']
      . exact updatedStateUpdate (InitStatesSomeMonotone Hold (updatedStatesInit Hl Hnotdef Hnd))
      . rewrite [List.unzip_zip Hl]
        exact fun Hin => nomatch Hold ▸ Hnotdef _ Hin⟩