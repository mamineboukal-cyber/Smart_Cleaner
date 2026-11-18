/** The file to upload from a drop event's dataTransfer: the first file, or null when
 * the drag carried none (selected text, a link). */
export function pickDroppedFile(dataTransfer) {
  return dataTransfer?.files?.[0] ?? null;
}
