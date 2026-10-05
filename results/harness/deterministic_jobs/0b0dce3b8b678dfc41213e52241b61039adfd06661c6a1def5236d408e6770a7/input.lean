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
  refine ⟨_, rfl,
    updatedStatesInit (InitStatesLength Hinit)
      (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hup)
      (InitStatesNodup Hinit), ?_⟩
  have hlen := UpdateStatesLength Hup
  have hdisj : (ks.zip vs).unzip.1.Disjoint (ks'.zip vs').unzip.1 := by
    rw [List.unzip_zip hlen,
      List.unzip_zip (InitStatesLength Hinit)]
    intro k hk hk'
    simpa [InitStatesNotDefined Hinit k hk'] using
      UpdateStatesDefined Hup k hk
  rw [InitStatesUpdated Hinit, UpdateStatesUpdated Hup]
  simp [updatedStates, updatedStatesComm (σ := σ) hdisj]
  exact updatedStatesUpdate hlen (updatedStatesDefMonotone (UpdateStatesDefined' Hup))