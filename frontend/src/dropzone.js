/** The file to upload from a drop event's dataTransfer: the first file, or null when
 * the drag carried none (selected text, a link). */
export function pickDroppedFile(dataTransfer) {
  return dataTransfer?.files?.[0] ?? null;
}

const isFileDrag = (e) => Array.from(e.dataTransfer?.types ?? []).includes("Files");

/** Stops the browser from opening a file dropped outside the drop zone, which would
 * navigate away and lose the whole session. Drags the zone already handled
 * (defaultPrevented) and non-file drags (text into an input) are left alone.
 * Returns a cleanup function. */
export function guardWindowDrop(target) {
  const onOver = (e) => {
    if (!isFileDrag(e) || e.defaultPrevented) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "none"; // "not allowed" cursor outside the zone
  };
  const onDrop = (e) => {
    if (isFileDrag(e) && !e.defaultPrevented) e.preventDefault();
  };
  target.addEventListener("dragover", onOver);
  target.addEventListener("drop", onDrop);
  return () => {
    target.removeEventListener("dragover", onOver);
    target.removeEventListener("drop", onDrop);
  };
}
