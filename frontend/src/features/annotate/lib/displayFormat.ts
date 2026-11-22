/** 8-digit zero-padded, apostrophe-grouped digits: 9123456 -> "09'123'456". */
function groupDigits(value: number): string {
  return String(value)
    .padStart(8, "0")
    .replace(/\B(?=(\d{3})+(?!\d))/g, "'");
}

/**
 * The score text as the screenshot renders it: zero-padded to 8 digits
 * and apostrophe-grouped. Negative and non-integer values render no text.
 */
export function formatScore(value: number | null): string | null {
  if (value == null || value < 0 || !Number.isInteger(value)) return null;
  return groupDigits(value);
}

/**
 * The high score text as the screenshot renders it: a zero high score
 * (no record yet) shows unpadded. Other values render like a score.
 */
export function formatHighScore(value: number | null): string | null {
  if (value === 0) return "0";
  return formatScore(value);
}

/**
 * formatScore with a leading sign, the high_score_delta rendering:
 * 1234 -> "+00'001'234". Zero carries "+". Non-integer values render no
 * text.
 */
export function formatScoreDelta(value: number | null): string | null {
  if (value == null || !Number.isInteger(value)) return null;
  return `${value < 0 ? "-" : "+"}${groupDigits(Math.abs(value))}`;
}

export interface EarlyLateFields {
  far_late: number | null;
  pure_late: number | null;
  far_early: number | null;
  pure_early: number | null;
}

/**
 * The screenshot's early/late line rebuilt from its four values:
 * "L12(P34) E56(P78)". The (P…) parts exist only when the PURE early/late
 * display is on — both or neither: incomplete PURE data cannot occur on a
 * real screenshot, so any missing pure value drops the whole PURE info.
 * Null unless both far values are set.
 */
export function formatEarlyLate(fields: EarlyLateFields): string | null {
  const { far_late, pure_late, far_early, pure_early } = fields;
  if (far_late == null || far_early == null) return null;
  const showPure = pure_late != null && pure_early != null;
  const late = showPure ? `L${far_late}(P${pure_late})` : `L${far_late}`;
  const early = showPure ? `E${far_early}(P${pure_early})` : `E${far_early}`;
  return `${late} ${early}`;
}
