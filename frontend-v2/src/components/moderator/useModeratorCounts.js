import { computed, ref } from "vue";
import { getModerationQueue, getModerationRequests } from "../../services/moderatorApi";

export function useModeratorCounts() {
  const counts = ref({ pending: 0, approved: 0, rejected: 0 });
  const loading = ref(true);

  const approvalPercent = computed(() => {
    const decided = counts.value.approved + counts.value.rejected;
    return decided ? `${Math.round((counts.value.approved / decided) * 100)}%` : "—";
  });

  async function loadCounts() {
    loading.value = true;
    try {
      const [pending, approved, rejected] = await Promise.all([
        getModerationQueue({ page_size: 1 }),
        getModerationRequests({ status: "published,in_progress,closed", page_size: 1 }),
        getModerationRequests({ status: "rejected", page_size: 1 }),
      ]);
      counts.value = {
        pending: pending.count,
        approved: approved.count,
        rejected: rejected.count,
      };
    } finally {
      loading.value = false;
    }
  }

  return { approvalPercent, counts, countsLoading: loading, loadCounts };
}
