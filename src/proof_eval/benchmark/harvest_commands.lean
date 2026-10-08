/- Parse source commands without elaborating or measuring their proofs.
   The caller supplies an explicit, already-built grammar environment. -/
import Lean

open Lean

partial def findKind (stx : Syntax) (kind : Name) : Option Syntax := do
  if stx.getKind == kind then return stx
  for arg in stx.getArgs do
    if let some found := findKind arg kind then return found
  none

partial def declaration? (stx : Syntax) : Option Syntax := do
  if stx.getKind == ``Parser.Command.theorem || stx.getKind == `lemma then return stx
  if stx.getKind == ``Parser.Command.declValSimple then failure
  for arg in stx.getArgs do
    if let some found := declaration? arg then return found
  none

partial def hasAtom (stx : Syntax) (value : String) : Bool :=
  stx.getAtomVal == value || stx.getArgs.any (hasAtom · value)

def scopeName (stx : Syntax) : Name := Id.run do
  for arg in stx.getArgs do
    if arg.isIdent then return arg.getId
  return .anonymous

def qualified (scopes : List Name) (decl : Name) : Name :=
  if decl.getRoot == `_root_ then decl.replacePrefix `_root_ .anonymous
  else scopes.reverse.foldl Name.append .anonymous |>.append decl

partial def openSyntax (ctx : Parser.ParserModuleContext) (stx : Syntax) :
    Parser.ParserModuleContext := Id.run do
  let mut ctx := ctx
  let simple := stx.getKind == ``Parser.Command.openSimple
  let isScoped := stx.getKind == ``Parser.Command.openScoped
  if simple || isScoped then
    let ids := if simple then stx[0].getArgs else stx[1].getArgs
    for id in ids do
      for ns in ResolveName.resolveNamespace ctx.env ctx.currNamespace ctx.openDecls id.getId do
        ctx := { ctx with env := Parser.parserExtension.activateScoped ctx.env ns }
        if simple then ctx := { ctx with openDecls := .simple ns [] :: ctx.openDecls }
  else
    for arg in stx.getArgs do ctx := openSyntax ctx arg
  return ctx

def harvestFile (env : Environment) (path : String) : IO Json := do
  let text ← IO.FS.readFile path
  let ctx := Parser.mkInputContext text path
  let (_, initial, headerMessages) ← Parser.parseHeader ctx
  let mut state := initial
  let mut pmctx : Parser.ParserModuleContext := { env, options := {} }
  let mut contexts : List Parser.ParserModuleContext := []
  let mut scopes : List Name := []
  let mut records : Array Json := #[]
  let mut errors := if headerMessages.hasErrors then 1 else 0
  repeat
    let (stx, next, messages) := Parser.parseCommand ctx pmctx state {}
    state := next
    if messages.hasErrors then errors := errors + 1
    if Parser.isTerminalCommand stx then break
    if !messages.hasErrors then
      if stx.getKind == ``Parser.Command.namespace then
        scopes := scopeName stx :: scopes
        contexts := pmctx :: contexts
        let ns := qualified scopes .anonymous
        pmctx := { pmctx with
          currNamespace := ns
          env := Parser.parserExtension.activateScoped pmctx.env ns }
      else if stx.getKind == ``Parser.Command.section then
        scopes := .anonymous :: scopes
        contexts := pmctx :: contexts
      else if stx.getKind == ``Parser.Command.end then
        scopes := scopes.drop 1
        if let old :: rest := contexts then
          pmctx := old
          contexts := rest
      else if stx.getKind == ``Parser.Command.open then
        pmctx := openSyntax pmctx stx
      else if let some decl := declaration? stx then
        if let some id := findKind decl ``Parser.Command.declId then
          if let some val := findKind decl ``Parser.Command.declValSimple then
            if let some start := stx.getPos? then
              if let some stop := stx.getTailPos? then
                if let some assign := val[0].getPos? then
                  if let some body := val[1].getPos? then
                    records := records.push <| Json.mkObj [
                      ("name", toJson (qualified scopes id[0].getId).toString),
                      ("start_byte", toJson start.byteIdx),
                      ("end_byte", toJson stop.byteIdx),
                      ("assignment_byte", toJson assign.byteIdx),
                      ("body_byte", toJson body.byteIdx),
                      ("kind", toJson (if decl.getKind == `lemma then "lemma" else "theorem")),
                      ("private", toJson (hasAtom stx "private")),
                      ("has_where", toJson (hasAtom val "where"))]
  return Json.mkObj [("path", toJson path), ("errors", toJson errors),
    ("records", toJson records)]

unsafe def main (args : List String) : IO Unit := do
  let some input := (args[0]? : Option String) | throw (IO.userError "Expected input JSON path")
  let spec ← IO.FS.readFile ⟨input⟩
  let spec ← IO.ofExcept (Json.parse spec)
  let imports ← IO.ofExcept ((spec.getObjVal? "imports").bind Json.getArr?)
  let paths ← IO.ofExcept ((spec.getObjVal? "paths").bind Json.getArr?)
  initSearchPath (← findSysroot)
  enableInitializersExecution
  let imports ← imports.mapM fun item => do
    let name ← IO.ofExcept item.getStr?
    pure ({ module := name.toName } : Import)
  let env ← importModules (loadExts := true) imports {}
  for item in paths do
    let path ← IO.ofExcept item.getStr?
    try
      IO.println (← harvestFile env path).compress
    catch err =>
      IO.println (Json.mkObj [("path", toJson path), ("error", toJson (toString err)),
        ("errors", toJson (1 : Nat)), ("records", toJson (#[] : Array Json))]).compress
