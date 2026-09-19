import type { ResultFields } from "./api";

// screenshot-internal consistency warnings; no chart metadata involved.
// absent values (null) never warn on their own
export function computeWarnings(r: ResultFields): string[] {
  const warnings: string[] = [];

  if (r.pure != null && r.pure_shiny != null && (r.pure_early != null || r.pure_late != null)) {
    const early = r.pure_early ?? 0;
    const late = r.pure_late ?? 0;
    if (r.pure !== r.pure_shiny + early + late) {
      warnings.push(`pure ≠ shiny+early+late (${r.pure} ≠ ${r.pure_shiny}+${early}+${late})`);
    }
  }

  if (r.far != null && (r.far_early != null || r.far_late != null)) {
    const early = r.far_early ?? 0;
    const late = r.far_late ?? 0;
    if (r.far !== early + late) {
      warnings.push(`far ≠ early+late (${r.far} ≠ ${early}+${late})`);
    }
  }

  if (r.pure != null && r.far != null && r.lost != null && r.max_recall != null) {
    if (r.lost === 0 && r.max_recall !== r.pure + r.far) {
      warnings.push(
        `无 lost 时 max_recall 应等于 pure+far (${r.max_recall} ≠ ${r.pure}+${r.far})`,
      );
    }
    if (r.lost > 0 && r.max_recall > r.pure + r.far) {
      warnings.push(
        `有 lost 时 max_recall 不可能超过 pure+far (${r.max_recall} > ${r.pure}+${r.far})`,
      );
    }
  }

  if (r.score === 0) warnings.push("score 为 0");
  if (r.score != null && r.score > 10_010_000) {
    warnings.push("score 超出可能上限");
  }

  if (r.clear_status === 2 && (r.lost ?? 0) !== 0) {
    warnings.push("FULL RECALL 但 lost ≠ 0");
  }
  if (r.clear_status === 3 && ((r.far ?? 0) !== 0 || (r.lost ?? 0) !== 0)) {
    warnings.push("PURE MEMORY 但 far/lost ≠ 0");
  }

  if (
    r.score != null &&
    r.high_score != null &&
    r.high_score_delta != null &&
    r.high_score + r.high_score_delta !== r.score
  ) {
    warnings.push(
      `high_score + delta ≠ score (${r.high_score}+${r.high_score_delta} ≠ ${r.score})`,
    );
  }

  return warnings;
}
