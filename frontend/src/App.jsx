// Holds the whole session state and the four workflow steps.
// Steps after Import stay locked until /configure succeeds.
import { useCallback, useEffect, useMemo, useState } from "react";
import { NetworkError, getLabels } from "./api.js";
import { defaultChoices, followScaling, setChoice } from "./choices.js";
import { fmtInt } from "./format.js";
import { LabelsContext, useLabels } from "./LabelsContext.jsx";
import EdaTab from "./tabs/EdaTab.jsx";
import ExportTab from "./tabs/ExportTab.jsx";
import ImportTab from "./tabs/ImportTab.jsx";
import PreprocessingTab from "./tabs/PreprocessingTab.jsx";

// The single exception to "all text comes from i18n.py": when the backend is
// unreachable, the labels themselves cannot be loaded.
const BOOT_NETWORK_ERROR = "The server could not be reached. Start the backend on port 8000, then try again.";
const BOOT_RETRY = "Retry";

const EMPTY = { sessionId: null, upload: null, config: null, eda: null, findings: [], choices: {},
                scaling: {}, applied: null };

export default function App() {
  const [labels, setLabels] = useState(null);
  const [labelsError, setLabelsError] = useState(null);

  const loadLabels = useCallback(() => {
    setLabelsError(null);
    getLabels().then(setLabels).catch(setLabelsError);
  }, []);
  useEffect(loadLabels, [loadLabels]);

  if (!labels) {
    return (
      <LabelsContext.Provider value={{}}>
        <main className="boot">{labelsError && <BootError err={labelsError} onRetry={loadLabels} />}</main>
      </LabelsContext.Provider>
    );
  }
  return (
    <LabelsContext.Provider value={labels}>
      <Workspace />
    </LabelsContext.Provider>
  );
}

function BootError({ err, onRetry }) {
  return (
    <div className="alert alert-error" role="alert">
      <p>{err instanceof NetworkError ? BOOT_NETWORK_ERROR : err.message}</p>
      <button type="button" className="btn" onClick={onRetry} aria-label={BOOT_RETRY}>↻</button>
    </div>
  );
}

function Workspace() {
  const t = useLabels();
  const [state, setState] = useState(EMPTY);
  const [tab, setTab] = useState("import");
  // Tabs stay mounted once visited (so their local state survives switching);
  // a new analysis clears the list so the later tabs start fresh.
  const [visited, setVisited] = useState(() => new Set(["import"]));
  const configured = state.config != null;

  const selectTab = useCallback((id) => {
    setTab(id);
    setVisited((v) => (v.has(id) ? v : new Set(v).add(id)));
    // Plotly sizes charts on window resize; a tab that was hidden needs one nudge.
    requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
  }, []);

  // A new upload invalidates everything downstream of it.
  const onUploaded = useCallback((upload) => {
    setState({ ...EMPTY, sessionId: upload.session_id, upload });
    setVisited(new Set(["import"]));
  }, []);

  const onAnalysed = useCallback(({ config, eda, findings }) => {
    setState((s) => ({ ...s, config, eda, findings, choices: defaultChoices(findings), scaling: {}, applied: null }));
    setVisited(new Set(["import"]));
    selectTab("eda");
  }, [selectTab]);

  // Changing a choice invalidates the last /apply, so the download can't be stale.
  const onChoice = useCallback((column, rule, option) => {
    setState((s) => ({ ...s, choices: setChoice(s.choices, column, rule, option), applied: null }));
  }, []);

  const onReset = useCallback(() => {
    setState((s) => ({ ...s, choices: defaultChoices(s.findings), scaling: {}, applied: null }));
  }, []);

  // Scaling runs last, so /preview and /apply recompute its recommendation on each
  // column after the earlier chosen steps (see followScaling).
  const onScaling = useCallback((column, finding) => {
    setState((s) => {
      const { choices, changed } = followScaling(withScaling(s.findings, s.scaling), s.choices, { [column]: finding });
      return { ...s, scaling: { ...s.scaling, [column]: finding }, choices, applied: changed ? null : s.applied };
    });
  }, []);

  // /apply result, plus the choices it was run with (they may follow recomputed scaling).
  const onApplied = useCallback((applied, choices) => {
    setState((s) => ({ ...s, applied, choices, scaling: { ...s.scaling, ...applied.scaling } }));
  }, []);

  const findings = useMemo(() => withScaling(state.findings, state.scaling), [state.findings, state.scaling]);

  const steps = useMemo(() => [
    { id: "import", label: t("ui.tab.import"),
      status: state.upload ? t("ui.step.rows", { n: fmtInt(state.upload.n_rows) }) : t("ui.step.no_file") },
    { id: "eda", label: t("ui.tab.eda"), locked: !configured,
      status: configured ? t("ui.step.split", { train: fmtInt(state.config.n_train), test: fmtInt(state.config.n_test) }) : "" },
    { id: "preprocessing", label: t("ui.tab.preprocessing"), locked: !configured,
      status: configured ? t("ui.step.findings", { n: state.findings.length }) : "" },
    { id: "export", label: t("ui.tab.export"), locked: !configured,
      status: configured ? (state.applied ? t("ui.step.applied") : t("ui.step.not_applied")) : "" },
  ], [t, state, configured]);

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead-inner">
          <div className="brand">
            <h1>{t("ui.app.title")}</h1>
            <p>{t("ui.app.subtitle")}</p>
          </div>
          <Stepper steps={steps} active={tab} onSelect={selectTab} />
        </div>
      </header>
      <main className="page" id="main">
        <TabPanel id="import" active={tab} visited={visited}>
          <ImportTab upload={state.upload} onUploaded={onUploaded} onAnalysed={onAnalysed} />
        </TabPanel>
        {configured && (
          <TabPanel id="eda" active={tab} visited={visited}>
            <EdaTab eda={state.eda} findings={state.findings} upload={state.upload} />
          </TabPanel>
        )}
        {configured && (
          <TabPanel id="preprocessing" active={tab} visited={visited}>
            <PreprocessingTab sessionId={state.sessionId} eda={state.eda} findings={findings}
                              scaling={state.scaling} choices={state.choices} onChoice={onChoice}
                              onReset={onReset} onScaling={onScaling} />
          </TabPanel>
        )}
        {configured && (
          <TabPanel id="export" active={tab} visited={visited}>
            <ExportTab sessionId={state.sessionId} findings={findings} choices={state.choices}
                       applied={state.applied} onApplied={onApplied} />
          </TabPanel>
        )}
      </main>
    </div>
  );
}

/** The findings with each column's scaling finding replaced by its recomputed version. */
function withScaling(findings, scaling) {
  if (!Object.keys(scaling).length) return findings;
  const out = findings.map((f) => (f.rule === "scaling" && scaling[f.column] ? scaling[f.column] : f));
  for (const [column, f] of Object.entries(scaling)) {
    if (!findings.some((g) => g.rule === "scaling" && g.column === column)) out.push(f);
  }
  return out;
}


function TabPanel({ id, active, visited, children }) {
  if (!visited.has(id)) return null;
  return <div role="tabpanel" id={`panel-${id}`} hidden={active !== id}>{children}</div>;
}

function Stepper({ steps, active, onSelect }) {
  const t = useLabels();
  return (
    <nav aria-label={t("ui.app.steps")}>
      <ol className="stepper" role="tablist">
        {steps.map((s, i) => (
          <li key={s.id}>
            <button
              type="button"
              role="tab"
              aria-selected={active === s.id}
              aria-controls={`panel-${s.id}`}
              disabled={s.locked}
              title={s.locked ? t("ui.step.locked") : undefined}
              className="step"
              onClick={() => onSelect(s.id)}
            >
              <span className="step-index" aria-hidden="true">{i + 1}</span>
              <span className="step-text">
                <span className="step-label">{s.label}</span>
                <span className="step-status">{s.status}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
