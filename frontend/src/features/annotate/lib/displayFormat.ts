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
 * "L12(P34) E56(P78)". The (P…) parts only exist when the PURE early/late
 * display is on, so each renders only when its value is filled. Null
 * unless both far values are set.
 */
export function formatEarlyLate(fields: EarlyLateFields): string | null {
  const { far_late, pure_late, far_early, pure_early } = fields;
  if (far_late == null || far_early == null) return null;
  const late = pure_late == null ? `L${far_late}` : `L${far_late}(P${pure_late})`;
  const early = pure_early == null ? `E${far_early}` : `E${far_early}(P${pure_early})`;
  return `${late} ${early}`;
}
