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
  have Hlen := UpdateStatesLength Hup
  have Hlen' := InitStatesLength Hinit
  have Hnone := InitStatesNotDefined Hinit
  refine ⟨_, rfl, updatedStatesInit Hlen'
    (UpdateStatesNotDefMonotone' Hnone Hup) (InitStatesNodup Hinit), ?_⟩
  rw [InitStatesUpdated Hinit, UpdateStatesUpdated Hup]
  unfold updatedStates
  rw [updatedStatesComm]
  · exact updatedStatesUpdate Hlen
      (updatedStatesDefMonotone (UpdateStatesDefined' Hup))
  · rw [List.unzip_zip Hlen, List.unzip_zip Hlen']
    intro k hk hk'
    have Hsome := UpdateStatesDefined Hup k hk
    simpa [Hnone k hk'] using Hsome
