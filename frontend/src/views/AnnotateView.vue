<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import {
  api,
  RATING_CLASS_NAMES,
  type Prefill,
  type ResultFields,
} from "../api";
import Combobox from "../components/Combobox.vue";
import NumberField from "../components/NumberField.vue";
import { computeWarnings } from "../warnings";

const route = useRoute();
const router = useRouter();

const imageId = computed(() => String(route.params.id));
const filename = ref<string | null>(null);
const loading = ref(true);

const songCandidates = ref<{ image_id: string; confidence: number }[]>([]);
const partnerCandidates = ref<{ image_id: string; confidence: number }[]>([]);

const emptyFields = (): ResultFields => ({
  rois_type: null,
  song_id: null,
  partner_id: null,
  rating_class: null,
  clear_status: null,
  score: null,
  pure: null,
  far: null,
  lost: null,
  max_recall: null,
  high_score: null,
  high_score_delta: null,
  pure_shiny: null,
  pure_early: null,
  pure_late: null,
  far_early: null,
  far_late: null,
  checked: false,
});

const form = reactive<ResultFields>(emptyFields());

function applyPrefill(prefill: Prefill) {
  form.rois_type = prefill.rois_type;
  form.song_id = prefill.song_id ?? null;
  form.partner_id = prefill.partner_id ?? null;
  form.rating_class = prefill.rating_class ?? null;
  form.clear_status = prefill.clear_status ?? null;
  form.score = prefill.score ?? null;
  form.pure = prefill.pure ?? null;
  form.far = prefill.far ?? null;
  form.lost = prefill.lost ?? null;
  form.max_recall = prefill.max_recall ?? null;
  form.high_score = null;
  form.high_score_delta = null;
  form.pure_shiny = null;
  form.pure_early = null;
  form.pure_late = null;
  form.far_early = null;
  form.far_late = null;
}

async function load() {
  loading.value = true;
  try {
    const [prefill] = await Promise.all([
      api.getPrefill(imageId.value).catch((e: Error) => {
        toast.error(`预识别失败：${e.message}`);
        return null;
      }),
      api
        .listImages(false, 0, 1)
        .then(() => undefined)
        .catch(() => undefined),
    ]);

    if (prefill != null) {
      applyPrefill(prefill);
      songCandidates.value = prefill.song_id_candidates ?? [];
      partnerCandidates.value = prefill.partner_id_candidates ?? [];
    }

		try {
			const saved = await api.getResult(imageId.value);
			// saved (draft) values win, but empty fields fall back to prefill
			const merged: ResultFields = { ...emptyFields(), ...prefill };
			for (const key of Object.keys(emptyFields()) as (keyof ResultFields)[]) {
				const value = saved[key];
				if (value != null) {
					(merged as Record<string, unknown>)[key] = value;
				}
			}
			Object.assign(form, merged);
		} catch {
			// not annotated yet; prefill stays
		}

    const list = await api.listImages(false, 0, 1);
    filename.value = list.items.find((it) => it.id === imageId.value)?.original_filename ?? null;
  } finally {
    loading.value = false;
  }
}

async function save(): Promise<boolean> {
  try {
    const saved = await api.saveResult(imageId.value, { ...form });
    form.checked = saved.checked;
    return true;
  } catch (e) {
    toast.error(`保存失败：${(e as Error).message}`);
    return false;
  }
}

async function goNext() {
  const data = await api.listImages(true, 0, 200);
  const ids = data.items.map((it) => it.id);
  if (ids.length === 0) {
    toast.success("没有未标注的图片了");
    await router.push("/");
    return;
  }
  const idx = ids.indexOf(imageId.value);
  const nextId = ids[(idx + 1) % ids.length];
  await router.replace(`/annotate/${nextId}`);
}

async function saveAndNext() {
  if (await save()) await goNext();
}

async function saveChecked() {
  form.checked = true;
  if (await save()) await goNext();
}

async function skip() {
  await goNext();
}

const warnings = computed(() => computeWarnings(form));

function onKeydown(event: KeyboardEvent) {
  if (event.ctrlKey && event.key === "Enter") {
    void saveAndNext();
  }
}

watch(imageId, load);
onMounted(() => {
  load();
  window.addEventListener("keydown", onKeydown);
});
onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
});
</script>

<template>
  <div v-if="!loading" class="grid gap-4 py-4 lg:grid-cols-[1fr_360px]">
    <section>
      <img
        :src="api.fileUrl(imageId)"
        class="w-full rounded border border-border bg-card"
        :alt="filename ?? imageId"
      />
      <p class="mt-1 text-xs text-muted-foreground">{{ filename ?? imageId }}</p>
    </section>

    <section class="space-y-4">
      <div class="rounded border border-border bg-card p-3 space-y-3">
        <div class="grid grid-cols-3 gap-2">
          <label>
            <span class="field-label">rois_type</span>
            <select v-model.number="form.rois_type" class="field-input mt-0.5">
              <option :value="null">未知</option>
              <option :value="0">T1</option>
              <option :value="1">T2</option>
            </select>
          </label>
          <label>
            <span class="field-label">rating_class</span>
            <select v-model.number="form.rating_class" class="field-input mt-0.5">
              <option :value="null">未知</option>
              <option v-for="(name, i) in RATING_CLASS_NAMES" :key="name" :value="i">
                {{ i }} {{ name }}
              </option>
            </select>
          </label>
          <label>
            <span class="field-label">clear_status</span>
            <select v-model.number="form.clear_status" class="field-input mt-0.5">
              <option :value="null">未知</option>
              <option :value="0">0 LOST</option>
              <option :value="1">1 CLEAR</option>
              <option :value="2">2 FR</option>
              <option :value="3">3 PM</option>
            </select>
          </label>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <Combobox v-model="form.song_id" label="song_id" :options="songCandidates" />
          <Combobox v-model="form.partner_id" label="partner_id" :options="partnerCandidates" />
        </div>

        <div class="grid grid-cols-3 gap-2">
          <NumberField v-model="form.score" label="score" />
          <NumberField v-model="form.pure" label="pure" />
          <NumberField v-model="form.far" label="far" />
          <NumberField v-model="form.lost" label="lost" />
          <NumberField v-model="form.max_recall" label="max_recall" />
          <NumberField v-model="form.pure_shiny" label="pure_shiny" />
          <NumberField v-model="form.high_score" label="high_score" />
          <NumberField v-model="form.high_score_delta" label="high_score_delta" />
        </div>

        <div class="grid grid-cols-4 gap-2">
          <NumberField v-model="form.pure_early" label="pure_early" />
          <NumberField v-model="form.pure_late" label="pure_late" />
          <NumberField v-model="form.far_early" label="far_early" />
          <NumberField v-model="form.far_late" label="far_late" />
        </div>
      </div>

      <div
        v-if="warnings.length > 0"
        class="rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
      >
        <div class="mb-1 font-medium">一致性警告</div>
        <ul class="list-inside list-disc space-y-0.5">
          <li v-for="w in warnings" :key="w">{{ w }}</li>
        </ul>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button class="btn" @click="saveChecked">确认并下一张</button>
        <button class="btn-secondary" @click="saveAndNext">保存草稿并下一张</button>
        <button class="btn-secondary" @click="skip">跳过</button>
        <label class="ml-auto flex items-center gap-1.5 text-sm">
          <input v-model="form.checked" type="checkbox" />
          checked
        </label>
      </div>
    </section>
  </div>
</template>
