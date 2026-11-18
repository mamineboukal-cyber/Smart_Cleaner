// The user's choices: {[column]: {[rule]: option}}.
// Starts from the backend's recommendations; every update returns a new object
// so React re-renders and the previous state is never mutated.

/** One choice per column-level finding, set to its recommendation. */
export function defaultChoices(findings) {
  const choices = {};
  for (const f of findings) {
    if (f.column == null) continue; // dataset-level (duplicates): not a per-column choice
    choices[f.column] = { ...choices[f.column], [f.rule]: f.recommendation };
  }
  return choices;
}

/** Immutable update of one (column, rule) choice. */
export function setChoice(choices, column, rule, option) {
  return { ...choices, [column]: { ...choices[column], [rule]: option } };
}

/** Summary for the Export tab: how many choices follow the recommendation,
 * differ from it, or are "none", and which columns will be dropped. */
export function countChoices(findings, choices) {
  const out = { recommended: 0, changed: 0, none: 0, dropped: [] };
  for (const f of findings) {
    if (f.column == null) continue;
    const chosen = choices[f.column]?.[f.rule] ?? f.recommendation;
    if (chosen === f.recommendation) out.recommended += 1;
    else if (chosen === "none") out.none += 1;
    else out.changed += 1;
    if (chosen === "drop_column" && !out.dropped.includes(f.column)) out.dropped.push(f.column);
  }
  return out;
}

/** Scaling runs last, so the backend recomputes its recommendation after each
 * column's earlier steps. Where the user had kept the previous recommendation,
 * follow the new one; an explicit different choice is left alone.
 * `findings` must already include any earlier recomputed scaling findings. */
export function followScaling(findings, choices, recomputed) {
  let next = choices;
  let changed = false;
  for (const [column, f] of Object.entries(recomputed)) {
    const previous = findings.find((g) => g.rule === "scaling" && g.column === column)?.recommendation;
    const chosen = choices[column]?.scaling;
    const follows = chosen == null || chosen === previous;
    if (follows && chosen !== f.recommendation) {
      next = setChoice(next, column, "scaling", f.recommendation);
      changed = true;
    }
  }
  return { choices: next, changed };
}
