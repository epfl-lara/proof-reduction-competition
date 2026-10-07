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
  have Hl := UpdateStatesLength Hup
  have Hl' := InitStatesLength Hinit
  exact ⟨_, ⟨rfl, updatedStatesInit Hl' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hup)
      (InitStatesNodup Hinit), by
    rewrite [InitStatesUpdated Hinit, UpdateStatesUpdated Hup]
    unfold updatedStates
    rewrite [updatedStatesComm (by rewrite [List.unzip_zip Hl, List.unzip_zip Hl']; exact fun _ hx hx' => by simpa [InitStatesNotDefined Hinit _ hx'] using UpdateStatesDefined Hup _ hx)]
    exact updatedStatesUpdate Hl (updatedStatesDefMonotone (UpdateStatesDefined' Hup))⟩⟩