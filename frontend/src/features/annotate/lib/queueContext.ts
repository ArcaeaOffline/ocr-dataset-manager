import { computed } from "vue";
import { useRoute, type LocationQuery } from "vue-router";

import type { QueueTraversal } from "@/api";

const CATEGORIES = ["all", "unchecked", "checked"] as const;
const SORT_KEYS = ["created_at", "original_filename"] as const;
const DIRECTIONS = ["asc", "desc"] as const;

function pick<T extends string>(allowed: readonly T[], value: unknown): T | undefined {
  return typeof value === "string" && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : undefined;
}

/**
 * Reads the queue view's traversal context from the annotate route
 * query. The hidden category has no walk, so it counts as absent.
 * Unknown, repeated (repeated params serialize as arrays) and missing
 * values all fall back to the backend defaults by becoming absent.
 */
export function readQueueTraversal(query: LocationQuery): QueueTraversal {
  return {
    category: pick(CATEGORIES, query.category),
    order_by: pick(SORT_KEYS, query.order_by),
    direction: pick(DIRECTIONS, query.direction),
  };
}

/**
 * Route binding of the traversal context for the annotate flows:
 * `traversal` re-parses the query on every navigation, and
 * `annotateLocation` hops to another annotate image carrying the query
 * along, so a walk keeps stepping through the slice the queue view
 * listed.
 */
export function useQueueTraversal() {
  const route = useRoute();
  const traversal = computed(() => readQueueTraversal(route.query));
  // the annotate query carries only the traversal context, so hops can
  // forward it verbatim
  const annotateLocation = (id: string) => ({ path: `/annotate/${id}`, query: route.query });
  return { traversal, annotateLocation };
}
