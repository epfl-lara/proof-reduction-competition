theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := fun Hup Hinit => ⟨_, rfl, updatedStatesInit (InitStatesLength Hinit) (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hup) (InitStatesNodup Hinit), by
    cases InitStatesUpdated Hinit
    unfold updatedStates
    refine UpdateStatesUpdated Hup ▸ updatedStatesComm ?_ ▸ updatedStatesUpdate (UpdateStatesLength Hup) (updatedStatesDefMonotone (UpdateStatesDefined' Hup))
    simp [List.unzip_zip, UpdateStatesLength Hup, InitStatesLength Hinit]
    intro x h1 h2
    nomatch InitStatesNotDefined Hinit x h1 ▸ UpdateStatesDefined Hup x h2⟩