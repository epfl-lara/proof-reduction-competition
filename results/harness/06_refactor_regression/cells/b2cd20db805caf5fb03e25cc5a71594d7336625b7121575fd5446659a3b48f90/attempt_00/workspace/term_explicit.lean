theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := by
  intro hu hi
  have hn := UpdateStatesNotDefMonotone' (InitStatesNotDefined hi) hu
  refine ⟨_, rfl, updatedStatesInit (InitStatesLength hi)
    hn (InitStatesNodup hi), ?_⟩
  rw [InitStatesUpdated hi, UpdateStatesUpdated hu]
  refine Eq.ndrec (motive := UpdateStates (updatedStates σ ks' vs') ks vs)
    (updatedStatesUpdate (UpdateStatesLength hu)
      (updatedStatesDefMonotone (UpdateStatesDefined' hu))) (updatedStatesComm ?_).symm
  rw [List.unzip_zip (UpdateStatesLength hu), List.unzip_zip (InitStatesLength hi)]
  intro k hk hk'
  exact Option.isSome_iff_ne_none.mp (UpdateStatesDefined' hu k hk) (hn k hk')
